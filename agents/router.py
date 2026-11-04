"""
Intelligent Intent Router Module.

Classifies incoming user requests into:
1. QUESTION -> User asking about content (RAG retrieval pipeline)
2. MODIFICATION -> User requesting a change to document content
3. CLARIFICATION -> Ambiguous or incomplete prompt
4. UNSUPPORTED_OPERATION -> Malicious, unsafe, or unsupported system commands
"""

import re
from typing import Dict, Any


def classify_user_intent(user_input: str) -> Dict[str, Any]:
    """
    Classifies intent using high-precision pattern recognition and intent rules.
    Returns structured JSON with classification, confidence, and reasoning.
    """
    text = user_input.strip()
    lower = text.lower()

    # 1. Check for Unsupported or Unsafe Operations
    unsafe_keywords = ["rm -rf", "drop table", "shutdown", "format disk", "eval(", "exec(", "cmd.exe", "powershell"]
    if any(k in lower for k in unsafe_keywords):
        return {
            "intent": "UNSUPPORTED_OPERATION",
            "confidence": 0.99,
            "reasoning": "The request contains system-level commands or unsupported unsafe code execution."
        }

    # 2. Check for Ambiguous / Clarification Needed
    clean_lower = re.sub(r"[^\w\s]", "", lower).strip()
    clarification_phrases = [
        "change that", "update it", "do it", "fix it", "change value",
        "change that value", "update that", "modify that", "fix that", "do change"
    ]
    if clean_lower in clarification_phrases or (len(clean_lower.split()) <= 3 and any(p == clean_lower for p in clarification_phrases)):
        return {
            "intent": "CLARIFICATION",
            "confidence": 0.95,
            "reasoning": "The instruction is ambiguous. Please specify which document, value, or text you want to change."
        }

    # 3. Check for Modification Intent
    mod_triggers = [
        "modify", "update", "change", "replace", "delete", "remove", "add column",
        "remove duplicate", "sort", "append", "set cell", "insert formula", "extract page",
        "extract", "merge pdf", "merge", "annotate", "annotation", "stamp"
    ]

    cell_pattern = bool(re.search(r"\b[A-Za-z]+[1-9][0-9]*\b", text))

    if any(t in lower for t in mod_triggers) or ("set" in lower and cell_pattern):
        return {
            "intent": "MODIFICATION",
            "confidence": 0.92,
            "reasoning": "The user is requesting an actionable, controlled edit to a document."
        }

    # 4. Default: Question Answering (RAG)
    return {
        "intent": "QUESTION",
        "confidence": 0.90,
        "reasoning": "The user is asking a factual question about documents in the workspace."
    }

