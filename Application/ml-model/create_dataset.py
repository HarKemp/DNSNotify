import pandas as pd
import dns.resolver
import requests
import math
import concurrent.futures
from datetime import datetime
import os
import time

def get_domains_from_feed(url, timeout=10):
    """Safely fetch domains from a threat feed URL"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            # Split by newlines and filter empty lines
            return [d.strip() for d in response.text.split('\n') if d.strip()]
    except Exception as e:
        print(f"Error fetching from {url}: {e}")
    return []

def get_alexa_top_domains(limit=1000):
    """Get top legitimate domains from Tranco list"""
    # Fallback domains in case of errors
    fallback_domains = [
        'google.com', 'microsoft.com', 'amazon.com', 'apple.com',
        'facebook.com', 'youtube.com', 'twitter.com', 'linkedin.com',
        'github.com', 'reddit.com', 'netflix.com', 'instagram.com',
        'wordpress.com', 'wikipedia.org', 'yahoo.com', 'adobe.com'
    ]
    
    try:
        # Direct download of CSV from Tranco
        url = "https://tranco-list.eu/download/KJN8W/1000000"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # Parse CSV content (rank,domain format)
            domains = []
            for line in response.text.split('\n')[1:]:  # Skip header
                if ',' in line:
                    rank, domain = line.strip().split(',')
                    domains.append(domain)
            if domains:
                print(f"Successfully loaded {len(domains)} domains from Tranco list")
                return domains[:limit]
    
    except Exception as e:
        print(f"Error fetching Tranco list: {e}")
    
    print("Using fallback domain list")
    return fallback_domains[:limit]

def get_malicious_domains():
    """Get malicious domains from various threat feeds"""
    feeds = [
        "https://urlhaus.abuse.ch/downloads/text/",
        "https://openphish.com/feed.txt",
        "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-domains-ACTIVE.txt"
    ]
    
    malicious_domains = set()
    for feed in feeds:
        domains = get_domains_from_feed(feed)
        malicious_domains.update(domains)
    
    return list(malicious_domains)

def calculate_entropy(s):
    """Calculate Shannon entropy of a string"""
    probabilities = [float(s.count(c)) / len(s) for c in dict.fromkeys(list(s))]
    return -sum([p * math.log(p, 2) for p in probabilities if p > 0])

def extract_features_from_domain(domain):
    """Extract DNS and string features from a domain"""
    features = {}
    try:
        features['domain'] = domain
        
        # String-based features
        features['domain_length'] = len(domain)
        features['domain_entropy'] = calculate_entropy(domain)
        features['numeric_ratio'] = sum(c.isdigit() for c in domain) / len(domain)
        features['special_char_ratio'] = sum(not c.isalnum() for c in domain) / len(domain)
        features['vowel_ratio'] = sum(c.lower() in 'aeiou' for c in domain) / len(domain)
        features['consonant_ratio'] = sum(c.lower() in 'bcdfghjklmnpqrstvwxyz' for c in domain) / len(domain)
        
        # Configure DNS resolver with strict timeouts
        resolver = dns.resolver.Resolver()
        resolver.timeout = 1
        resolver.lifetime = 1
        
        # DNS record features
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
        
        return features
        
    except Exception as e:
        print(f"Error processing {domain}: {str(e)}")
        return None

def create_dataset(benign_limit=1000, malicious_limit=1000):
    """Create balanced dataset of benign and malicious domains"""
    print("Fetching domain lists...")
    
    # Get benign domains from your trusted list
    benign_domains = [
        'google.com', 'microsoft.com', 'rtu.lv', 'lu.lv', 
        'apple.com', 'github.com', 'youtube.com', 'linkedin.com'
    ]
    
    # Add more benign domains from Alexa/Tranco list
    benign_domains.extend(get_alexa_top_domains(benign_limit))
    benign_domains = list(set(benign_domains))[:benign_limit]
    
    # Get malicious domains from threat feeds
    malicious_domains = get_malicious_domains()[:malicious_limit]
    
    print(f"Processing {len(benign_domains)} benign and {len(malicious_domains)} malicious domains...")
    
    results = []
    total_domains = len(benign_domains) + len(malicious_domains)
    processed_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # Process benign domains
        future_to_domain = {
            executor.submit(extract_features_from_domain, domain): (domain, 0)
            for domain in benign_domains
        }
        
        # Process malicious domains
        future_to_domain.update({
            executor.submit(extract_features_from_domain, domain): (domain, 1)
            for domain in malicious_domains
        })
        
        for future in concurrent.futures.as_completed(future_to_domain):
            domain, label = future_to_domain[future]
            try:
                features = future.result()
                if features:
                    features['label'] = label
                    results.append(features)
                processed_count += 1
                
                # Calculate and print progress
                progress = (processed_count / total_domains) * 100
                print(f"\rProgress: {progress:.1f}% ({processed_count}/{total_domains} domains processed)", end="")
            except Exception as e:
                print(f"\nError processing {domain}: {e}")
                processed_count += 1
    
    print("\n")  # New line after progress bar
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(os.path.dirname(__file__), f'dns_dataset_{timestamp}.csv')
    df.to_csv(output_file, index=False)
    
    print(f"\nDataset created successfully:")
    print(f"- Total samples: {len(df)}")
    print(f"- Benign samples: {len(df[df['label'] == 0])}")
    print(f"- Malicious samples: {len(df[df['label'] == 1])}")
    print(f"- Features: {', '.join(df.columns)}")
    print(f"- Saved to: {output_file}")

if __name__ == "__main__":
    create_dataset(benign_limit=10000, malicious_limit=10000)