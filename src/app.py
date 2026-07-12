import sys
import logging
from pathlib import Path
import os

# Add parent directory to path to allow absolute imports from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gradio as gr
from chatbot import build_chain, load_system_prompt
from config import SYSTEM_PROMPT_PATH, GROQ_MODEL

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load prompt and construct LCEL chain
system_prompt = load_system_prompt(SYSTEM_PROMPT_PATH)
chain = build_chain(system_prompt)


def process_input(user_input: str) -> str:
    """Invokes the LangChain retrieval & prompt chain and returns response text."""
    if not user_input.strip():
        return "Please enter a transcript or query."
    try:
        response = chain.invoke({"user_input": user_input})
        return response
    except Exception as e:
        log.error(f"Error invoking chain: {e}")
        return f"Error: {e}\n\nMake sure your GROQ_API_KEY is configured in your .env file."


# Build custom Gradio Blocks interface
with gr.Blocks(theme=gr.themes.Soft(), title="MedNote Scribe") as demo:
    gr.Markdown(
        """
        # 🩺 MedNote Scribe
        ### Clinical Documentation Assistant for Dr. Rao
        Paste a doctor-patient conversation transcript or query below to generate structured, RAG-grounded SOAP notes and ICD-10 suggestions.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            input_box = gr.Textbox(
                label="Transcript or Query Input",
                placeholder="Enter transcript (e.g. 'Patient reports headache...') or ask a clinical documentation question...",
                lines=8,
            )
            submit_btn = gr.Button("Generate Note / Query", variant="primary")

            # Example inputs
            gr.Examples(
                examples=[
                    ["Patient reports headache for 3 days, worse in the morning, no nausea. BP 130/85."],
                    ["What ICD-10 code fits 'recurrent tension headache'?"],
                    ["The patient has chest pain radiating to the left arm; write the note."],
                    ["Diagnose this patient's condition for me."]
                ],
                inputs=input_box,
                label="Sample Inputs (Click to populate)"
            )

        with gr.Column(scale=1):
            output_box = gr.Markdown(
                label="MedNote Scribe Response"
            )

    submit_btn.click(
        fn=process_input,
        inputs=input_box,
        outputs=output_box,
    )

    gr.Markdown(
        f"*Running with Model: `{GROQ_MODEL}` | RAG enabled (HuggingFace + Chroma DB)*"
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
