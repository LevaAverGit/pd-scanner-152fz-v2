"""
DOM field extractor for the PD Scanner.
Accepts a Playwright Page object; does NOT launch the browser itself.
"""

import logging

logger = logging.getLogger(__name__)

# Maximum number of form fields to extract per page
MAX_FIELDS = 100

# Input types to skip entirely (carry no meaningful label data for classification)
_SKIP_TYPES = {"hidden", "submit", "button", "reset", "image"}


async def extract_fields(page) -> list[dict]:
    """
    Extract interactive form fields (input, select, textarea) from the page.

    For each visible field returns a dict with:
        tag, field_type, name, id, label, placeholder, autocomplete, required, selector

    Hidden inputs are excluded from the returned list.
    Capped at MAX_FIELDS (100) results.
    """
    fields: list[dict] = []

    # Build a combined selector for all relevant elements
    locator = page.locator("input, select, textarea")
    count = await locator.count()

    for i in range(min(count, MAX_FIELDS * 3)):  # over-fetch then cap
        if len(fields) >= MAX_FIELDS:
            break

        try:
            el = locator.nth(i)

            tag = (await el.evaluate("e => e.tagName.toLowerCase()")).strip()
            field_type = await _get_field_type(el, tag)

            # Skip hidden and button-type inputs
            if field_type in _SKIP_TYPES:
                continue

            # Check visibility — skip if not visible
            try:
                is_visible = await el.is_visible()
                if not is_visible:
                    continue
            except Exception:
                continue

            name = await _get_attr(el, "name")
            field_id = await _get_attr(el, "id")
            placeholder = await _get_attr(el, "placeholder")
            autocomplete = await _get_attr(el, "autocomplete")
            required_attr = await el.evaluate(
                "e => e.hasAttribute('required') || e.required || false"
            )
            required = bool(required_attr)

            # Build a robust CSS selector for this element
            selector = await _build_selector(el, tag, field_id, name, i)

            # Label resolution: for[id] → aria-label → ancestor label
            label = await _resolve_label(page, el, field_id)

            fields.append(
                {
                    "tag": tag,
                    "field_type": field_type,
                    "name": name,
                    "id": field_id,
                    "label": label,
                    "placeholder": placeholder,
                    "autocomplete": autocomplete,
                    "required": required,
                    "selector": selector,
                }
            )
        except Exception as exc:
            logger.debug("Skipping field %d due to error: %s", i, exc)
            continue

    logger.info("Extracted %d fields from page", len(fields))
    return fields


async def _get_field_type(el, tag: str) -> str:
    """Return the effective type string for a form element."""
    if tag == "select":
        return "select"
    if tag == "textarea":
        return "textarea"
    try:
        t = await el.evaluate("e => (e.type || 'text').toLowerCase()")
        return t.strip() or "text"
    except Exception:
        return "text"


async def _get_attr(el, attr: str) -> str | None:
    """Safely retrieve an attribute, returning None if absent or empty."""
    try:
        val = await el.get_attribute(attr)
        if val is not None:
            val = val.strip()
            return val if val else None
        return None
    except Exception:
        return None


async def _build_selector(el, tag: str, field_id: str | None, name: str | None, index: int) -> str:
    """Build a CSS selector for the element, preferring id > name > nth-of-type."""
    if field_id:
        return f'#{field_id}'
    if name:
        return f'{tag}[name="{name}"]'
    return f'{tag}:nth-of-type({index + 1})'


async def _resolve_label(page, el, field_id: str | None) -> str | None:
    """
    Resolve the human-readable label for a field.
    Priority: <label for="id"> → aria-label → nearest ancestor <label>.
    """
    # 1. <label for="...">
    if field_id:
        try:
            label_loc = page.locator(f'label[for="{field_id}"]')
            if await label_loc.count() > 0:
                text = await label_loc.first.text_content()
                if text:
                    text = text.strip()
                    if text:
                        return text
        except Exception:
            pass

    # 2. aria-label attribute
    try:
        aria = await el.get_attribute("aria-label")
        if aria:
            aria = aria.strip()
            if aria:
                return aria
    except Exception:
        pass

    # 3. Nearest ancestor <label> element
    try:
        ancestor_text = await el.evaluate(
            """e => {
                let node = e.parentElement;
                while (node) {
                    if (node.tagName && node.tagName.toLowerCase() === 'label') {
                        return node.textContent || '';
                    }
                    node = node.parentElement;
                }
                return '';
            }"""
        )
        if ancestor_text:
            ancestor_text = ancestor_text.strip()
            if ancestor_text:
                return ancestor_text
    except Exception:
        pass

    return None
