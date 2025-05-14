import pandas as pd
import dns.resolver
import requests
import math
import concurrent.futures
from datetime import datetime
import os
import ipaddress
import tldextract


def get_domains_from_feed(url, timeout=10):
    """Safely fetch domains from a threat feed URL"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return [d.strip() for d in response.text.split('\n') if d.strip()]
    except Exception as e:
        print(f"Error fetching from {url}: {e}")
    return []


def get_alexa_top_domains(limit=1000):
    """Get top legitimate domains from Tranco list"""
    fallback_domains = [
        'google.com', 'microsoft.com', 'amazon.com', 'apple.com',
        'facebook.com', 'youtube.com', 'twitter.com', 'linkedin.com',
        'github.com', 'reddit.com', 'netflix.com', 'instagram.com',
        'wordpress.com', 'wikipedia.org', 'yahoo.com', 'adobe.com'
    ]
    try:
        url = "https://tranco-list.eu/download/KJN8W/1000000"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            domains = []
            for line in response.text.split('\n')[1:]:
                if ',' in line:
                    _, domain = line.strip().split(',')
                    domains.append(domain)
            if domains:
                print(f"Loaded {len(domains)} domains from Tranco list")
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
    malicious = set()
    for feed in feeds:
        domains = get_domains_from_feed(feed)
        malicious.update(domains)
    return list(malicious)


def calculate_entropy(s):
    """Calculate Shannon entropy of a string"""
    probs = [float(s.count(c)) / len(s) for c in dict.fromkeys(list(s))]
    return -sum(p * math.log(p, 2) for p in probs if p > 0)


def is_ip_address(host):
    """Check if the host is a valid IP address"""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def extract_features_from_domain(domain):
    """Extract DNS and string features from a domain or IP address"""
    features = {'domain': domain}

    # 1) IP address flagging
    if is_ip_address(domain):
        features['is_ip'] = True
        # Default DNS-based features
        features.update({
            'dns_record_type': 0,
            'ip_count': 1,
            'has_mx_response': False,
            'has_txt_dns_response': False,
            'has_spf_info': False,
            'has_dkim_info': False,
            'has_dmarc_info': False,
        })
        # String metrics on IP literal
        features['domain_length'] = len(domain)
        features['subdomain_count'] = 0
        features['domain_entropy'] = calculate_entropy(domain)
        return features

    features['is_ip'] = False

    # 2) Parse with tldextract for subdomain vs. registered domain
    ext = tldextract.extract(domain)
    sub = ext.subdomain or ''
    reg = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain

    features['registered_domain'] = reg
    features['subdomain_count'] = 0 if sub == '' else len(sub.split('.'))

    # 3) String-based features
    features['domain_length'] = len(domain)
    features['registered_length'] = len(reg)
    features['subdomain_length'] = len(sub)
    features['domain_entropy'] = calculate_entropy(domain)
    features['registered_entropy'] = calculate_entropy(reg)
    features['subdomain_entropy'] = calculate_entropy(sub) if sub else 0
    features['numeric_ratio'] = sum(c.isdigit() for c in domain) / len(domain)
    features['special_char_ratio'] = sum(not c.isalnum() for c in domain) / len(domain)
    features['vowel_ratio'] = sum(c.lower() in 'aeiou' for c in domain) / len(domain)
    features['consonant_ratio'] = sum(c.lower() in 'bcdfghjklmnpqrstvwxyz' for c in domain) / len(domain)

    # 4) DNS resolution with strict timeouts
    resolver = dns.resolver.Resolver()
    resolver.timeout = resolver.lifetime = 1

    # A records
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

    # MX record
    try:
        resolver.resolve(domain, 'MX')
        features['has_mx_response'] = True
    except Exception:
        features['has_mx_response'] = False

    # TXT record & SPF/DKIM/DMARC
    try:
        txt_records = resolver.resolve(domain, 'TXT')
        txt_concat = "".join(str(r) for r in txt_records)
        features['has_txt_dns_response'] = True
        features['has_spf_info'] = 'spf' in txt_concat.lower()
        features['has_dkim_info'] = 'dkim' in txt_concat.lower()
        features['has_dmarc_info'] = 'dmarc' in txt_concat.lower()
    except Exception:
        features['has_txt_dns_response'] = False
        features['has_spf_info'] = False
        features['has_dkim_info'] = False
        features['has_dmarc_info'] = False

    return features


def create_dataset(benign_limit=1000, malicious_limit=1000):
    """Create balanced dataset of benign and malicious domains/IPs"""
    print("Fetching domain lists...")

    # Base benign list
    benign = [
        'google.com', 'microsoft.com', 'rtu.lv', 'lu.lv',
        'apple.com', 'github.com', 'youtube.com', 'linkedin.com'
    ]
    benign.extend(get_alexa_top_domains(benign_limit))
    benign = list(dict.fromkeys(benign))[:benign_limit]

    malicious = get_malicious_domains()[:malicious_limit]

    total = len(benign) + len(malicious)
    print(f"Processing {len(benign)} benign + {len(malicious)} malicious domains... Total = {total}")

    results = []
    count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_map = {
            executor.submit(extract_features_from_domain, d): (d, 0)
            for d in benign
        }
        future_map.update({
            executor.submit(extract_features_from_domain, d): (d, 1)
            for d in malicious
        })

        for fut in concurrent.futures.as_completed(future_map):
            domain, label = future_map[fut]
            try:
                feats = fut.result()
                feats['label'] = label
                results.append(feats)
            except Exception as e:
                print(f"Error on {domain}: {e}")
            count += 1
            print(f"\rProgress: {(count/total)*100:.1f}% ({count}/{total})", end='')

    print("\nBuilding DataFrame...")
    df = pd.DataFrame(results)

    # Save CSV
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(os.getcwd(), f'dns_dataset_{ts}.csv')
    df.to_csv(out, index=False)

    print("Dataset created!")
    print(f"- Samples: {len(df)}")
    print(f"- Benign: {len(df[df['label']==0])}")
    print(f"- Malicious: {len(df[df['label']==1])}")
    print(f"- Features: {', '.join(df.columns)}")
    print(f"- Saved to: {out}")


if __name__ == '__main__':
    create_dataset(benign_limit=10000, malicious_limit=10000)
