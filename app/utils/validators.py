"""Input validation functions for the application.

This module provides validation functions for common data types
such as phone numbers, email addresses, GST numbers, and more.
"""

from __future__ import annotations

import re
from typing import Optional


# Indian phone number patterns
_PHONE_REGEX = re.compile(r"^(\+91[\-\s]?)?[0]?(91)?[6-9]\d{9}$")
# GSTIN format: 2 digits state code, 10 digit PAN, 1 digit entity type, 1 digit checksum, 1 char default
_GST_REGEX = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$"
)
# Email pattern
_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)
# PAN format: 5 letters, 4 digits, 1 letter
_PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
# IFSC format: 4 letters bank code, 0, 6 digit branch code
_IFSC_REGEX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def validate_email(email: str, *, allow_empty: bool = False) -> tuple[bool, Optional[str]]:
    """Validate an email address.

    Args:
        email: The email address to validate.
        allow_empty: If True, empty string is considered valid.

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)

    Example:
        >>> valid, error = validate_email("test@example.com")
        >>> print(valid)
        True
    """
    if allow_empty and email == "":
        return True, None

    if not email or not isinstance(email, str):
        return False, "Email is required"

    email = email.strip()
    if len(email) > 254:
        return False, "Email is too long (max 254 characters)"

    if not _EMAIL_REGEX.match(email):
        return False, "Invalid email format"

    # Additional checks
    local, _, domain = email.partition("@")
    if len(local) > 64:
        return False, "Local part of email is too long (max 64 characters)"

    if domain and not re.search(r"\.[a-zA-Z]{2,}$", domain):
        return False, "Domain must have a valid TLD"

    return True, None


def validate_phone_india(phone: str, *, allow_empty: bool = False) -> tuple[bool, Optional[str]]:
    """Validate an Indian phone number.

    Supports various formats:
    - 10-digit: 9876543210
    - With leading 0: 09876543210
    - With country code: +919876543210
    - With country code and space/hyphen: +91-9876543210, +91 9876543210

    Args:
        phone: The phone number to validate.
        allow_empty: If True, empty string is considered valid.

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)

    Example:
        >>> valid, error = validate_phone_india("+91-9876543210")
        >>> print(valid)
        True
    """
    if allow_empty and phone == "":
        return True, None

    if not phone or not isinstance(phone, str):
        return False, "Phone number is required"

    phone = phone.strip()

    if not _PHONE_REGEX.match(phone):
        return False, "Invalid Indian phone number format"

    # Extract digits only
    digits = re.sub(r"\D", "", phone)
    if len(digits) != 10:
        return False, "Phone number must have 10 digits"

    return True, None


def validate_gstin(gstin: str, *, allow_empty: bool = False) -> tuple[bool, Optional[str]]:
    """Validate a GSTIN (Goods and Services Tax Identification Number).

    Indian GSTIN format:
    - First 2 digits: State code
    - Next 10 digits: PAN (5 letters + 4 digits + 1 letter)
    - 13th digit: Entity type
    - 14th digit: Checksum alphabet (default Z)
    - 15th digit: Checksum digit or alphabet

    Args:
        gstin: The GSTIN to validate.
        allow_empty: If True, empty string is considered valid.

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)

    Example:
        >>> valid, error = validate_gstin("27AABCS9921R1ZD")
        >>> print(valid)
        True
    """
    if allow_empty and gstin == "":
        return True, None

    if not gstin or not isinstance(gstin, str):
        return False, "GSTIN is required"

    gstin = gstin.strip().upper()

    if len(gstin) != 15:
        return False, "GSTIN must be exactly 15 characters"

    if not _GST_REGEX.match(gstin):
        return False, "Invalid GSTIN format"

    # Validate checksum using mod-36 algorithm
    if not _validate_gstin_checksum(gstin):
        return False, "GSTIN checksum validation failed"

    return True, None


def _validate_gstin_checksum(gstin: str) -> bool:
    """Internal: Validate GSTIN checksum using mod-36 algorithm.

    Args:
        gstin: The 15-character GSTIN.

    Returns:
        bool: True if checksum is valid, False otherwise.
    """
    if len(gstin) != 15:
        return False

    # Characters for base-36 conversion
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    try:
        # Convert first 14 chars to base-36 and compute mod 36
        total = 0
        for char in gstin[:14]:
            value = chars.index(char)
            total = (total * 36 + value) % 36

        # Last character should equal (36 - total_mod) mod 36
        check_char = gstin[14]
        expected_index = (36 - (total % 36)) % 36
        expected_char = chars[expected_index]

        return check_char == expected_char
    except (ValueError, IndexError):
        return False


def validate_pan(pan: str, *, allow_empty: bool = False) -> tuple[bool, Optional[str]]:
    """Validate an Indian PAN (Permanent Account Number).

    Format: 5 uppercase letters + 4 digits + 1 uppercase letter

    Args:
        pan: The PAN to validate.
        allow_empty: If True, empty string is considered valid.

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)

    Example:
        >>> valid, error = validate_pan("AABCS1234X")
        >>> print(valid)
        True
    """
    if allow_empty and pan == "":
        return True, None

    if not pan or not isinstance(pan, str):
        return False, "PAN is required"

    pan = pan.strip().upper()

    if len(pan) != 10:
        return False, "PAN must be exactly 10 characters"

    if not _PAN_REGEX.match(pan):
        return False, "Invalid PAN format"

    # The 4th character indicates holder type
    holder_type = pan[3]
    valid_types = {"A", "B", "C", "F", "G", "H", "L", "J", "P", "T"}
    if holder_type not in valid_types:
        return False, f"Invalid PAN holder type: {holder_type}"

    return True, None


def validate_ifsc(ifsc: str, *, allow_empty: bool = False) -> tuple[bool, Optional[str]]:
    """Validate an Indian IFSC (Indian Financial System Code).

    Format: 4 letters (bank code) + 0 + 6 alphanumeric characters (branch code)

    Args:
        ifsc: The IFSC code to validate.
        allow_empty: If True, empty string is considered valid.

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)

    Example:
        >>> valid, error = validate_ifsc("SBIN0005900")
        >>> print(valid)
        True
    """
    if allow_empty and ifsc == "":
        return True, None

    if not ifsc or not isinstance(ifsc, str):
        return False, "IFSC is required"

    ifsc = ifsc.strip().upper()

    if len(ifsc) != 11:
        return False, "IFSC must be exactly 11 characters"

    if not _IFSC_REGEX.match(ifsc):
        return False, "Invalid IFSC format"

    return True, None


def validate_aadhaar(aadhaar: str, *, allow_empty: bool = False) -> tuple[bool, Optional[str]]:
    """Validate an Indian Aadhaar number using Verhoeff algorithm.

    Args:
        aadhaar: The 12-digit Aadhaar number to validate.
        allow_empty: If True, empty string is considered valid.

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)

    Example:
        >>> valid, error = validate_aadhaar("123456789012")
        >>> print(valid)
        True
    """
    if allow_empty and aadhaar == "":
        return True, None

    if not aadhaar or not isinstance(aadhaar, str):
        return False, "Aadhaar number is required"

    aadhaar = aadhaar.strip()

    if not aadhaar.isdigit():
        return False, "Aadhaar must contain only digits"

    if len(aadhaar) != 12:
        return False, "Aadhaar must be exactly 12 digits"

    # Verhoeff algorithm for checksum validation
    return _verhoeff_validate(aadhaar)


def _verhoeff_validate(number: str) -> tuple[bool, Optional[str]]:
    """Validate a number using Verhoeff algorithm.

    Args:
        number: The number string to validate.

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Verhoeff multiplication table
    d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
    ]

    # Permutation table
    inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

    try:
        digits = [int(d) for d in number]
        check = 0
        for i, digit in enumerate(reversed(digits)):
            check = d[check][inv[(i + 1) % 8] * digit % 10]
        return check == 0, None if check == 0 else "Invalid checksum"
    except (ValueError, IndexError):
        return False, "Invalid number format"
