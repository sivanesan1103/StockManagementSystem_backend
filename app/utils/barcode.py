"""Barcode and QR code generation utilities.

This module provides functions to generate various types of barcodes
and QR codes using the python-barcode and qrcode libraries.

Supported barcode types:
    - EAN-13
    - EAN-8
    - UPC-A
    - Code128
    - Code39
    - ITF
    - QR Code

All generated images are returned as bytes in PNG format by default.
"""

from __future__ import annotations

import io
from typing import Optional, Union

import barcode
from barcode.errors import IllegalCharacterError, BarcodeError
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from PIL import Image

from .helpers import generate_uuid

__all__ = [
    "generate_barcode",
    "generate_qr_code",
    "ErrorCorrectionLevel",
]

# Type alias for error correction levels
ErrorCorrectionLevel = Union[ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H]


def generate_barcode(
    code: str,
    barcode_type: str = "ean13",
    writer_options: Optional[dict] = None,
    add_checksum: bool = True,
) -> bytes:
    """Generate a barcode image.

    Args:
        code: The data to encode. For EAN-13, must be 12-13 digits; for EAN-8, 7-8 digits;
            for UPC-A, 11-12 digits; for Code128, any ASCII string.
        barcode_type: Type of barcode to generate. Supported types:
            - "ean13" (default): EAN-13 barcode
            - "ean8": EAN-8 barcode
            - "upca": UPC-A barcode
            - "code128": Code 128 barcode
            - "code39": Code 39 barcode
            - "itf": ITF barcode
        writer_options: Optional dict of writer options (e.g., {"module_width": 0.2, "module_height": 15.0})
        add_checksum: Whether to automatically add/verify checksum (default: True).

    Returns:
        bytes: PNG image data as bytes.

    Raises:
        ValueError: If code is invalid or barcode_type is unsupported.
        BarcodeError: If barcode generation fails.

    Example:
        >>> barcode_bytes = generate_barcode("123456789012")
        >>> with open("barcode.png", "wb") as f:
        ...     f.write(barcode_bytes)
    """
    if not code or not isinstance(code, str):
        raise ValueError("Code must be a non-empty string")

    code = code.strip()

    # Validate barcode type
    supported_types = ["ean13", "ean8", "upca", "code128", "code39", "itf"]
    if barcode_type not in supported_types:
        raise ValueError(
            f"Unsupported barcode type: {barcode_type}. "
            f"Supported types: {', '.join(supported_types)}"
        )

    try:
        # Get barcode class
        barcode_class = barcode.get_barcode_class(barcode_type)

        # Create barcode instance
        if barcode_type in ("ean13", "ean8", "upca"):
            barcode_obj = barcode_class(code, writer=None, add_checksum=add_checksum)
        else:
            barcode_obj = barcode_class(code, writer=None)

        # Render to PNG
        buffer = io.BytesIO()

        # Default writer options
        default_options = {
            "module_width": 0.2,
            "module_height": 15.0,
            "quiet_zone": 6.5,
            "font_size": 10,
            "text_distance": 5.0,
            "background": "white",
            "foreground": "black",
        }

        if writer_options:
            default_options.update(writer_options)

        barcode_obj.write(buffer, options=default_options)
        return buffer.getvalue()

    except IllegalCharacterError as e:
        raise ValueError(f"Invalid characters in code for {barcode_type}: {e}") from e
    except BarcodeError as e:
        raise BarcodeError(f"Failed to generate {barcode_type}: {e}") from e
    except Exception as e:
        raise ValueError(f"Unexpected error generating barcode: {e}") from e


def generate_qr_code(
    data: str,
    version: Optional[int] = None,
    error_correction: ErrorCorrectionLevel = ERROR_CORRECT_M,
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white",
) -> bytes:
    """Generate a QR code image.

    Args:
        data: The data to encode (string or bytes).
        version: QR code version (1-40). None means auto-select.
        error_correction: Error correction level (L, M, Q, H). Default: ERROR_CORRECT_M.
        box_size: Size of each box in pixels (default: 10).
        border: Border thickness in boxes (default: 4).
        fill_color: Color of the QR modules (default: "black").
        back_color: Background color (default: "white").

    Returns:
        bytes: PNG image data as bytes.

    Raises:
        ValueError: If parameters are invalid or data cannot be encoded.

    Example:
        >>> qr_bytes = generate_qr_code("https://example.com")
        >>> with open("qr.png", "wb") as f:
        ...     f.write(qr_bytes)

        >>> # High error correction for logos
        >>> qr_bytes = generate_qr_code(
        ...     data="Hello World",
        ...     error_correction=qrcode.constants.ERROR_CORRECT_H,
        ...     box_size=20
        ... )
    """
    if not data:
        raise ValueError("Data cannot be empty")

    if not isinstance(data, (str, bytes)):
        raise ValueError("Data must be string or bytes")

    try:
        qr = qrcode.QRCode(
            version=version,
            error_correction=error_correction,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)

        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception as e:
        raise ValueError(f"Failed to generate QR code: {e}") from e


def generate_barcode_with_metadata(
    code: str,
    barcode_type: str = "ean13",
    product_id: Optional[str] = None,
    add_checksum: bool = True,
) -> dict[str, object]:
    """Generate a barcode with associated metadata.

    Args:
        code: The data to encode.
        barcode_type: Type of barcode (default: "ean13").
        product_id: Optional product identifier to associate.
        add_checksum: Whether to add checksum automatically.

    Returns:
        dict: Dictionary containing barcode data and metadata:
            - barcode_bytes: PNG image bytes
            - code: original code used
            - barcode_type: type of barcode generated
            - metadata: dict with product_id and generated uuid

    Example:
        >>> result = generate_barcode_with_metadata("123456789012", product_id="PROD-001")
        >>> print(result["metadata"]["product_id"])
        'PROD-001'
    """
    barcode_bytes = generate_barcode(code, barcode_type, add_checksum=add_checksum)

    return {
        "barcode_bytes": barcode_bytes,
        "code": code,
        "barcode_type": barcode_type,
        "metadata": {
            "product_id": product_id or generate_uuid(),
            "generated_at": barcode_bytes,  # Actual generation timestamp would be added here
        },
    }


def generate_qr_with_metadata(
    data: str,
    url: Optional[str] = None,
    error_correction: ErrorCorrectionLevel = ERROR_CORRECT_M,
) -> dict[str, object]:
    """Generate a QR code with associated metadata.

    Args:
        data: The data to encode.
        url: Optional URL associated with the QR code.
        error_correction: Error correction level.

    Returns:
        dict: Dictionary containing QR code data and metadata.

    Example:
        >>> result = generate_qr_with_metadata("Hello", url="https://example.com/hello")
        >>> print(result["metadata"]["url"])
        'https://example.com/hello'
    """
    qr_bytes = generate_qr_code(data, error_correction=error_correction)

    return {
        "qr_bytes": qr_bytes,
        "data": data,
        "url": url,
        "metadata": {
            "uuid": generate_uuid(),
            "error_correction": str(error_correction),
        },
    }
