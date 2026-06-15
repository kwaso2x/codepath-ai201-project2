"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    # Load listings
    listings = load_listings()

    # Filter by price
    if max_price is not None:
        listings = [item for item in listings if item.get("price") is not None and item["price"] <= max_price]

    # Filter by size
    if size:
        size_norm = size.lower()
        def size_matches(item_size: str | None) -> bool:
            if not item_size:
                return False
            return size_norm in item_size.lower()

        listings = [item for item in listings if size_matches(item.get("size"))]

    # Score by keyword overlap between query and title/description/style_tags
    keywords = [k for k in description.lower().split() if k]

    def score_item(item: dict) -> int:
        text_parts = [item.get("title", ""), item.get("description", "")]
        # include tags and category
        text_parts.append(" ".join(item.get("style_tags", []) or []))
        text_parts.append(item.get("category", ""))
        text = " ".join(text_parts).lower()
        return sum(1 for kw in keywords if kw in text)

    scored = [(item, score_item(item)) for item in listings]
    # drop zero scores
    scored = [(item, s) for item, s in scored if s > 0]

    # sort by score desc
    scored.sort(key=lambda pair: pair[1], reverse=True)

    return [item for item, _ in scored]



# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    items = wardrobe.get("items", [])

    # ── Case 1: Wardrobe empty ────────────────────────────────────────────────
    if not items:
        prompt = f"""
        You are a fashion stylist.

        The user thrifted this item:
        {new_item}

        Their wardrobe is empty.

        Give 2–3 outfit ideas using general styling principles.
        Be specific about colors, silhouettes, and vibes.
        """

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )

        return response.choices[0].message.content

    # ── Case 2: Wardrobe has items ────────────────────────────────────────────
    wardrobe_text = "\n".join(
        f"- {w['name']} ({w['category']}, {w['colors']})"
        for w in items
    )

    prompt = f"""
    You are a fashion stylist.

    New thrifted item:
    {new_item}

    Wardrobe items:
    {wardrobe_text}

    Suggest 1–2 complete outfits using the new item and pieces from the wardrobe.
    Be specific and creative.
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )

    return response.choices[0].message.content



# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard against empty outfit
    if not outfit or not outfit.strip():
        return "I couldn't create a fit card because the outfit description was missing."

    client = _get_groq_client()

    # Extract item details
    title = new_item.get("title", "this thrifted piece")
    price = new_item.get("price", "unknown price")
    platform = new_item.get("platform", "a thrift platform")

    # Build prompt
    prompt = f"""
    Create a short, casual Instagram-style caption (2–4 sentences).

    Details:
    - Item: {title}
    - Price: ${price}
    - Platform: {platform}

    Outfit:
    {outfit}

    Guidelines:
    - Sound natural and conversational.
    - Mention the item name, price, and platform once each.
    - Capture the vibe of the outfit.
    - Avoid sounding like an ad or product description.
    """

    # LLM call
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )

    return response.choices[0].message.content

