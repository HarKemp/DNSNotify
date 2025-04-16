import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os
import glob

def train_model():
    # Find the most recent dataset
    dataset_files = glob.glob(os.path.join(os.path.dirname(__file__), 'dns_dataset_*.csv'))
    if not dataset_files:
        raise FileNotFoundError("No dataset files found. Run create_dataset.py first.")
    
    latest_dataset = max(dataset_files)
    print(f"Using dataset: {latest_dataset}")

    # Load the dataset
    df = pd.read_csv(latest_dataset)
    
    # Define features to use (matching the features we extract in main.py)
    features = [
        'domain_length', 'domain_entropy',
        'numeric_ratio', 'special_char_ratio', 
        'vowel_ratio', 'consonant_ratio',
        'dns_record_type', 'ip_count',
        'has_mx_response', 'has_txt_dns_response',
        'has_spf_info', 'has_dkim_info', 'has_dmarc_info'
    ]
    
    # Prepare features and target
    X = df[features].copy()
    y = df['label']
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train Random Forest model
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42
    )
    
    rf_model.fit(X_train, y_train)
    
    # Evaluate the model
    y_pred = rf_model.predict(X_test)
    print("\nModel Performance:")
    print("=================")
    print(classification_report(y_test, y_pred))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': features,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\nFeature Importance:")
    print("==================")
    print(feature_importance)
    
    # Save the model with features list
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'dns_classifier.joblib')
    
    model_dict = {
        'model': rf_model,
        'features': features
    }
    
    joblib.dump(model_dict, model_path)
    print(f"\nModel saved to: {model_path}")

if __name__ == "__main__":
    train_model()