"""
Self-contained Training Script for the Bayesian Security Model.

High level role: Trains the Complement Naive Bayes model using the 
local corpus.json and exports artifacts to the backend.
"""
import os
import json
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import ComplementNB

def train():
    """Trains and saves the model artifacts."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_path = os.path.join(current_dir, "corpus.json")
    # Output to the backend's model directory
    output_dir = os.path.join(current_dir, "..", "src", "backend", "security", "models")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading corpus: {corpus_path}")
    with open(corpus_path, 'r') as f:
        data = json.load(f)
        
    train_data = [item for item in data if item.get('split') == 'train']
    print(f"Training on {len(train_data)} samples...")
    
    texts = [item['text'] for item in train_data]
    labels = [1 if item['label'] == 'injection' else 0 for item in train_data]
    
    print("Training model...")
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), analyzer='char_wb')
    X = vectorizer.fit_transform(texts)
    
    model = ComplementNB()
    model.fit(X, labels)
    
    print(f"Exporting to: {output_dir}")
    joblib.dump(vectorizer, os.path.join(output_dir, "vectorizer.joblib"))
    joblib.dump(model, os.path.join(output_dir, "model.joblib"))
    print("Success!")

if __name__ == "__main__":
    train()
