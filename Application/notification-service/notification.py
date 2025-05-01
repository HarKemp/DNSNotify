import asyncio
import nats
from nats.errors import ConnectionClosedError, TimeoutError, NoServersError
import json
import os
import signal
import requests


NATS_URL = os.getenv('NATS_URL', 'nats://nats:4222')
NATS_NOTIFY_SUBJECT = os.getenv('NATS_NOTIFY_SUBJECT', 'dns.malicious.notify') # Subject ML service publishes to
NATS_QUEUE_GROUP = os.getenv('NATS_QUEUE_GROUP', 'notification_group') # Queue group for load balancing
MATTERMOST_WEBHOOK_URL = os.getenv('MATTERMOST_WEBHOOK_URL') # Get webhook

shutdown_event = asyncio.Event()

def send_mattermost_notification(payload):
    if not MATTERMOST_WEBHOOK_URL:
        print("[ERROR] MATTERMOST_WEBHOOK_URL not set. Cannot send notification.")
        return False

    try:
        message = (
            f"🚨 **Malicious DNS Query Detected** 🚨\n"
            f"-------------------------------------\n"
            f"**Domain:** `{payload.get('domain', 'N/A')}`\n"
            f"**Timestamp:** {payload.get('timestamp', 'N/A')}\n"
            f"**Client IP:** {payload.get('client_ip', 'N/A')}\n"
            f"**Query Type:** {payload.get('query_type', 'N/A')}\n"
            f"**Malicious Probability:** {payload.get('probability', 'N/A'):.2f}\n"
            f"**Log Snippet:** ```{payload.get('raw_log_snippet', 'N/A')}```"
        )

        headers = {'Content-Type': 'application/json'}
        data = json.dumps({'text': message})

        response = requests.post(MATTERMOST_WEBHOOK_URL, headers=headers, data=data, timeout=10)
        response.raise_for_status()

        print(f"Successfully sent notification for domain: {payload.get('domain')}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to send Mattermost notification: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error formatting/sending notification: {e}")
        return False


async def run_notification_consumer():
    nc = None
    while not shutdown_event.is_set():
        try:
            print(f"Notification Service: Connecting to NATS at {NATS_URL}...")
            nc = await nats.connect(NATS_URL, name="notification-service",
                                    reconnect_time_wait=5, max_reconnect_attempts=10)
            print(f"Notification Service: Connected to NATS: {nc.connected_url.netloc}...")

            sub = await nc.subscribe(NATS_NOTIFY_SUBJECT, queue=NATS_QUEUE_GROUP)
            print(f"Notification Service: Subscribed to '{NATS_NOTIFY_SUBJECT}' with queue group '{NATS_QUEUE_GROUP}'.")


            async for msg in sub.messages:
                if shutdown_event.is_set():
                     break
                try:
                    print(f"Notification Service: Received message on subject {msg.subject}")
                    payload = json.loads(msg.data.decode())

                    # Attempt to send notification
                    success = send_mattermost_notification(payload)
                    if not success:
                        print(f"[WARN] Notification failed for payload: {payload}")

                except json.JSONDecodeError:
                    print(f"[ERROR] Failed to decode JSON notification message")
                except Exception as e:
                    print(f"[ERROR] Error processing notification message: {e}")

        except (ConnectionClosedError, TimeoutError, NoServersError, OSError) as conn_err:
            print(f"[ERROR] Notification Service: NATS connection error: {conn_err}. Retrying...")
        except Exception as e:
            print(f"[ERROR] Notification Service: Unexpected error in consumer loop: {e}")
        finally:
            if sub: # Unsubscribe if subscription exists
                 try: await sub.unsubscribe()
                 except Exception: pass
                 sub = None
            if nc and nc.is_connected:
                print("Notification Service: Draining NATS connection...")
                await nc.drain()
                print("Notification Service: NATS connection drained.")
            elif nc:
                 await nc.close()
                 print("Notification Service: NATS connection closed.")
            nc = None
            if not shutdown_event.is_set():
                 await asyncio.sleep(5)

    print("Notification Service: Shutdown signal received. Exiting.")

def handle_shutdown(sig, frame):
    print(f"Notification Service: Received signal {sig}. Initiating graceful shutdown...")
    shutdown_event.set()

if __name__ == "__main__":
    if not MATTERMOST_WEBHOOK_URL:
        print("[ERROR] MATTERMOST_WEBHOOK_URL environment variable is not set. Notification service will not work.")

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Start the consumer
    print("Starting Notification Service consumer...")
    try:
        asyncio.run(run_notification_consumer())
    except KeyboardInterrupt:
        print("Notification Service: KeyboardInterrupt received. Shutting down.")
        shutdown_event.set()

    print("Notification Service shut down.")

