import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

# Load the dataset
df = pd.read_csv('Application\ml-model\BenignAndMaliciousDataset.csv')

# Define features with proper DataFrame
features = [
    'TXTDnsResponse', 'NumericRatio', 'SpecialCharRatio', 'VowelRatio', 'ConsoantRatio',
    'DNSRecordNum', 'MXDnsResponse', 'HasSPFInfo', 'HasDkimInfo',
    'HasDmarcInfo', 'HttpResponseCode', 'ConsoantSequence', 'VowelSequence',
    'NumericSequence', 'SpecialCharSequence', 'EntropyOfSubDomains'
]

X = df[features].copy()  # Create explicit copy with features
y = df['Class']

# Split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the model
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# Print model performance
y_pred = rf_model.predict(X_test)
print(classification_report(y_test, y_pred))

# Save both model and feature names
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'dns_classifier.joblib')

# Save as dictionary containing both model and features
model_dict = {
    'model': rf_model,
    'features': features
}

joblib.dump(model_dict, model_path)
print(f"Model and features saved to: {model_path}")