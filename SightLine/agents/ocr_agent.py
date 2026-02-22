"""SightLine OCR Sub-Agent.

Asynchronous text extraction using Gemini Flash (gemini-3-flash-preview)
optimized for menus, signage, documents, and labels. Uses the free-tier
Gemini Developer API.

The context_hint parameter helps the model focus on the most relevant
text type (e.g., "user is at a restaurant" prioritizes menu items).
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger("sightline.ocr_agent")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OCR_MODEL = "gemini-3-flash-preview"

_SYSTEM_PROMPT = """\
You are a text extraction system for a blind user. Your job is to read ALL \
visible text in the image accurately.

Rules:
1. Extract every piece of readable text — signs, menus, labels, documents, \
   screens, handwriting.
2. Classify the text type: "menu", "sign", "document", "label", or "unknown".
3. For menus: parse into individual items with prices when visible. Format \
   each item as "Item Name - $Price" or just "Item Name" if no price.
4. For signs: preserve the exact wording.
5. For documents: maintain reading order (top to bottom, left to right).
6. Report confidence based on text clarity (0.0 = unreadable, 1.0 = crystal clear).
7. If no text is visible, return empty results with confidence 0.0.

Priority: accuracy over speed. A blind user depends on correct text reading.
"""

# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "text": types.Schema(
            type=types.Type.STRING,
            description="All extracted text as a single string.",
        ),
        "text_type": types.Schema(
            type=types.Type.STRING,
            enum=["menu", "sign", "document", "label", "unknown"],
            description="Classification of the dominant text type.",
        ),
        "items": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
            description="Parsed items (menu items with prices, sign lines, etc).",
        ),
        "confidence": types.Schema(
            type=types.Type.NUMBER,
            description="Confidence score from 0.0 to 1.0.",
        ),
    },
    required=["text", "text_type", "items", "confidence"],
)

# ---------------------------------------------------------------------------
# Empty / fallback result
# ---------------------------------------------------------------------------

_EMPTY_RESULT: dict[str, Any] = {
    "text": "",
    "text_type": "unknown",
    "items": [],
    "confidence": 0.0,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazily initialize the Gemini client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        _client = genai.Client(api_key=api_key)
    return _client


async def extract_text(
    image_base64: str,
    context_hint: str = "",
) -> dict[str, Any]:
    """Extract text from an image using Gemini Flash OCR.

    Args:
        image_base64: Base64-encoded image data (JPEG or PNG).
        context_hint: Optional context about the user's situation
            (e.g., "user is at a restaurant") to help focus extraction.

    Returns:
        Structured dict with text, text_type, items, confidence.
        Returns empty result on failure (never raises).
    """
    try:
        image_bytes = base64.b64decode(image_base64)
    except Exception:
        logger.error("Failed to decode base64 image data")
        return dict(_EMPTY_RESULT)

    user_message = "Extract all visible text from this image."
    if context_hint:
        user_message += f" Context: {context_hint}"

    try:
        client = _get_client()
        response = await client.aio.models.generate_content(
            model=OCR_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type="image/jpeg",
                        ),
                        types.Part.from_text(text=user_message),
                    ],
                ),
            ],
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                media_resolution=types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
                response_mime_type="application/json",
                response_schema=_RESPONSE_SCHEMA,
                temperature=0.1,
            ),
        )

        if not response.text:
            logger.warning("OCR model returned empty response")
            return dict(_EMPTY_RESULT)

        result = json.loads(response.text)

        # Ensure all expected keys exist
        for key, default_val in _EMPTY_RESULT.items():
            if key not in result:
                result[key] = default_val

        return result

    except json.JSONDecodeError:
        logger.error("Failed to parse OCR model JSON response: %s", response.text)
        return dict(_EMPTY_RESULT)
    except Exception:
        logger.exception("OCR extraction failed")
        return dict(_EMPTY_RESULT)
