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
app = Flask(__name__)
LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "dns_logs.txt")

# Load the trained model and features
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'dns_classifier.joblib')
model_dict = joblib.load(model_path)
model = model_dict['model']
feature_names = model_dict['features']

def calculate_entropy(s):
    probabilities = [float(s.count(c)) / len(s) for c in dict.fromkeys(list(s))]
    return -sum([p * math.log(p, 2) for p in probabilities if p > 0])
def write_to_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
def extract_features_from_log_string(log_string):
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

@app.route('/logs', methods=['POST'])
def handle_logs():
    try:
        data = request.get_json(force=True)
        
        if "log" not in data[0]:
            return jsonify({
                'error': 'Invalid request format',
                'prediction': 0,
                'malicious_probability': 0
            }), 400

        features = extract_features_from_log_string(data[0]["log"])
        
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
        write_to_log(f"Log: {data[0]['log']}, Prediction: {features['prediction']}, Probability: {features['malicious_probability']}")
        return jsonify(features), 200

    except Exception as e:
        return jsonify({
            'error': str(e),
            'prediction': 0,
            'malicious_probability': 0
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
