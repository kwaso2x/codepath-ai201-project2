"""
app.py

Gradio interface for FitFindr. Wraps the conversational Agent so users can
search thrifted items, get styling advice, and generate captions from a single
text box.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr

from agent import Agent


# ── agent instance ────────────────────────────────────────────────────────────

# A single agent instance holds session state (selected listing, last outfit)
# across messages, so each request can build on the previous one.
bot = Agent()


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_input: str) -> str:
    """
    Called by Gradio when the user submits a message.

    Routes the message through the Agent's planning loop and returns its
    natural-language reply.
    """
    if not user_input or not user_input.strip():
        return "Tell me what you're after — a thrift find, an outfit idea, or a caption."
    return bot.handle_message(user_input)


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "I'm looking for a vintage graphic tee under $30",
    "how would I style it?",
    "write me a caption",
    "90s track jacket in size M",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

iface = gr.Interface(
    fn=handle_query,
    inputs=gr.Textbox(
        label="Your message",
        placeholder="Ask me about clothes, styling, or captions...",
        lines=2,
    ),
    outputs=gr.Textbox(
        label="FitFindr",
        lines=12,
    ),
    title="Fashion Fit Assistant 👗✨",
    description="Search thrifted items, get styling advice, and generate captions.",
    examples=EXAMPLE_QUERIES,
    flagging_mode="never",
)


if __name__ == "__main__":
    iface.launch()
