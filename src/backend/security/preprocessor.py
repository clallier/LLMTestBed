"""
Security Preprocessor and Inference Engine.

High level role: Orchestrates the security pipeline:
1. Filters: Normalization, Base64 decoding, Fuzzy matching.
2. Classification: Uses pre-trained Bayesian models to calculate risk.
"""
import re
import base64
import os
import joblib
from rapidfuzz import process, fuzz
from backend.security.constants import FUZZY_PATTERNS, MAX_TEXT_LENGTH, MIN_WORD_LENGTH

class SecurityPreprocessor:
    """Hybrid security engine for cleaning and scoring prompts."""

    def __init__(self):
        """Initializes filters and loads the trained Bayesian model."""
        model_dir = os.path.join(os.path.dirname(__file__), "models")
        self._vectorizer_path = os.path.join(model_dir, "vectorizer.joblib")
        self._model_path = os.path.join(model_dir, "model.joblib")
        
        self._vectorizer = None
        self._model = None
        self._load_model_artifacts()

    def calculate_risk(self, text: str) -> float:
        """Runs the text through filters and returns a risk score.
        
        Args:
            text (str): Raw input text.
            
        Returns:
            float: Risk probability (0.0 to 1.0).
        """
        if not self._model or not self._vectorizer:
            return 0.0
            
        # 1. Apply Filters
        cleaned_text = self._apply_filters(text)
        
        # 2. Vectorize and Predict
        vectorized = self._vectorizer.transform([cleaned_text])
        return float(self._model.predict_proba(vectorized)[0][1])

    def _apply_filters(self, text: str) -> str:
        """Applies normalization, decoding, and fuzzy typoglycemia fixes."""
        if not text:
            return ""
            
        text = text[:MAX_TEXT_LENGTH]
        text = self._normalize(text)
        text = self._decode_base64(text)
        text = self._fix_typoglycemia(text)
        return text.lower()

    def _normalize(self, text: str) -> str:
        """Normalizes whitespace and character repetitions."""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(.)\1{3,}', r'\1', text)
        return text

    def _decode_base64(self, text: str) -> str:
        """Attempts to find and decode Base64 strings."""
        def b64_repl(match):
            try:
                decoded = base64.b64decode(match.group(0)).decode('utf-8', errors='ignore')
                return f" {decoded} " if len(decoded) > 5 else match.group(0)
            except Exception:
                return match.group(0)
        
        return re.sub(r'[A-Za-z0-9+/]{8,}={0,2}', b64_repl, text)

    def _fix_typoglycemia(self, text: str) -> str:
        """Maps scrambled words back using RapidFuzz."""
        words = text.split()
        fixed_words = [self._get_fuzzy_match(w) for w in words]
        return " ".join(fixed_words)

    def _get_fuzzy_match(self, word: str) -> str:
        """Finds the closest match from FUZZY_PATTERNS."""
        if len(word) < MIN_WORD_LENGTH:
            return word
            
        match = process.extractOne(word.lower(), FUZZY_PATTERNS, scorer=fuzz.WRatio)
        return match[0] if match and match[1] > 80 else word

    def _load_model_artifacts(self):
        """Loads joblib artifacts from the models directory."""
        if os.path.exists(self._vectorizer_path) and os.path.exists(self._model_path):
            self._vectorizer = joblib.load(self._vectorizer_path)
            self._model = joblib.load(self._model_path)
