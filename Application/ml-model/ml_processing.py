import re
import math
import dns.resolver
import json
import datetime
import ipaddress
import pandas as pd


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

def calculate_entropy(s):
    probabilities = [float(s.count(c)) / len(s) for c in dict.fromkeys(list(s))]
    return -sum([p * math.log(p, 2) for p in probabilities if p > 0])


def write_to_log(rows_to_insert, client, table_name):
    if not client: return
    if not rows_to_insert: return

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
        client.insert(table_name, rows_to_insert, column_names=column_names)
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


def process_log_entry(payload, ml_model, feature_names):

    raw_line = None
    iso_time = None
    db_data_tuple = None
    notification_payload = None

    try:
        raw_line = payload.get("message")
        iso_time = payload.get("timestamp")

        if not raw_line or not isinstance(raw_line, str):
            print(f"[ERROR] Invalid log format: Missing or invalid 'message' field. Payload: {str(payload)[:200]}")
            return None, None

        raw_line = raw_line.strip()
        if not iso_time or not isinstance(iso_time, str):
            print(f"[WARN] Missing or invalid 'timestamp' field ({type(iso_time)}), using current time.")
            iso_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        features = extract_features_from_log_string(raw_line)
        prediction_val = None
        probability_val = None

        if features and ml_model and feature_names:
            # Prepare feature vector
            feature_vector = pd.DataFrame([
                [features.get(feat, 0) for feat in feature_names]
            ], columns=feature_names)

            # Make prediction
            prediction = ml_model.predict(feature_vector)[0]
            probability = ml_model.predict_proba(feature_vector)[0]

            # Add prediction to response
            prediction_val = int(prediction)
            probability_val = float(probability[1])

        match = log_pattern_db.search(raw_line)
        if match:
            details = match.groupdict()
            log_time_obj = datetime.datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            db_data_tuple = (
                log_time_obj, ipaddress.ip_address(details['ip']), int(details['port']),
                int(details['query_id']), details['type'], details['domain'], details['proto'],
                details['rcode'], details['flags'], float(details['resp_time']),
                prediction_val, probability_val,
                raw_line
            )

            # TODO Define Mattermost notification payload structure?
            # Temporary implementation of notification payload
            if prediction_val == 1:
                notification_payload = {
                    "timestamp": log_time_obj.isoformat(),
                    "client_ip": details['ip'], "query_type": details['type'],
                    "domain": details['domain'], "probability": probability_val,
                    "raw_log_snippet": raw_line[:200]
                }
        else:
            print(f"[WARN] Log line did not match DB pattern")

    except Exception as e:
        print(f"[ERROR] Exception during processing: {e}.")
        return None, None

    return db_data_tuple, notification_payload