# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the thrift listings dataset for items that match the user’s description, optional size, and optional maximum price, then returns the most relevant matches.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ...Keywords describing what the user is looking for (e.g., "vintage graphic tee").
- `size` (str): ... Optional size filter (e.g., "M"); matching is case‑insensitive and can match ranges like "S/M".
- `max_price` (float): ...(float | None): Optional maximum price (inclusive) for the item.

**What it returns:**
A list of listing dicts sorted by relevance. Each result includes fields like id, title, description, category, style_tags, size, condition, price, colors, brand, and platform.

**What happens if it fails or returns nothing:**
If no listings match, the agent explains that nothing was found for the given description/filters and suggests relaxing the price limit, changing the size, or trying different keywords instead of crashing.
---

### Tool 2: suggest_outfit

**What it does:**
Given a selected thrifted item and the user’s wardrobe, it generates 1–2 outfit suggestions that incorporate the new item and existing wardrobe pieces, or general styling advice if the wardrobe is empty.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ...The listing dict for the thrifted item the user is considering.
- `wardrobe` (dict): ...A wardrobe dict with an items list, where each item follows the wardrobe_schema.json structure (e.g., name, category, colors).

**What it returns:**
<!-- Describe the return value -->
A non‑empty string describing 1–2 outfit ideas, or general styling guidance for the item if the wardrobe has no items.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->If the wardrobe is empty or unusable, the agent switches to general styling advice (what kinds of pieces would pair well) instead of returning an empty string. If the LLM response is unusable, the agent explains that it couldn’t generate a good outfit and invites the user to describe their wardrobe in more detail.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Generates a short, casual, social‑media‑ready caption (2–4 sentences) for the outfit and thrifted item, mentioning the item name, price, and platform naturally.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit`(str): The outfit suggestion text produced by suggest_outfit.
new_item (dict): The listing dict for the thrifted item (used to pull title, price, and platform).
**What it returns:**
<!-- Describe the return value -->
A 2–4 sentence caption string that feels like a real OOTD post, references the item, price, and platform once each, and captures the vibe of the outfit.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If the outfit input is missing or empty, the tool returns a friendly error message explaining that an outfit is needed before a caption can be generated. If the LLM fails, the agent tells the user it couldn’t create a caption and suggests they use the outfit description directly or try again.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The planning loop reads the user’s message and decides which tool to call based on intent: search‑type requests (e.g., “what’s out there under $30?”) trigger search_listings, styling questions (e.g., “how would I style this?”) trigger suggest_outfit, and caption/“fit card” requests trigger create_fit_card. After each tool call, the agent updates its internal state (e.g., selected listing, generated outfit) and uses that state to decide the next tool. The loop ends when the user’s request has been fully answered and no further tools are needed, at which point the agent sends a final natural‑language response.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
Within a session, the agent tracks the current selected listing, the user’s wardrobe, and the latest outfit suggestion. When search_listings returns results, the agent stores the chosen listing and passes it as new_item into suggest_outfit. When suggest_outfit returns an outfit string, the agent stores it and passes it along with new_item into create_fit_card. This state is kept in memory (e.g., a conversation context or a session dict) so each tool can build on the outputs of the previous ones.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

| Tool | Failure mode | Agent response |
| --- | --- | --- |
| search_listings | No results match the query | Explain that no listings were found with those filters and suggest changing price/size/keywords. |
| suggest_outfit | Wardrobe is empty | Switch to general styling advice for the new item instead of failing or returning an empty string. |
| create_fit_card | Outfit input is missing or incomplete | Return a friendly message saying an outfit is needed before generating a caption, and prompt the user to ask for styling first. |
---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->
     User input
    ↓
Planning Loop (agent.py)
    ↓
    ├─ If user is searching for items → search_listings()
    │       ↓
    │   Selected listing stored in session state
    │
    ├─ If user wants styling → suggest_outfit()
    │       ↓
    │   Outfit text stored in session state
    │
    ├─ If user wants a caption → create_fit_card()
    │       ↓
    │   Caption returned
    │
    └─ Error paths:
            - If a tool returns no useful result, agent explains the issue
              and suggests next steps instead of crashing.

Session state:
    - current_listing
    - wardrobe
    - outfit_text


---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
I will use Copilot (and/or Claude) to implement each tool based on the specs in this planning.md. For search_listings, I’ll provide the tool description, input/return types, and failure behavior, along with the load_listings() helper, and ask the AI to write the filtering and scoring logic. For suggest_outfit and create_fit_card, I’ll share the wardrobe schema, item fields, and prompt requirements, and ask the AI to generate Groq LLM calls that follow my failure‑handling rules. I’ll verify each tool by running test queries and checking that the outputs match the expected behavior before moving on.

**Milestone 4 — Planning loop and state management:**
I will use Copilot (and/or Claude) to help implement the planning loop in agent.py, giving it my Planning Loop, State Management, Error Handling, and Architecture sections from this document. I’ll ask it to write code that routes user messages to the correct tools, stores intermediate results (selected listing, outfit text), and handles failures gracefully. I’ll verify the loop by stepping through the “Complete Interaction” example and confirming that each tool is called with the right inputs and that the final response matches my spec.
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

***Step 1:**  
The agent identifies that the user is searching for an item, so it calls `search_listings` with:  
- description="vintage graphic tee"  
- size=None  
- max_price=30  

The tool returns a list of matching thrift listings sorted by relevance.

**Step 2:**  
The agent selects the top matching listing (e.g., a vintage 90s graphic tee for $22 on Depop).  
Because the user also asked how to style it, the agent calls `suggest_outfit` with:  
- new_item=<the selected listing dict>  
- wardrobe={"items": [{"name": "baggy jeans"}, {"name": "chunky sneakers"}]}  

The tool returns 1–2 outfit ideas using the thrifted tee and the user’s wardrobe.

**Step 3:**  
Now that an outfit has been generated, the agent calls `create_fit_card` with:  
- outfit=<the outfit suggestion text>  
- new_item=<the same listing dict>  

The tool returns a short, casual Instagram-style caption describing the fit.

**Final output to user:**  
The agent sends a combined response that includes:  
- the best matching thrift listing  
- the outfit suggestions  
- the final caption  

If any tool fails (e.g., no listings found, empty wardrobe, missing outfit), the agent gracefully explains the issue instead of crashing and guides the user on what to do next.