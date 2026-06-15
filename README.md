# FitFindr – AI Fashion Assistant 👗✨

FitFindr is an AI-powered fashion assistant for secondhand shopping. Tell it what
you're looking for and it searches thrift listings, suggests complete outfits using
your wardrobe, and writes a social-media-ready caption for your find. It runs as a
simple chat-style web app — **search → style → caption**, all in one conversation.

---

## Features

- **🛍️ Search thrifted items** — find secondhand pieces by description, size, and price.
- **👗 Generate outfit suggestions** — get 1–2 complete outfit ideas built around your find and your existing wardrobe.
- **✨ Create social-media-ready captions** — turn an outfit into a short, casual OOTD-style caption ready to post.

---

## How It Works (High-Level)

FitFindr is built around a lightweight **planning loop**. Each time you send a
message, the agent:

1. **Classifies your intent** — is this a search, a styling request, a caption
   request, or just conversation?
2. **Routes to the right tool** — it calls only the tool that matches your intent.
3. **Maintains state across turns** — it remembers the item you selected and the
   outfit it generated, so a later "how would I style it?" or "write me a caption"
   builds naturally on what came before.

This means you don't have to repeat yourself — the conversation flows from finding
an item, to styling it, to captioning it.

---

## Running the App

Install the dependencies and launch the app:

```bash
pip install -r requirements.txt
python app.py
```

This launches a **Gradio UI** in your browser (usually at http://localhost:7860 —
check your terminal for the exact URL).

> **Note:** FitFindr uses the Groq API for outfit and caption generation. Add a
> free API key (from [console.groq.com](https://console.groq.com)) to a `.env`
> file in the project root:
>
> ```
> GROQ_API_KEY=your_key_here
> ```

---

## Example Interaction

```
You:       I'm looking for a vintage graphic tee under $30
FitFindr:  Found a Y2K Baby Tee – Butterfly Print for $18 on Depop.
           Want me to style it? Just ask how to wear it.

You:       how would I style it?
FitFindr:  Pair it with baggy straight-leg jeans and chunky white sneakers
           for a retro Y2K look, or wide-leg khakis and combat boots for
           an edgier vibe.

You:       write me a caption
FitFindr:  "Scored the cutest Y2K baby tee on Depop for just $18 ✨
           styling it two ways this week — which fit are you picking?"
```

---

## Demo Video

**Demo Video:** [link coming soon]

---

## Tools Summary

- **`search_listings`** — searches the thrift listings dataset by description, size, and max price, returning the most relevant matches.
- **`suggest_outfit`** — generates outfit ideas that combine a selected item with the user's wardrobe (or general styling advice if the wardrobe is empty).
- **`create_fit_card`** — writes a short, casual, social-media-ready caption for the outfit and item.

---

## Tech Stack

- **Python**
- **Gradio** — web UI
- **Groq API** — LLM-powered styling and captions
- **Custom planning loop + tool functions** — intent routing and session state

---

## Credits

Built for **CodePath AI201 – Applications of AI Engineering**.
