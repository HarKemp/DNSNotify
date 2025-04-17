from flask import Flask, request, jsonify
import json
import os
import re
import math
import dns.resolver
import joblib
import numpy as np
import pandas as pd
import datetime
import ipaddress
from clickhouse_connect import get_client
import time

app = Flask(__name__)

CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 8123))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'default')
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'default')
CLICKHOUSE_TABLE = 'dns_logs'

client = None
max_retries = 5
retry_delay = 3 # seconds

# Connect to clickhouse
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
        break
    except Exception as e:
        print(f"[WARN] Connection attempt {attempt + 1}/{max_retries} failed: {e}")
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("[ERROR] Max retries reached. Failed to connect to ClickHouse. Logs will not be stored.")
            client = None


current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'dns_classifier.joblib')
model_dict = joblib.load(model_path)
model = model_dict['model']
feature_names = model_dict['features']

def calculate_entropy(s):
    probabilities = [float(s.count(c)) / len(s) for c in dict.fromkeys(list(s))]
    return -sum([p * math.log(p, 2) for p in probabilities if p > 0])

def write_to_log(rows_to_insert):
    if not client:
        print("[WARN] ClickHouse client not available. Skipping DB insert.")
        return
    if not rows_to_insert:
        print("[INFO] No rows provided for DB insertion.")
        return

    try:
        column_names = [
            'log_time',           # DateTime
            'client_ip',          # IPv4 or IPv6 or String
            'client_port',        # UInt
            'query_id',           # UInt
            'query_type',         # String
            'domain',             # String
            'protocol',           # String
            'response_code',      # String
            'flags',              # String
            'response_time',      # Float
            'prediction',         # Int
            'malicious_probability', # Float
            'raw_log'             # String
        ]
        client.insert(CLICKHOUSE_TABLE, rows_to_insert, column_names=column_names)
        print(f"Inserted {len(rows_to_insert)} row(s) into ClickHouse.")
    except Exception as e:
        print(f"[ERROR] Failed to insert into ClickHouse: {e}")

def extract_features_from_log_string(log_string):
    if not log_string:
        return None

    features = {}

    # Extract domain from CoreDNS log format
    domain_match = re.search(r'"(?:[A-Z]+) IN (?:https?://)?([a-z0-9.-]+\.[a-z0-9-]+\.?)[^"]*"', log_string)

    if domain_match:
        domain = domain_match.group(1).rstrip('.). ')
        features['domain'] = domain

        # Basic domain features
        features['domain_length'] = len(domain)
        features['domain_entropy'] = calculate_entropy(domain)

        # Character-based features
        domain_lower = domain.lower()
        total_length = len(domain)

        features['numeric_ratio'] = sum(c.isdigit() for c in domain) / total_length
        features['special_char_ratio'] = sum(not c.isalnum() for c in domain) / total_length
        features['vowel_ratio'] = sum(c in 'aeiou' for c in domain_lower) / total_length
        features['consonant_ratio'] = sum(c in 'bcdfghjklmnpqrstvwxyz' for c in domain_lower) / total_length

        # DNS features with timeout
        resolver = dns.resolver.Resolver()
        resolver.timeout = 1
        resolver.lifetime = 1

        try:
            a_records = resolver.resolve(domain, 'A')
            features['dns_record_type'] = 1
            features['ip_count'] = len(a_records)
        except dns.resolver.NXDOMAIN:
            features['dns_record_type'] = -1
            features['ip_count'] = 0
        except Exception:
            features['dns_record_type'] = 0
            features['ip_count'] = 0

        # MX record check
        try:
            mx_records = resolver.resolve(domain, 'MX')
            features['has_mx_response'] = True
        except Exception:
            features['has_mx_response'] = False

        # TXT record checks
        try:
            txt_records = resolver.resolve(domain, 'TXT')
            txt_string = "".join(str(record) for record in txt_records)
            features['has_txt_dns_response'] = True
            features['has_spf_info'] = "spf" in txt_string.lower()
            features['has_dkim_info'] = "dkim" in txt_string.lower()
            features['has_dmarc_info'] = "dmarc" in txt_string.lower()
        except Exception:
            features['has_txt_dns_response'] = False
            features['has_spf_info'] = False
            features['has_dkim_info'] = False
            features['has_dmarc_info'] = False

        # Create feature vector matching training data
        return {
            'domain_length': features['domain_length'],
            'domain_entropy': features['domain_entropy'],
            'numeric_ratio': features['numeric_ratio'],
            'special_char_ratio': features['special_char_ratio'],
            'vowel_ratio': features['vowel_ratio'],
            'consonant_ratio': features['consonant_ratio'],
            'dns_record_type': features['dns_record_type'],
            'ip_count': features['ip_count'],
            'has_mx_response': int(features['has_mx_response']),
            'has_txt_dns_response': int(features['has_txt_dns_response']),
            'has_spf_info': int(features['has_spf_info']),
            'has_dkim_info': int(features['has_dkim_info']),
            'has_dmarc_info': int(features['has_dmarc_info']),
            'domain': features['domain']
        }

    return None

# Regex for parsing the whole log line from coredns
log_pattern_db = re.compile(
    r'''
    ^\[INFO\]\s+
    (?P<ip>[\d\.]+):(?P<port>\d+)\s+-\s+(?P<query_id>\d+)\s+
    "(?P<type>\w+)\s+IN\s+(?P<domain>[^\s]+?)\.?\s+(?P<proto>\w+)\s+[^"]*"\s+
    (?P<rcode>\S+)\s+(?P<flags>[^\s,]+(?:,[^\s,]+)*)\s+ # Handle comma flags
    \d+\s+(?P<resp_time>[\d\.]+)s
    ''', re.VERBOSE
)

@app.route('/logs', methods=['POST'])
def handle_logs():
    try:
        data = request.get_json(force=True)

        raw_line = None
        iso_time = None
        db_row_data = None

        try:
            inner_log_json = json.loads(data[0]["log"])
            raw_line = inner_log_json.get("log", "").strip()
            iso_time = inner_log_json.get("time")
        except (json.JSONDecodeError, KeyError, AttributeError):
            raw_line = data[0].get("log", "").strip()
            if "date" in data[0]:
                iso_time = datetime.datetime.fromtimestamp(data[0]["date"], tz=datetime.timezone.utc).isoformat()
            print("[WARN] Couldn't parse inner JSON, using raw log field and outer timestamp if available.")

        if not raw_line:
            return jsonify({'error': 'Could not extract raw log line'}), 400

        features = extract_features_from_log_string(raw_line)

        if not features:
            return jsonify({
                'error': 'Could not extract features',
                'prediction': 0,
                'malicious_probability': 0
            }), 400

        # Prepare feature vector
        feature_vector = pd.DataFrame([
            [features.get(feat, 0) for feat in feature_names]
        ], columns=feature_names)

        # Make prediction
        prediction = model.predict(feature_vector)[0]
        probability = model.predict_proba(feature_vector)[0]

        # Add prediction to response
        features['prediction'] = int(prediction)
        features['malicious_probability'] = float(probability[1])

        match = log_pattern_db.search(raw_line)
        if match and iso_time and client:
            try:
                details = match.groupdict()
                log_time_obj = datetime.datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
                db_single_row = (
                    log_time_obj, ipaddress.ip_address(details['ip']), int(details['port']),
                    int(details['query_id']), details['type'], details['domain'], details['proto'],
                    details['rcode'], details['flags'], float(details['resp_time']),
                    features['prediction'], features['malicious_probability'],
                    raw_line
                )
                db_row_data = [db_single_row]
            except Exception as db_prep_e:
                print(f"[WARN] Failed preparing DB data: {db_prep_e}")
                db_row_data = None

        if db_row_data:
            write_to_log(db_row_data)

        return jsonify(features), 200

    except Exception as e:
        return jsonify({
            'error': str(e),
            'prediction': 0,
            'malicious_probability': 0
        }), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False)