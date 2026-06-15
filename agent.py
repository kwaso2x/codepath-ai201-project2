"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via session state.

Two entry points are provided:

  * ``Agent`` — a conversational agent that keeps state across messages.
    Call ``agent.handle_message(user_input)`` repeatedly; each call classifies
    the user's intent, routes to the right tool, updates state, and returns a
    natural-language reply.

  * ``run_agent(query, wardrobe)`` — a one-shot pipeline (search → style →
    caption) that returns a session dict. Kept for the Gradio app (app.py) and
    the CLI test below.

The tool implementations in tools.py are NOT modified here — this file only
contains the planning loop and intent routing.

Usage (conversational):
    from agent import Agent

    agent = Agent()
    print(agent.handle_message("vintage graphic tee under $30"))
    print(agent.handle_message("how would I style it?"))
    print(agent.handle_message("write me a caption"))
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe


# ── intent detection ────────────────────────────────────────────────────────

# Recognized intents. "general" is the fallback when nothing else matches.
INTENT_SEARCH = "search"
INTENT_STYLING = "styling"
INTENT_CAPTION = "caption"
INTENT_GENERAL = "general"

# Keyword groups for each intent. Checked in priority order (see classify_intent):
# caption is most specific, then search (shopping language / price / size),
# then styling, and finally general conversation.
_CAPTION_KEYWORDS = (
    "caption", "fit card", "fitcard", "ootd", "instagram", "insta ",
    "ig caption", "tiktok", "make a post", "write a post", "write a caption",
    "share this", "post about",
)
_SEARCH_KEYWORDS = (
    "find", "looking for", "look for", "search", "show me", "what's out there",
    "whats out there", "browse", "shop", "do you have", "any ", "under $",
)
_STYLING_KEYWORDS = (
    "style", "outfit", "wear", "pair", "match", "go with", "goes with",
    "what do i wear", "how would i", "how should i", "dress",
)
_GENERAL_KEYWORDS = (
    "hi", "hey", "hello", "thanks", "thank you", "who are you", "what can you do",
    "help", "how does this work",
)


def classify_intent(text: str) -> str:
    """
    Classify a user message into one of: search, styling, caption, general.

    Uses simple case-insensitive keyword matching. Priority order matters:
        1. caption  — most specific ("write a caption", "fit card")
        2. search   — shopping language, a price ("under $30"), or "find"
        3. styling  — "how would I style this", "what do I wear"
        4. general  — anything else (greetings, small talk, unclear requests)
    """
    t = text.lower().strip()

    if _contains_any(t, _CAPTION_KEYWORDS):
        return INTENT_CAPTION

    # A bare price/size mention (e.g. "anything under $25?") reads as a search.
    if _contains_any(t, _SEARCH_KEYWORDS) or re.search(r"\$\s*\d", t):
        return INTENT_SEARCH

    if _contains_any(t, _STYLING_KEYWORDS):
        return INTENT_STYLING

    if _contains_any(t, _GENERAL_KEYWORDS):
        return INTENT_GENERAL

    return INTENT_GENERAL


def _contains_any(text: str, keywords) -> bool:
    """Return True if any keyword appears as a substring of (lowercased) text."""
    return any(kw in text for kw in keywords)


def parse_search_query(text: str) -> dict:
    """
    Extract search parameters from a free-text query.

    Returns a dict with keys:
        description (str): cleaned keywords to match against listings
        size (str | None): size filter if the user wrote "size X"
        max_price (float | None): price ceiling if the user wrote "under $30"

    Parsing strategy (documented in planning.md):
        * max_price — regex for "under/below/less than/max $N" or a bare "$N".
        * size      — regex for "size X" (letter sizes or shoe numbers).
        * description — the original text with the price/size phrases and a few
          filler words removed, leaving keywords for search_listings to score.
    """
    desc = text.strip()
    size = None
    max_price = None

    # max_price: "under $30", "below 30", "less than $25.50", or a bare "$40"
    price_match = re.search(
        r"(?:under|below|less than|max(?:imum)?|<=?)\s*\$?\s*(\d+(?:\.\d+)?)",
        desc,
        re.IGNORECASE,
    )
    if not price_match:
        price_match = re.search(r"\$\s*(\d+(?:\.\d+)?)", desc)
    if price_match:
        max_price = float(price_match.group(1))
        desc = desc.replace(price_match.group(0), " ")

    # size: "size M", "size 8", "size S/M"
    size_match = re.search(r"\bsize\s+([a-z0-9/]+)\b", desc, re.IGNORECASE)
    if size_match:
        size = size_match.group(1)
        desc = desc.replace(size_match.group(0), " ")

    # Drop a few filler phrases so they don't pollute the keyword scoring.
    desc = re.sub(
        r"\b(i'?m\s+)?(looking for|look for|find me|find|show me|search for|"
        r"search|do you have|any|some|a|an|the|please|under|below)\b",
        " ",
        desc,
        flags=re.IGNORECASE,
    )
    desc = re.sub(r"\s+", " ", desc).strip()
    desc = desc.strip(" ,.;:!?-")  # drop stray punctuation left by removals

    return {"description": desc or text.strip(), "size": size, "max_price": max_price}


# ── presentation helpers ────────────────────────────────────────────────────

def format_listing(item: dict) -> str:
    """Format a listing dict into a readable multi-line summary string."""
    colors = item.get("colors") or []
    tags = item.get("style_tags") or []
    brand = item.get("brand") or "Unbranded"
    return (
        f"{item.get('title', 'Untitled')} — ${item.get('price', '?')}\n"
        f"  Platform:  {item.get('platform', 'unknown')}\n"
        f"  Size:      {item.get('size', 'n/a')}   "
        f"Condition: {item.get('condition', 'n/a')}\n"
        f"  Brand:     {brand}\n"
        f"  Colors:    {', '.join(colors) if colors else 'n/a'}\n"
        f"  Tags:      {', '.join(tags) if tags else 'n/a'}\n"
        f"  {item.get('description', '')}"
    )


# ── conversational agent ──────────────────────────────────────────────────────

class Agent:
    """
    Conversational FitFindr agent.

    Keeps session state across messages so each tool can build on the last:
        current_listing — the selected listing dict (from search_listings)
        outfit_text     — the latest outfit suggestion (from suggest_outfit)
        wardrobe        — the user's wardrobe (defaults to the example wardrobe)

    Call ``handle_message(user_input)`` once per user turn; it returns a
    natural-language reply string.
    """

    def __init__(self, wardrobe: dict | None = None):
        """Initialize session state. Uses the example wardrobe unless one is given."""
        self.wardrobe = wardrobe if wardrobe is not None else get_example_wardrobe()
        self.current_listing = None   # dict — selected item, input to the other tools
        self.outfit_text = None       # str  — last outfit, input to create_fit_card
        self.last_intent = None       # str  — most recent classified intent

    # -- main planning loop --------------------------------------------------

    def handle_message(self, user_input: str) -> str:
        """
        Process one user message: classify intent, route to a tool, update
        state, and return a natural-language response.
        """
        if not user_input or not user_input.strip():
            return "Tell me what you're after — a thrift find, an outfit idea, or a caption."

        intent = classify_intent(user_input)
        self.last_intent = intent

        if intent == INTENT_SEARCH:
            return self._handle_search(user_input)
        if intent == INTENT_STYLING:
            return self._handle_styling()
        if intent == INTENT_CAPTION:
            return self._handle_caption()
        return self._handle_general()

    # -- intent handlers -----------------------------------------------------

    def _handle_search(self, user_input: str) -> str:
        """Route a search request to search_listings() and update state."""
        parsed = parse_search_query(user_input)
        results = search_listings(
            description=parsed["description"],
            size=parsed["size"],
            max_price=parsed["max_price"],
        )

        # Error handling: nothing matched.
        if not results:
            self.current_listing = None
            self.outfit_text = None
            filters = []
            if parsed["size"]:
                filters.append(f"size {parsed['size']}")
            if parsed["max_price"] is not None:
                filters.append(f"under ${parsed['max_price']:g}")
            filter_note = f" with {', '.join(filters)}" if filters else ""
            return (
                f"I couldn't find anything matching \"{parsed['description']}\""
                f"{filter_note}. Try relaxing the price, changing the size, or "
                f"using different keywords."
            )

        # Success: select the top result and store it.
        self.current_listing = results[0]
        self.outfit_text = None  # a new pick invalidates the old outfit

        reply = [
            f"Found {len(results)} match{'es' if len(results) != 1 else ''}. "
            f"Here's the top pick:\n",
            format_listing(self.current_listing),
        ]
        if len(results) > 1:
            others = ", ".join(
                f"{r.get('title')} (${r.get('price')})" for r in results[1:4]
            )
            reply.append(f"\nOther options: {others}")
        reply.append("\nWant me to style it? Just ask how to wear it.")
        return "\n".join(reply)

    def _handle_styling(self) -> str:
        """Route a styling request to suggest_outfit() and update state."""
        if self.current_listing is None:
            return (
                "I need an item to style first. Search for something — e.g. "
                "\"vintage graphic tee under $30\" — and then ask me how to wear it."
            )

        try:
            outfit = suggest_outfit(self.current_listing, self.wardrobe)
        except Exception:
            outfit = None

        # Error handling: suggest_outfit failed — fall back to general advice.
        if not outfit or not outfit.strip():
            return (
                "I couldn't generate a full outfit just now. As a general rule, "
                f"build around \"{self.current_listing.get('title', 'this piece')}\" "
                "with neutral basics, then add one statement layer and shoes that "
                "match the vibe. Tell me more about your wardrobe and I'll try again."
            )

        self.outfit_text = outfit
        title = self.current_listing.get("title", "your find")
        return (
            f"Here's how I'd style {title}:\n\n{outfit}\n\n"
            "Like it? Ask me for a caption and I'll write a fit card."
        )

    def _handle_caption(self) -> str:
        """Route a caption request to create_fit_card() and update state."""
        # Error handling: need an outfit before a caption.
        if not self.outfit_text or not self.outfit_text.strip():
            return (
                "You'll need an outfit first. Pick an item and ask me to style it, "
                "then I can write you a fit card caption."
            )

        card = create_fit_card(self.outfit_text, self.current_listing or {})
        return f"Here's your fit card:\n\n{card}"

    def _handle_general(self) -> str:
        """Handle greetings and anything that isn't a tool request."""
        return (
            "Hey! I'm FitFindr. I can:\n"
            "  • find secondhand pieces — \"vintage graphic tee under $30, size M\"\n"
            "  • style a find — \"how would I wear it?\"\n"
            "  • write a shareable caption — \"make me a fit card\"\n"
            "What are you looking for?"
        )


# ── one-shot pipeline (used by app.py and the CLI test) ───────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one one-shot interaction."""
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    One-shot planning loop: search → style → caption, in sequence.

    This mirrors the "Complete Interaction" in planning.md and returns the
    session dict that app.py expects. It reuses the same tool-calling logic as
    the Agent class via parse_search_query() and the three tools.

    Returns the session dict. Check session["error"] first — if it is not None,
    the interaction ended early and the other output fields are None.
    """
    session = _new_session(query, wardrobe)

    # Step 1–2: parse the query.
    parsed = parse_search_query(query)
    session["parsed"] = parsed

    # Step 3: search.
    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results
    if not results:
        session["error"] = (
            f"No listings found for \"{parsed['description']}\". "
            f"Try relaxing the price, changing the size, or different keywords."
        )
        return session

    # Step 4: select the top result.
    session["selected_item"] = results[0]

    # Step 5: style it (fall back gracefully on failure).
    try:
        outfit = suggest_outfit(results[0], wardrobe)
    except Exception:
        outfit = None
    if not outfit or not outfit.strip():
        outfit = (
            f"Build around \"{results[0].get('title', 'this piece')}\" with neutral "
            "basics, one statement layer, and shoes that match the vibe."
        )
    session["outfit_suggestion"] = outfit

    # Step 6: caption it.
    session["fit_card"] = create_fit_card(outfit, results[0])

    # Step 7: done.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Happy path: graphic tee (one-shot run_agent) ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")

    print("\n\n=== Conversational Agent ===\n")
    agent = Agent()
    for msg in [
        "Hi, what can you do?",
        "looking for a vintage graphic tee under $30",
        "how would I style it?",
        "make me a fit card",
    ]:
        print(f"USER:  {msg}")
        print(f"AGENT: {agent.handle_message(msg)}\n")
