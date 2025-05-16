import asyncio
import nats
import json
import os
from nats.errors import ConnectionClosedError, TimeoutError, NoServersError
import joblib
import numpy as np
import pandas as pd
import datetime
import ipaddress
from clickhouse_connect import get_client
import time

from ml_processing import process_log_entry, write_to_log

NATS_URL = os.getenv('NATS_URL', 'nats://nats:4222')
NATS_LOG_SUBJECT = os.getenv('NATS_LOG_SUBJECT', "dns.logs")
NATS_NOTIFY_SUBJECT = os.getenv('NATS_NOTIFY_SUBJECT', "dns.malicious.notify")
NATS_STREAM_NAME = os.getenv('NATS_STREAM_NAME', "DNSLogsStream")
NATS_CONSUMER_NAME = os.getenv('NATS_CONSUMER_NAME', "MLProcessorBatch")
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
BATCH_WAIT_TIMEOUT = float(os.getenv('BATCH_WAIT_TIMEOUT', '1.0'))

CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', '8123'))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'default')
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'default')

CLICKHOUSE_TABLE = 'dns_logs'
CLICKHOUSE_RECONNECT_RETRIES = 6
CLICKHOUSE_RETRY_DELAY = 3

ALLOWLIST_PATH = os.getenv("ALLOWLIST_PATH", "/config/allowlist.txt")

def _load_allowlist():
    try:
        with open(ALLOWLIST_PATH) as f:
            return {l.strip().lower() for l in f if l.strip()}
    except FileNotFoundError:
        return set()

allowlist = _load_allowlist()
allowlist_mtime = os.path.getmtime(ALLOWLIST_PATH) if os.path.exists(ALLOWLIST_PATH) else 0

client = None
ml_model = None
feature_names = []


# Connect to clickhouse
def connect_clickhouse():
    global client
    max_retries = CLICKHOUSE_RECONNECT_RETRIES
    retry_delay = CLICKHOUSE_RETRY_DELAY
    print("Attempting to connect to ClickHouse...")
    for attempt in range(max_retries):
        try:
            client = get_client(
                host=CLICKHOUSE_HOST,
                port=CLICKHOUSE_PORT,
                username=CLICKHOUSE_USER,
                password=CLICKHOUSE_PASSWORD,
                database=CLICKHOUSE_DATABASE,
                connect_timeout = 5,
                send_receive_timeout = 10
            )
            client.command('SELECT 1') # Test connection
            print(f"Successfully connected to ClickHouse on attempt {attempt + 1}.")
            return True
        except Exception as e:
            print(f"[WARN] Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print("[ERROR] Failed to connect to ClickHouse.")
                client = None
                return False
    return False


def load_model():
    global ml_model, feature_names
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'dns_classifier.joblib')
    try:
        model_dict = joblib.load(model_path)
        ml_model = model_dict['model']
        feature_names = model_dict['features']
        print("Model loaded successfully.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        ml_model = None
        feature_names = []
        return False


async def main():
    # Load model and connect DB
    if not load_model(): exit(1)
    if not connect_clickhouse(): exit(1)

    nc = None
    js = None
    psub = None
    # Connect to NATS and subscribe to logs
    while True:
        try:
            print(f"Connecting to NATS at {NATS_URL}...")
            nc = await nats.connect(NATS_URL, name="ml-model-processor")
            js = nc.jetstream()
            print(f"Connected to NATS: {nc.connected_url.netloc}...")

            try:
                print(f"Ensuring JetStream stream '{NATS_STREAM_NAME}' exists...")
                await js.add_stream(name=NATS_STREAM_NAME, subjects=[NATS_LOG_SUBJECT])
            except Exception as e:
                print(f"[ERROR] Failed to ensure NATS stream exists: {e}")
                raise # Trigger reconnect loop


            print(f"Creating/getting durable consumer '{NATS_CONSUMER_NAME}'...")
            psub = await js.pull_subscribe(
                subject=NATS_LOG_SUBJECT,
                durable=NATS_CONSUMER_NAME,
                config=nats.js.api.ConsumerConfig(ack_policy=nats.js.api.AckPolicy.EXPLICIT)
            )
            print(f"Consumer '{NATS_CONSUMER_NAME}' ready.")

            # Trigger batch processing loop
            while nc.is_connected:
                db_batch_to_insert = []
                notifications_to_publish = []
                processed_msgs_metadata = []  # Keep track of msgs to ack

                try:
                    # Fetch a batch of messages
                    # print(f"Fetching batch (size={BATCH_SIZE}, timeout={BATCH_WAIT_TIMEOUT}s)...")
                    msgs = await psub.fetch(batch=BATCH_SIZE, timeout=BATCH_WAIT_TIMEOUT)

                    if not msgs: continue  # Go back to fetch if no messages

                    # print(f"Received {len(msgs)} messages.")
                    for msg in msgs:
                        try:
                            payload = json.loads(msg.data.decode())
                            print(f"[DEBUG] Received Payload: {payload}") ## TODO: REmove
                            global allowlist, allowlist_mtime
                            try:
                                cur_mtime = os.path.getmtime(ALLOWLIST_PATH)
                                if cur_mtime != allowlist_mtime:
                                    allowlist = _load_allowlist()
                                    allowlist_mtime = cur_mtime
                                    print(f"[INFO] Reloaded allow‑list: {len(allowlist)} domains")
                            except FileNotFoundError:
                                pass
                            db_tuple, notification_payload = process_log_entry(payload, ml_model, feature_names, allowlist)

                            if db_tuple:
                                db_batch_to_insert.append(db_tuple)
                            if notification_payload:
                                notifications_to_publish.append(notification_payload)

                            processed_msgs_metadata.append(msg)

                        except json.JSONDecodeError:
                            print(f"[ERROR] Failed JSON decode")
                            await msg.nak(delay=5)
                        except Exception as e:
                            print(f"[ERROR] Failed processing message {e}")
                            await msg.nak(delay=5)

                    # Insert batch into ClickHouse
                    if db_batch_to_insert:
                        write_to_log(db_batch_to_insert, client, CLICKHOUSE_TABLE)

                    # Send notification to Mattermost
                    if notifications_to_publish:
                        for notif_payload in notifications_to_publish:
                            await nc.publish(NATS_NOTIFY_SUBJECT, json.dumps(notif_payload).encode())

                    # Acknowledge all successfully processed messages in the batch
                    if processed_msgs_metadata:
                        ack_tasks = [msg.ack() for msg in processed_msgs_metadata]
                        await asyncio.gather(*ack_tasks)
                        print(f"Acked {len(processed_msgs_metadata)} messages.")


                except TimeoutError:  # Expected when fetch times out
                    pass
                except nats.errors.NoMessagesError:  # Expected when no messages available
                    pass
                except Exception as e:
                    print(f"[ERROR] Error fetching/processing batch: {e}")
                    await asyncio.sleep(2)  # Delay before retrying fetch

        except (ConnectionClosedError, TimeoutError, NoServersError, OSError) as conn_err:
            print(f"[ERROR] NATS connection error: {conn_err}. Reconnecting...")
        except Exception as e:
            print(f"[ERROR] Unexpected error in main loop: {e}. Reconnecting...")
        finally:
            if nc and nc.is_connected:
                await nc.close()
            nc = None
            js = None
            psub = None
            await asyncio.sleep(5)  # Wait before retrying connection


if __name__ == "__main__":
    print("Starting NATS...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")