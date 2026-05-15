"""
Security Constants for the LLM Testbed.

High level role: Centralizes all security-related configuration, including 
fuzzy patterns for typoglycemia detection and risk score thresholds.
"""

# Patterns for fuzzy matching (typoglycemia defense)
FUZZY_PATTERNS = [
    "ignore", 
    "bypass", 
    "override", 
    "reveal", 
    "delete", 
    "system", 
    "jailbreak",
    "developer",
    "password",
    "secret"
]

# Risk score thresholds for visual feedback
RISK_THRESHOLDS = {
    "HIGH": 0.8,
    "MEDIUM": 0.4,
    "LOW": 0.1
}

# Preprocessing Constants
MAX_TEXT_LENGTH = 10000
MIN_WORD_LENGTH = 3
