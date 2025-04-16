from flask import Flask, request, jsonify
import json
import os
import datetime
import re
import math
import dns.resolver
import requests
import joblib
import numpy as np
import pandas as pd

# Load the trained model and features
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'dns_classifier.joblib')
model_dict = joblib.load(model_path)
model = model_dict['model']
feature_names = model_dict['features']

def calculate_entropy(s):
    # Calculates the entropy of a string
    probabilities = [float(s.count(c)) / len(s) for c in dict.fromkeys(list(s))]
    return -sum([p * math.log(p, 2) for p in probabilities if p > 0])

def extract_features_from_log_string(log_string):
    features = {}

    # Updated regex to handle CoreDNS log format with possible https:// prefix
    domain_match = re.search(r'"(?:[A-Z]+) IN (?:https?://)?([a-z0-9.-]+\.[a-z0-9-]+\.?)[^"]*"', log_string)

    if domain_match:
        # Clean the domain by removing trailing dots and spaces
        domain = domain_match.group(1).rstrip('.). ')
        features['domain'] = domain

        # DNS Record type
        try:
            a_records = dns.resolver.resolve(domain, 'A')
            features['dns_record_type'] = 1  # A record
        except dns.resolver.NoAnswer: #If no A record, check for CNAME.
            try:
                cname_records = dns.resolver.resolve(domain, 'CNAME')
                features['dns_record_type'] = 2 # CNAME record
            except dns.resolver.NoAnswer: #if no CNAME, check for MX.
                try:
                    mx_records = dns.resolver.resolve(domain, 'MX')
                    features['dns_record_type'] = 3 # MX record
                except:
                    features['dns_record_type'] = 0 # Other/None.
            except:
                features['dns_record_type'] = 0 # other/none
        except:
            features['dns_record_type'] = 0 # Other/None.

        # MX DNS response
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            features['has_mx_response'] = True  # If we get here, there are MX records!
        except:
            features['has_mx_response'] = False # If there's an error, there are no MX records.

        # TXT DNS response, SPF, DKIM, DMARC
        try:
            txt_records = dns.resolver.resolve(domain, 'TXT')
            features['has_txt_dns_response'] = True
            txt_string = "".join(str(record) for record in txt_records)
            features['has_spf_info'] = "spf" in txt_string.lower()
            features['has_dkim_info'] = "dkim" in txt_string.lower()
            features['has_dmarc_info'] = "dmarc" in txt_string.lower()
        except:
            features['has_txt_dns_response'] = False
            features['has_spf_info'] = False
            features['has_dkim_info'] = False
            features['has_dmarc_info'] = False

        # Domain Entropy
        features['domain_entropy'] = calculate_entropy(domain)

        # Subdomain Entropy
        subdomains = domain.split('.')[:-2]
        if subdomains:
            subdomain_string = "".join(subdomains)
            features['subdomain_entropy'] = calculate_entropy(subdomain_string)
        else:
            features['subdomain_entropy'] = 0

        # Character Features
        vowels = "aeiou"
        special_chars = "-_"
        consonants = "bcdfghjklmnpqrstvwxyz"
        numbers = "0123456789"

        vowel_count = 0
        consonant_count = 0
        numeric_count = 0
        special_char_count = 0

        max_vowel_seq = 0
        max_numeric_seq = 0
        max_special_char_seq = 0

        current_vowel_seq = 0
        current_numeric_seq = 0
        current_special_char_seq = 0

        for char in domain.lower():
            if char in vowels:
                vowel_count += 1
                current_vowel_seq += 1
                current_numeric_seq = 0
                current_special_char_seq = 0
            elif char in consonants:
                consonant_count += 1
                current_vowel_seq = 0
                current_numeric_seq = 0
                current_special_char_seq = 0
            elif char in numbers:
                numeric_count += 1
                current_numeric_seq += 1
                current_vowel_seq = 0
                current_special_char_seq = 0
            elif char in special_chars:
                special_char_count += 1
                current_special_char_seq += 1
                current_vowel_seq = 0
                current_numeric_seq = 0
            else:
                current_vowel_seq = 0
                current_numeric_seq = 0
                current_special_char_seq = 0

            max_vowel_seq = max(max_vowel_seq, current_vowel_seq)
            max_numeric_seq = max(max_numeric_seq, current_numeric_seq)
            max_special_char_seq = max(max_special_char_seq, current_special_char_seq)

        total_length = len(domain)
        if total_length > 0:
            features['vowel_ratio'] = vowel_count / total_length
            features['consonant_ratio'] = consonant_count / total_length
            features['numeric_ratio'] = numeric_count / total_length
            features['special_char_ratio'] = special_char_count / total_length
        else:
            features['vowel_ratio'] = 0
            features['consonant_ratio'] = 0
            features['numeric_ratio'] = 0
            features['special_char_ratio'] = 0

        features['vowel_sequence'] = max_vowel_seq
        features['numeric_sequence'] = max_numeric_seq
        features['special_char_sequence'] = max_special_char_seq
        features['domain_length'] = total_length

        # Alexa DB and Common Ports place holders.
        #features['domain_in_alexa_db'] = False #add alexa db logic
        #features['common_ports'] = False #add common ports logic

        try:
            response = requests.get("http://" + domain, timeout = 3) #Timeout after 3 seconds.
            features['http_response_code'] = response.status_code
        except requests.exceptions.RequestException:
            features['http_response_code'] = -1 #Indicates an error.

        # Align features with training data
        features['TXTDnsResponse'] = int(features.get('has_txt_dns_response', False))
        features['NumericRatio'] = features.get('numeric_ratio', 0)
        features['SpecialCharRatio'] = features.get('special_char_ratio', 0)
        features['VowelRatio'] = features.get('vowel_ratio', 0)
        features['ConsoantRatio'] = features.get('consonant_ratio', 0)
        features['DNSRecordNum'] = features.get('dns_record_type', 0)
        features['MXDnsResponse'] = int(features.get('has_mx_response', False))
        features['HasSPFInfo'] = int(features.get('has_spf_info', False))
        features['HasDkimInfo'] = int(features.get('has_dkim_info', False))
        features['HasDmarcInfo'] = int(features.get('has_dmarc_info', False))
        features['HttpResponseCode'] = features.get('http_response_code', -1)
        features['ConsoantSequence'] = features.get('consonant_sequence', 0)
        features['VowelSequence'] = features.get('vowel_sequence', 0)
        features['NumericSequence'] = features.get('numeric_sequence', 0)
        features['SpecialCharSequence'] = features.get('special_char_sequence', 0)
        features['EntropyOfSubDomains'] = features.get('subdomain_entropy', 0)

        return features
    return None

    
app = Flask(__name__)

LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "dns_logs.txt")

def create_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

def write_to_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

@app.route('/logs', methods=['POST'])
def handle_logs():
    try:
        # Get the request data and validate
        data = request.get_json(force=True)
        if not data or not isinstance(data, list) or len(data) == 0 or "log" not in data[0]:
            write_to_log("Invalid request format")
            return jsonify({
                'error': 'Invalid request format',
                'prediction': 0,
                'malicious_probability': 0
            }), 400

        # Extract features
        write_to_log("Raw log:" + str(data[0]["log"]))
        features = extract_features_from_log_string(data[0]["log"])
        
        if not features:
            write_to_log("Could not extract features from log")
            return jsonify({
                'error': 'Could not extract features from log',
                'prediction': 0,
                'malicious_probability': 0
            }), 400

        # Create feature vector as pandas DataFrame with correct column names
        feature_vector = pd.DataFrame([
            [features.get(feat, 0) for feat in feature_names]
        ], columns=feature_names)

        # Make prediction
        prediction = model.predict(feature_vector)[0]
        probability = model.predict_proba(feature_vector)[0]

        # Add prediction to response
        features['prediction'] = int(prediction)
        features['malicious_probability'] = float(probability[1])

        write_to_log(f"Successfully processed domain: {features.get('domain', 'unknown')}")
        write_to_log(f"Prediction: {features['prediction']}, Probability: {features['malicious_probability']}")
        return jsonify(features), 200

    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        write_to_log(error_msg)
        return jsonify({
            'error': error_msg,
            'prediction': 0,
            'malicious_probability': 0
        }), 500


if __name__ == '__main__':
    # Make sure the log directory exists
    create_log_dir()

    # Write startup message to the log file (this will not affect feature extraction)
    write_to_log("ML container started")

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
