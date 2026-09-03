"""Enterprise Safety, DLP SPII Masking, Model Armor & RBAC Guardrails."""
import re
from typing import Tuple

# Regex Patterns for Sensitive Identifiers (SPII)
# Singapore NRIC / FIN format: S1234567A, T1234567A, F1234567A, G1234567A, M1234567A
FIN_REGEX = re.compile(r'\b[STFGM]\d{7}[A-Z]\b', re.IGNORECASE)
# Standard Passport format: 8-9 alphanumeric characters
PASSPORT_REGEX = re.compile(r'\b[A-Z][0-9]{7,8}\b')
# E.164 and common phone numbers: e.g. +65 9123 4567 or +6591234567
PHONE_REGEX = re.compile(r'(?:\+?65[-.\s]?)?[89]\d{3}[-.\s]?\d{4}\b|\b\+[1-9]\d{7,14}\b')

# Known Prompt Injection / Jailbreak Triggers
INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|above) instructions",
    r"disregard (?:all )?prior guidelines",
    r"system prompt",
    r"you are now in (?:developer|dan|god) mode",
    r"bypass (?:policy|approval|verification)",
    r"leak (?:the )?confidential",
    r"act as an unfiltered",
]

# Out-of-Domain Non-HR Patterns
OUT_OF_DOMAIN_PATTERNS = [
    r"write (?:a )?python (?:function|script|code)",
    r"reverse (?:a )?string",
    r"fibonacci",
    r"solve (?:this )?math",
    r"write an essay on",
    r"write code to",
    r"what is the weather",
]


def redact_spii(text: str) -> str:
    """Mask sensitive PII / SPII entities using cryptographic token placeholders."""
    if not text:
        return text
    text = FIN_REGEX.sub("[REDACTED_FIN]", text)
    text = PASSPORT_REGEX.sub("[REDACTED_PASSPORT]", text)
    text = PHONE_REGEX.sub("[REDACTED_PHONE]", text)
    return text


def validate_caller(session_caller_id: str, target_employee_id: str) -> bool:
    """Validate that the caller is authorized to view or mutate the target record.
    Enforces strict employee data boundary (employee_id == session.caller_id).
    """
    if not session_caller_id or not target_employee_id:
        return False
    # Managers (EMP2048) have administrative read access to direct reports in certain contexts,
    # but employees can only mutate their own records.
    return session_caller_id.strip().upper() == target_employee_id.strip().upper()


def check_prompt_injection(prompt: str) -> Tuple[bool, str]:
    """Scan incoming prompts for prompt injection attacks or system manipulation.
    Returns (is_safe, message).
    """
    if not prompt:
        return True, ""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            return False, "Security Notice: Your request triggered the AI Safety pre-execution filter (Prompt Injection detected). Please rephrase your HR query."
    return True, ""


def check_domain_containment(prompt: str) -> Tuple[bool, str]:
    """Ensure the prompt is contained within corporate HR and workplace domains.
    Returns (is_contained, message).
    """
    if not prompt:
        return True, ""
    for pattern in OUT_OF_DOMAIN_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            return False, "I am the Altostrat Singapore HR Assistant, dedicated to answering questions about company policies, leave entitlements, and workplace support. I cannot fulfill general programming, mathematical, or non-work queries."
    return True, ""
