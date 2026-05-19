"""
Security Preprocessor and Inference Engine.

High level role: Orchestrates the security pipeline:
1. Filters: Normalization, Base64 decoding, Fuzzy matching.
2. Classification: Uses pre-trained Bayesian models to calculate risk.
"""
import base64
import os
import re

import joblib
from rapidfuzz import fuzz, process

from backend.security.constants import FUZZY_PATTERNS, MAX_TEXT_LENGTH, MIN_WORD_LENGTH


class SecurityPreprocessor:  # pylint: disable=too-few-public-methods
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
        """Normalizes whitespace and reconstructs spaced-out obfuscation."""
        # Standardize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Reconstruct spaced-out words (e.g., 'm a l w a r e')
        text = self._reconstruct_spaced_text(text)

        # Standard character repetition cleanup
        text = re.sub(r'(.)\1{3,}', r'\1', text)

        return text

    def _reconstruct_spaced_text(self, text: str) -> str:
        """
        Detects and joins sequences of single-character 'spaced' words.

        High level role: This is a defensive filter against token-splitting attacks
        where an attacker injects spaces between characters to bypass simple filters
        (e.g., 'm a l w a r e'). It identifies chains of 3 or more single-character
        tokens and collapses the spaces between them to reconstruct the original
        word for the classifier. It is designed to ignore natural language patterns
        like 'I am' or 'a lion' by requiring a minimum chain length of 3.

        Args:
            text (str): The normalized string to process.

        Returns:
            str: The text with obfuscated word chains reconstructed.

        Examples:
            >>> _reconstruct_spaced_text("c r e a t e  m a l w a r e")
            "create malware"
            >>> _reconstruct_spaced_text("I am a lion")
            "I am a lion"
        """
        def de_space_match(match):
            return match.group(0).replace(" ", "")

        # Regex: finds 3 or more single-character words separated by spaces
        return re.sub(r'(?i)\b\w(?:\s\w){2,}\b', de_space_match, text)

    def _decode_base64(self, text: str) -> str:
        """Attempts to find and decode Base64 strings."""
        def b64_repl(match):
            try:
                decoded = base64.b64decode(match.group(0)).decode('utf-8', errors='ignore')
                return f" {decoded} " if len(decoded) > 5 else match.group(0)
            except Exception:  # pylint: disable=broad-exception-caught
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
