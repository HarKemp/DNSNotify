import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os
import glob


def train_model():
    #Locate the most recent dataset
    dataset_files = glob.glob(os.path.join(os.path.dirname(__file__), 'dns_dataset_*.csv'))
    if not dataset_files:
        raise FileNotFoundError("No dataset files found. Run create_dataset.py first.")

    #latest_dataset = max(dataset_files)
    latest_dataset = '/content/dns_dataset_20250514_075116.csv'
    print(f"Using dataset: {latest_dataset}")

    # Load the dataset
    df = pd.read_csv(latest_dataset)

    # Define numeric features matching extract_features_from_domain
    features = [
        'domain_length', 'registered_length', 'subdomain_length',
        'domain_entropy', 'registered_entropy', 'subdomain_entropy',
        'numeric_ratio', 'special_char_ratio', 'vowel_ratio', 'consonant_ratio',
        'subdomain_count', 'is_ip',
        'dns_record_type', 'ip_count',
        'has_mx_response', 'has_txt_dns_response',
        'has_spf_info', 'has_dkim_info', 'has_dmarc_info'
    ]

    # Ensure boolean columns are numeric
    bool_cols = [c for c in features if df[c].dtype == 'bool']
    for col in bool_cols:
        df[col] = df[col].astype(int)

    # Prepare features and target
    X = df[features].copy()
    y = df['label']

    # Handle any missing values by filling with zeros
    X.fillna(0, inplace=True)

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train Random Forest model
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)

    # Evaluate the model
    y_pred = rf_model.predict(X_test)
    print("\nModel Performance:")
    print("=================")
    print(classification_report(y_test, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Feature importance
    fi = pd.DataFrame({
        'feature': features,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)
    print("\nFeature Importance:")
    print(fi)

    # Save the model and feature list
    model_dict = {
        'model': rf_model,
        'features': features
    }
    model_path = os.path.join(os.path.dirname(__file__), 'dns_classifier.joblib')
    #model_path = '/content/dns_classifier.joblib'
    joblib.dump(model_dict, model_path)
    print(f"\nModel saved to: {model_path}")


if __name__ == "__main__":
    train_model()
