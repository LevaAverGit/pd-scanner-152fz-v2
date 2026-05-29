"""
Field classification service for the PD Scanner.
Matches extracted form fields against the PD_CATEGORIES keyword dictionary.
"""

import re

from backend.app.utils.pd_dictionary import PD_CATEGORIES
from backend.app.utils.normalization import extract_text_signals, normalize_field_identifier
from backend.app.utils.patterns import HIGH_RISK_CATEGORIES
from backend.app.models.schemas import DataCategoryItem


def classify_field(field: dict) -> DataCategoryItem | None:
    """
    Given an extracted field dict, return a DataCategoryItem or None if no
    category matched.

    Matching logic:
    - Build text signals from name, id, label, placeholder, aria_label, autocomplete.
    - For each PD category, count how many distinct signals contain any keyword.
    - confidence = 1.0 if 2+ signals match, 0.7 if exactly 1 signal matches.
    - When multiple categories match, return the one with the most signal hits
      (highest_confidence wins ties by category order in PD_CATEGORIES).
    - Keywords are matched as whole tokens only (word-boundary aware) to prevent
      substring false positives (e.g. "age" inside "language").
    """
    signals = extract_text_signals(field)
    if not signals:
        return None

    best_category: str | None = None
    best_hit_count: int = 0
    best_matched_signals: list[str] = []
    best_matched_keyword: str = ""

    for category_name, cat_data in PD_CATEGORIES.items():
        keywords = cat_data["keywords"]
        hit_signals: list[str] = []
        matched_kw: str = ""

        for signal in signals:
            for kw in keywords:
                norm_kw = normalize_field_identifier(kw)
                if norm_kw and re.search(r'\b' + re.escape(norm_kw) + r'\b', signal):
                    if signal not in hit_signals:
                        hit_signals.append(signal)
                    if not matched_kw:
                        matched_kw = kw
                    break

        if hit_signals and len(hit_signals) > best_hit_count:
            best_hit_count = len(hit_signals)
            best_category = category_name
            best_matched_signals = hit_signals
            best_matched_keyword = matched_kw

    if best_category is None:
        return None

    confidence = 1.0 if best_hit_count >= 2 else 0.7
    cat_data = PD_CATEGORIES[best_category]
    risk_note = " [HIGH RISK]" if best_category in HIGH_RISK_CATEGORIES else ""
    explanation = (
        f"Matched '{best_matched_keyword}' in field signals for category "
        f"'{best_category}' ({cat_data['gdpr_article']}){risk_note}."
    )

    return DataCategoryItem(
        category=best_category,
        confidence=confidence,
        matched_signals=best_matched_signals,
        explanation=explanation,
    )


def classify_fields(fields: list[dict]) -> list[DataCategoryItem]:
    """
    Classify all extracted fields and deduplicate by category,
    keeping the highest-confidence item per category.
    """
    category_best: dict[str, DataCategoryItem] = {}

    for field in fields:
        item = classify_field(field)
        if item is None:
            continue
        existing = category_best.get(item.category)
        if existing is None or item.confidence > existing.confidence:
            category_best[item.category] = item

    # Return in a stable order matching PD_CATEGORIES definition order
    ordered: list[DataCategoryItem] = []
    for cat_name in PD_CATEGORIES:
        if cat_name in category_best:
            ordered.append(category_best[cat_name])
    return ordered
