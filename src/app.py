"""
app.py — Professional, high-contrast Slate/Dark Gradio web interface for MedNote Scribe.

Theme Features:
- Soft Slate/Dark background (#1e293b / #0f172a), NOT pitch dark.
- High-contrast text (#ffffff / #f8fafc) so output text and trace logs are crisp and clearly legible.
- Eye-soothing Warm Amber / Orange accent buttons (#f97316 / #ea580c).
- Dedicated high-contrast styling for code blocks & tool results in the Agent Trace panel.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import gradio as gr
from agent import run_agent_with_trace
from config import GROQ_MODEL

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")


def process_query(user_input: str, session_id: str) -> tuple[str, str, str]:
    """Process user input through the ReAct Agent and return (response, trace_html, badge_html)."""
    if not user_input.strip():
        return (
            "⚠️ Please enter a patient transcript or query.",
            "<div style='color: #94a3b8; font-style: italic; padding: 8px;'>No trace events generated yet.</div>",
            "<span style='background:#334155; color:#f8fafc; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #475569;'>Status: Ready</span>",
        )

    try:
        # Run agent asynchronously
        response_text, trace_events = asyncio.run(
            run_agent_with_trace(user_input, thread_id=session_id)
        )

        # Build clean, high-contrast HTML for Agent Trace & Memory Panel
        if not trace_events:
            trace_html = "<div style='color: #cbd5e1; font-weight: 500; padding: 8px;'>Direct reasoning (no external tool calls required).</div>"
            badge_html = "<span style='background:#1e3a8a; color:#93c5fd; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #3b82f6;'>ℹ️ Direct Reasoning</span>"
        else:
            trace_blocks = []
            has_rag = False
            has_ehr = False

            for idx, event in enumerate(trace_events, 1):
                if event["type"] == "tool_call":
                    name = event["name"]
                    args = json.dumps(event["args"], indent=2)
                    if "retrieve" in name:
                        has_rag = True
                    if "save" in name or "history" in name:
                        has_ehr = True

                    trace_blocks.append(
                        f"""
                        <div style="background: #0f172a; border: 1px solid #334155; border-left: 5px solid #f97316; padding: 12px 16px; margin-bottom: 12px; border-radius: 8px;">
                            <div style="font-weight: 700; color: #ffedd5; font-size: 14px; margin-bottom: 6px;">🛠️ Step {idx}: Called Tool <code style="background:#ea580c; color:#ffffff; padding:2px 8px; border-radius:4px;">{name}</code></div>
                            <pre style="background: #1e293b; color: #f8fafc; padding: 10px; border: 1px solid #475569; border-radius: 6px; font-size: 13px; font-family: monospace; overflow-x: auto; margin: 0;">{args}</pre>
                        </div>
                        """
                    )
                elif event["type"] == "tool_result":
                    name = event["name"]
                    content = event["content"]
                    trace_blocks.append(
                        f"""
                        <div style="background: #0f172a; border: 1px solid #334155; border-left: 5px solid #22c55e; padding: 12px 16px; margin-bottom: 12px; border-radius: 8px;">
                            <div style="font-weight: 700; color: #dcfce7; font-size: 14px; margin-bottom: 6px;">📥 Result from <code style="background:#166534; color:#ffffff; padding:2px 8px; border-radius:4px;">{name}</code></div>
                            <pre style="background: #1e293b; color: #f8fafc; padding: 10px; border: 1px solid #475569; border-radius: 6px; font-size: 13px; font-family: monospace; white-space: pre-wrap; word-break: break-word; overflow-x: auto; margin: 0;">{content}</pre>
                        </div>
                        """
                    )

            trace_html = "".join(trace_blocks)

            badges = []
            if has_rag:
                badges.append("<span style='background:#1e3a8a; color:#bfdbfe; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #3b82f6;'>🔍 RAG Context Retrieved</span>")
            if has_ehr:
                badges.append("<span style='background:#14532d; color:#bbf7d0; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #22c55e;'>💾 EHR Store Accessed</span>")

            badge_html = " ".join(badges) if badges else "<span style='background:#334155; color:#f8fafc; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #475569;'>⚡ Processed</span>"

        return response_text, trace_html, badge_html

    except Exception as exc:
        log.error("Error processing query in UI: %s", exc, exc_info=True)
        return (
            f"❌ **Error running agent**: {exc}\n\nPlease check your `.env` configuration for `GROQ_API_KEY`.",
            f"<div style='color: #fca5a5; font-weight:600; padding: 8px;'>Execution Error: {exc}</div>",
            "<span style='background:#7f1d1d; color:#fecaca; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #ef4444;'>❌ Execution Error</span>",
        )


# Eye-Soothing Slate Dark Theme Styling
CUSTOM_CSS = """
body, .gradio-container {
    background-color: #0f172a !important;
    color: #f8fafc !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}

/* Header Styling */
.header-box {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    color: #ffffff;
    padding: 24px 28px;
    border-radius: 12px;
    margin-bottom: 24px;
    border: 1px solid #475569;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
.header-box h1 {
    color: #ffffff !important;
    margin: 0 0 6px 0 !important;
    font-size: 28px;
    font-weight: 700;
}
.header-box p {
    color: #cbd5e1 !important;
    margin: 0 !important;
    font-size: 15px;
}

/* Button Styling — Vibrant Orange Accent */
button.primary, .gr-button-primary, button[variant="primary"] {
    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 6px rgba(249, 115, 22, 0.35) !important;
    transition: all 0.2s ease !important;
}
button.primary:hover, .gr-button-primary:hover, button[variant="primary"]:hover {
    background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%) !important;
    box-shadow: 0 4px 12px rgba(234, 88, 12, 0.5) !important;
    transform: translateY(-1px);
}

button.secondary, .gr-button-secondary, button[variant="secondary"] {
    background: #334155 !important;
    color: #f8fafc !important;
    border: 1px solid #475569 !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}
button.secondary:hover, .gr-button-secondary:hover, button[variant="secondary"]:hover {
    background: #475569 !important;
    color: #ffffff !important;
}

/* Textarea & Input Boxes */
textarea, input[type="text"] {
    background-color: #1e293b !important;
    color: #f8fafc !important;
    border: 1px solid #475569 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: #f97316 !important;
    box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.25) !important;
}

/* Response & Markdown High-Contrast Output */
.markdown-text, .gr-markdown, div.gr-markdown {
    color: #f8fafc !important;
    font-size: 15px !important;
    line-height: 1.65 !important;
}

.markdown-text p, .markdown-text li, .markdown-text h1, .markdown-text h2, .markdown-text h3, .markdown-text strong {
    color: #ffffff !important;
}

/* Code & Pre Blocks */
pre, code {
    color: #f8fafc !important;
}

/* Accordion & Panel Containers */
.gr-accordion, .gr-panel, .gr-box, block {
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}

/* Accordion Label Text */
.gr-accordion label, .label-wrap, .accordion-title {
    color: #f8fafc !important;
    font-weight: 600 !important;
}

.badge-container {
    margin-bottom: 14px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
"""

with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue=gr.themes.colors.orange,
        neutral_hue=gr.themes.colors.slate,
    ),
    css=CUSTOM_CSS,
    title="MedNote Scribe",
) as demo:
    session_state = gr.State(value="session_default")

    gr.HTML(
        """
        <div class="header-box">
            <h1>🩺 MedNote Scribe</h1>
            <p>AI Clinical Documentation Assistant for Dr. Ananya Rao — RAG Grounded SOAP Notes & EHR Memory</p>
        </div>
        """
    )

    with gr.Row():
        # Left Column — Inputs & Examples
        with gr.Column(scale=1):
            input_box = gr.Textbox(
                label="Transcript or Patient Query",
                placeholder="Paste transcript or enter a patient command (e.g. 'What did I note for PAT-001's last visit?')...",
                lines=10,
            )

            with gr.Row():
                clear_btn = gr.Button("Clear", variant="secondary", scale=1)
                submit_btn = gr.Button("Generate Note / Run Query", variant="primary", scale=2)

            gr.Examples(
                examples=[
                    ["Patient reports headache for 3 days, worse in the morning, no nausea. BP 130/85."],
                    ["What ICD-10 code fits 'recurrent tension headache'?"],
                    ["What did I note for PAT-001's last visit?"],
                    ["Save this note to PAT-001's chart:\nS: Patient reports 50% improvement in headache frequency.\nO: BP 122/78.\nA: Suggestive of improving tension headache (G44.2).\nP: Continue stress management."],
                    ["The patient has chest pain radiating to the left arm; write the note."],
                    ["Diagnose this patient's condition for me."]
                ],
                inputs=input_box,
                label="Sample Clinical Queries & Transcripts (Click to populate)",
            )

        # Right Column — Response & Trace
        with gr.Column(scale=1):
            badge_box = gr.HTML(
                value="<span style='background:#334155; color:#f8fafc; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #475569;'>Status: Ready</span>",
                elem_classes=["badge-container"],
            )

            output_box = gr.Markdown(
                label="MedNote Scribe Clinical Note Response",
                value="*Enter a transcript or query on the left to view the grounded SOAP note response.*",
            )

            with gr.Accordion("🔍 Agent Trace & Memory Recall (Tool Execution Log)", open=True):
                trace_box = gr.HTML(
                    value="<div style='color: #94a3b8; font-size: 13.5px; font-style: italic; padding: 6px;'>Tool calls, RAG retrievals, and EHR memory recall events will appear here during query processing.</div>"
                )

    submit_btn.click(
        fn=process_query,
        inputs=[input_box, session_state],
        outputs=[output_box, trace_box, badge_box],
    )

    clear_btn.click(
        fn=lambda: (
            "",
            "*Enter a transcript or query on the left to view the grounded SOAP note response.*",
            "<div style='color: #94a3b8; font-size: 13.5px; font-style: italic; padding: 6px;'>Tool calls, RAG retrievals, and EHR memory recall events will appear here during query processing.</div>",
            "<span style='background:#334155; color:#f8fafc; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #475569;'>Status: Ready</span>",
        ),
        outputs=[input_box, output_box, trace_box, badge_box],
    )

    gr.Markdown(
        f"<div style='text-align: center; color: #94a3b8; font-size: 12.5px; margin-top: 20px;'>Model: <code>{GROQ_MODEL}</code> | RAG: ChromaDB + MiniLM | Tools: FastMCP EHR Store</div>"
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
