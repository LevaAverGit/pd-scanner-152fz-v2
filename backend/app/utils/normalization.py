"""
Text normalization utilities for the PD Scanner field classification pipeline.
"""

import re

from backend.app.utils.patterns import FIELD_NAME_NORMALIZER_RE


def normalize_field_identifier(value: str) -> str:
    """
    Lowercase, strip non-alphanumeric characters (except spaces),
    and collapse whitespace to a single space.
    """
    lowered = value.lower()
    stripped = FIELD_NAME_NORMALIZER_RE.sub(" ", lowered)
    collapsed = re.sub(r"\s+", " ", stripped).strip()
    return collapsed


def normalize_label(label: str) -> str:
    """
    Strip leading/trailing whitespace, lowercase, and collapse internal whitespace.
    """
    return re.sub(r"\s+", " ", label.strip().lower())


def extract_text_signals(field_attrs: dict) -> list[str]:
    """
    Return a list of non-empty lowercased text signals drawn from the field's
    name, id, label, placeholder, aria_label, and autocomplete attributes.
    Each present, non-empty value is normalized and included.
    """
    signal_keys = ["name", "id", "label", "placeholder", "aria_label", "autocomplete"]
    signals: list[str] = []
    for key in signal_keys:
        raw = field_attrs.get(key)
        if raw and isinstance(raw, str):
            normalized = normalize_field_identifier(raw)
            if normalized:
                signals.append(normalized)
    return signals
