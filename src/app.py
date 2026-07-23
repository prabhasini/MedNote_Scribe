"""
app.py — Professional, high-contrast Slate/Dark Gradio web interface for MedNote Scribe.

UI Layout Features:
- Soft Slate/Dark background (#1e293b / #0f172a).
- Full Patient Identifier Banner (Dropdown + Auto-Generated Patient ID for New Patient).
- Structured Visual "Wells" for SOAP sections (Subjective [Blue], Objective [Green], Assessment [Amber], Plan [Orange]).
- Dedicated ICD-10 Suggested Codes Tag Tiles section at the end of the note.
- Full-width Agent Trace & Memory Panel at the bottom (collapsed/minimized by default).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import gradio as gr
from agent import run_agent_with_trace
from config import EHR_STORE_PATH, GROQ_MODEL

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")


def get_known_patients() -> list[tuple[str, str]]:
    """Load list of known patients from EHR store for dropdown choices."""
    if not EHR_STORE_PATH.exists():
        return [("PAT-001", "PAT-001 (Synthetic Patient A)")]

    try:
        with open(EHR_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        choices = []
        for pid, pdata in data.get("patients", {}).items():
            name = pdata.get("name", "Unknown")
            dob = pdata.get("dob", "N/A")
            vcount = len(pdata.get("visits", []))
            vlabel = f"{vcount} visits" if vcount > 0 else "New Patient"
            label = f"{pid} | {name} ({vlabel}, DOB: {dob})"
            choices.append((label, pid))

        choices.append(("➕ Create New Patient ID...", "NEW_PATIENT"))
        return choices
    except Exception as exc:
        log.error("Failed to load patient choices from EHR store: %s", exc)
        return [("PAT-001", "PAT-001")]


def generate_next_patient_id() -> str:
    """Scan EHR store and auto-generate next sequential Patient ID (e.g. PAT-007)."""
    if not EHR_STORE_PATH.exists():
        return "PAT-007"

    try:
        with open(EHR_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        existing_ids = list(data.get("patients", {}).keys())
        max_num = 0
        for pid in existing_ids:
            match = re.search(r'PAT-(\d+)', pid)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

        next_num = max_num + 1
        return f"PAT-{next_num:03d}"
    except Exception as exc:
        log.error("Failed to generate next patient ID: %s", exc)
        return "PAT-007"


def render_patient_banner(patient_id: str, custom_id: str = "") -> str:
    """Render high-contrast HTML banner card for the currently selected patient."""
    resolved_id = custom_id.strip() if patient_id == "NEW_PATIENT" else patient_id

    if not resolved_id:
        resolved_id = "PAT-001"

    if not EHR_STORE_PATH.exists():
        return f"""
        <div class="patient-banner" style="background:#1e293b; border:1px solid #334155; border-left:5px solid #f97316; padding:14px 18px; border-radius:10px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#f8fafc; font-size:16px;">👤 Selected Patient: <code style="background:#ea580c; color:#fff; padding:2px 8px; border-radius:4px;">{resolved_id}</code></span>
                <span style="color:#94a3b8; font-size:13px;">EHR Store Initializing</span>
            </div>
        </div>
        """

    try:
        with open(EHR_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        patient = data.get("patients", {}).get(resolved_id)

        if not patient:
            return f"""
            <div class="patient-banner" style="background:#1e293b; border:1px solid #334155; border-left:5px solid #22c55e; padding:14px 18px; border-radius:10px; margin-bottom:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:700; color:#ffffff; font-size:16px;">👤 Patient ID: <code style="background:#166534; color:#fff; padding:2px 8px; border-radius:4px;">{resolved_id}</code> (New Patient Chart)</span>
                    <span style="background:#14532d; color:#bbf7d0; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; border:1px solid #22c55e;">🆕 Initial Registration</span>
                </div>
                <div style="color:#cbd5e1; font-size:13.5px; margin-top:6px;">No prior visit history. Generating a new chart for <code>{resolved_id}</code>.</div>
            </div>
            """

        name = patient.get("name", "Synthetic Patient")
        dob = patient.get("dob", "N/A")
        visits = patient.get("visits", [])
        v_count = len(visits)

        past_codes = set()
        for v in visits:
            for c in v.get("icd10_suggestions", []):
                past_codes.add(c)
        codes_str = ", ".join(sorted(past_codes)) if past_codes else "None recorded"

        last_visit_date = visits[0]["visit_date"] if v_count > 0 else "None"
        last_note_summary = visits[0]["note"][:140] + "..." if v_count > 0 else "No prior visit notes."

        return f"""
        <div class="patient-banner" style="background:#1e293b; border:1px solid #334155; border-left:5px solid #f97316; padding:14px 18px; border-radius:10px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; color:#ffffff; font-size:16px;">👤 Patient Chart: <strong style="color:#f97316;">{name}</strong> (<code style="background:#334155; color:#f8fafc; padding:2px 6px; border-radius:4px;">{resolved_id}</code>)</span>
                <span style="background:#1e3a8a; color:#bfdbfe; padding:4px 12px; border-radius:14px; font-size:12.5px; font-weight:600; border:1px solid #3b82f6;">📅 Visits: {v_count}</span>
            </div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:10px; font-size:13px; color:#cbd5e1; background:#0f172a; padding:10px 12px; border-radius:6px; border:1px solid #334155;">
                <div><strong>DOB:</strong> {dob}</div>
                <div><strong>Last Visit Date:</strong> {last_visit_date}</div>
                <div><strong>Active / Past ICD-10s:</strong> <code style="color:#fdba74;">{codes_str}</code></div>
            </div>
            <div style="margin-top:8px; font-size:12.5px; color:#94a3b8; font-style:italic;">
                <strong>Latest Chart History:</strong> "{last_note_summary}"
            </div>
        </div>
        """
    except Exception as exc:
        log.error("Error rendering patient banner: %s", exc)
        return f"<div style='color:#f8fafc;'>Patient ID: {resolved_id}</div>"


def format_clean_soap_section(text: str) -> str:
    """Format SOAP section text into clean HTML with ○ bullets and paragraphs."""
    if not text or not text.strip():
        return "<div style='color:#94a3b8; font-style:italic;'>Not documented.</div>"

    cleaned = text.strip()

    lines = cleaned.split('\n')
    items_html = []

    # A line that is ONLY a bullet/circle decorator with no real text content
    lone_decorator_re = re.compile(r'^[\u25cb\u25e6\u2022\u00b7\*\-\+]\s*$')
    # A line where bullet/circle + space(s) + actual text are all together
    inline_bullet_re  = re.compile(r'^[\u25cb\u25e6\u2022\u00b7\*\-\+]\s+(.+)$')

    for line in lines:
        l = line.strip()
        if not l:
            continue

        # Skip lone decorator lines (○ or • or - alone on a line)
        if lone_decorator_re.match(l):
            continue

        # Check if bullet + text are on the SAME line
        m = inline_bullet_re.match(l)
        if m:
            content = m.group(1).strip()
            is_bullet = True
        else:
            content = l
            is_bullet = False

        # Convert **bold** → <strong>
        content = re.sub(
            r'\*\*(.*?)\*\*',
            r'<strong style="color:#f1f5f9; font-weight:600;">\1</strong>',
            content,
        )
        # Remove stray lone asterisks (but don't touch content inside <strong>)
        content = re.sub(r'(?<!<strong[^>]*>)\*(?!</strong>)', '', content)

        if is_bullet:
            items_html.append(
                f'<li style="margin-bottom:5px; list-style-type:none; display:flex; align-items:flex-start; gap:10px;">'
                f'<span style="color:#94a3b8; font-size:14px; line-height:1.55; flex-shrink:0;">○</span>'
                f'<span style="color:#cbd5e1; font-size:13.5px; line-height:1.60;">{content}</span>'
                f'</li>'
            )
        else:
            items_html.append(
                f'<p style="margin:0 0 7px 0; color:#cbd5e1; font-size:13.5px; line-height:1.65;">{content}</p>'
            )

    # Wrap consecutive <li> items in a <ul>
    grouped = []
    in_ul = False
    for item in items_html:
        if item.startswith('<li'):
            if not in_ul:
                grouped.append('<ul style="padding:0; margin:4px 0 4px 0; list-style:none;">')
                in_ul = True
            grouped.append(item)
        else:
            if in_ul:
                grouped.append('</ul>')
                in_ul = False
            grouped.append(item)
    if in_ul:
        grouped.append('</ul>')

    return ''.join(grouped)


def render_structured_soap_wells(response_text: str) -> str:
    """Parse SOAP sections and render structured wells with bold headers and content."""
    if not response_text.strip():
        return "<div style='color:#94a3b8; padding:8px;'>No content generated.</div>"

    # Very permissive SOAP header patterns — match any common LLM heading format:
    # **Subjective**, ## Subjective, SUBJECTIVE:, Subjective:, Subjective (alone on line), etc.
    def _soap_pattern(word: str) -> re.Pattern:
        return re.compile(
            r'(?:^|\n)\s*(?:[\*\#]{0,3}\s*)' + word + r'(?:\s*[\*\#]{0,3})\s*[:\n]',
            re.IGNORECASE,
        )

    sub_pattern = _soap_pattern('Subjective')
    obj_pattern = _soap_pattern('Objective')
    ass_pattern = _soap_pattern('Assessment')
    pla_pattern = _soap_pattern('Plan')

    s_match = sub_pattern.search(response_text)
    o_match = obj_pattern.search(response_text)
    a_match = ass_pattern.search(response_text)
    p_match = pla_pattern.search(response_text)

    # --- Structured SOAP render ---
    if s_match and o_match and a_match and p_match:
        s_text = response_text[s_match.end(): o_match.start()].strip()
        o_text = response_text[o_match.end(): a_match.start()].strip()
        a_text = response_text[a_match.end(): p_match.start()].strip()
        p_text = response_text[p_match.end():].strip()

        # Strip any leftover section-header keywords from within the content blocks
        for kw in ['**Subjective**', '**Objective**', '**Assessment**', '**Plan**',
                   'SUBJECTIVE:', 'OBJECTIVE:', 'ASSESSMENT:', 'PLAN:',
                   'Subjective:', 'Objective:', 'Assessment:', 'Plan:']:
            s_text = s_text.replace(kw, '').strip()
            o_text = o_text.replace(kw, '').strip()
            a_text = a_text.replace(kw, '').strip()
            p_text = p_text.replace(kw, '').strip()

        def _section(label: str, content: str) -> str:
            return (
                f'<div style="padding: 14px 20px 12px 20px;">'
                f'<div style="font-weight:700; color:#f1f5f9; font-size:14.5px; margin-bottom:8px; letter-spacing:0.01em;">'
                f'{label}</div>'
                f'<div>{format_clean_soap_section(content)}</div>'
                f'</div>'
            )

        _hr = '<hr style="border:none; border-top:1px solid #334155; margin:0;">'

        return (
            '<div style="background:#1e293b; border:1px solid #334155; border-radius:12px; '
            'overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.25); margin-top:4px;">'
            + _section('Subjective', s_text)
            + _hr
            + _section('Objective', o_text)
            + _hr
            + _section('Assessment', a_text)
            + _hr
            + _section('Plan', p_text)
            + '</div>'
        )

    # --- Urgent escalation fallback ---
    if 'urgent escalation' in response_text.lower() or 'emergency' in response_text.lower():
        clean_text = format_clean_soap_section(response_text)
        return (
            '<div style="background:#450a0a; border:1px solid #991b1b; border-left:6px solid #ef4444; '
            'padding:16px 20px; border-radius:10px; margin-bottom:14px;">'
            '<div style="font-weight:800; color:#fca5a5; font-size:16px; margin-bottom:8px;">'
            '⚠️ URGENT CLINICAL ESCALATION REQUIRED</div>'
            f'<div style="color:#fef2f2; font-size:14px; line-height:1.65;">{clean_text}</div>'
            '</div>'
        )

    # --- Generic Q&A / info fallback ---
    clean_resp = format_clean_soap_section(response_text)
    return (
        '<div style="background:#1e293b; border:1px solid #334155; border-left:5px solid #3b82f6; '
        'padding:16px 20px; border-radius:10px;">'
        '<div style="font-weight:700; color:#93c5fd; font-size:15px; margin-bottom:8px;">💬 Clinical Response:</div>'
        f'<div style="color:#f8fafc; font-size:14.5px; line-height:1.65;">{clean_resp}</div>'
        '</div>'
    )



def extract_icd10_tiles(text: str) -> str:
    """Extract ICD-10 codes from agent output and format as HTML tag tiles."""
    code_pattern = re.compile(r'\b([A-Z]\d{2}(?:\.\d{1,4})?)\b')
    matched_codes = sorted(list(set(code_pattern.findall(text))))

    descriptions = {
        "G44.2": "Tension-type headache",
        "I10": "Essential (primary) hypertension",
        "I21.9": "Acute myocardial infarction, unspecified",
        "I63.9": "Cerebral infarction, unspecified (Stroke)",
        "J20.9": "Acute bronchitis, unspecified",
        "S93.401A": "Sprain of ligament of right ankle, initial encounter",
        "E11.9": "Type 2 diabetes mellitus without complications",
        "M54.5": "Low back pain, unspecified",
        "M20.21": "Hallux rigidus, right foot",
        "R05.9": "Cough, unspecified",
    }

    if not matched_codes:
        return """
        <div style="background:#1e293b; border:1px solid #334155; padding:12px; border-radius:8px; color:#94a3b8; font-size:13px; font-style:italic;">
            🏷️ No ICD-10 code suggestions identified in this response.
        </div>
        """

    tiles = []
    for code in matched_codes:
        desc = descriptions.get(code, "Suggested ICD-10 Code")
        tiles.append(
            f"""
            <div style="display:inline-flex; align-items:center; gap:8px; background:linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%); border:1px solid #3b82f6; padding:8px 14px; border-radius:20px; color:#ffffff; font-size:13.5px; font-weight:600; box-shadow: 0 2px 6px rgba(0,0,0,0.2);">
                <span style="background:#2563eb; color:#ffffff; padding:2px 8px; border-radius:12px; font-family:monospace; font-size:13px; font-weight:700;">🏷️ {code}</span>
                <span style="color:#dbeafe; font-weight:500;">{desc}</span>
                <span style="color:#93c5fd; font-size:11px; font-style:italic; border-left:1px solid #3b82f6; padding-left:6px;">(Pending Confirmation)</span>
            </div>
            """
        )

    return f"""
    <div style="background:#0f172a; border:1px solid #334155; padding:14px 16px; border-radius:10px; margin-top:14px;">
        <div style="font-weight:700; color:#93c5fd; font-size:14px; margin-bottom:10px; display:flex; align-items:center; gap:6px;">
            📌 Suggested ICD-10 Coding Tags (RAG Grounded):
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:10px;">
            {"".join(tiles)}
        </div>
    </div>
    """


def process_query(user_input: str, patient_id_choice: str, custom_patient_id: str, session_id: str) -> tuple[str, str, str, str, str]:
    """Process query and return (soap_wells_html, tiles_html, trace_html, badge_html, banner_html)."""
    resolved_patient_id = custom_patient_id.strip() if patient_id_choice == "NEW_PATIENT" else patient_id_choice

    if not resolved_patient_id:
        resolved_patient_id = "PAT-001"

    if not user_input.strip():
        banner_html = render_patient_banner(patient_id_choice, custom_patient_id)
        empty_tiles = "<div style='color:#94a3b8; font-size:13px; font-style:italic; padding:6px;'>No code tags generated yet.</div>"
        empty_soap = "<div style='color:#cbd5e1; font-style:italic; padding:12px;'>Select a patient above and enter a transcript on the left to view the grounded SOAP note response.</div>"
        return (
            empty_soap,
            empty_tiles,
            "<div style='color: #94a3b8; font-style: italic; padding: 8px;'>No trace events generated yet.</div>",
            "<span style='background:#334155; color:#f8fafc; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #475569;'>Status: Ready</span>",
            banner_html,
        )

    try:
        prompt_with_patient_context = (
            f"[Target Patient Context: patient_id='{resolved_patient_id}']\n"
            f"Target Patient ID: '{resolved_patient_id}'. Please process the input below. "
            f"If generating a SOAP note from a transcript, you MUST call the save_note tool "
            f"with patient_id='{resolved_patient_id}' and the full SOAP note content to save it into ehr_store.json:\n\n{user_input}"
        )

        response_text, trace_events = asyncio.run(
            run_agent_with_trace(prompt_with_patient_context, thread_id=f"session_{resolved_patient_id}")
        )

        banner_html = render_patient_banner(patient_id_choice, custom_patient_id)
        soap_wells_html = render_structured_soap_wells(response_text)
        tiles_html = extract_icd10_tiles(response_text)

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

            badges = [f"<span style='background:#431407; color:#ffedd5; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #f97316;'>👤 Patient: {resolved_patient_id}</span>"]
            if has_rag:
                badges.append("<span style='background:#1e3a8a; color:#bfdbfe; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #3b82f6;'>🔍 RAG Context Retrieved</span>")
            if has_ehr:
                badges.append("<span style='background:#14532d; color:#bbf7d0; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #22c55e;'>💾 EHR Store Accessed</span>")

            badge_html = " ".join(badges)

        fresh_choices = get_known_patients()
        fresh_labels = [c[0] for c in fresh_choices]
        target_val = None
        for choice in fresh_choices:
            if choice[1] == resolved_patient_id:
                target_val = choice[0]
                break

        updated_dropdown = gr.update(choices=fresh_labels, value=target_val) if target_val else gr.update(choices=fresh_labels)

        return soap_wells_html, tiles_html, trace_html, badge_html, banner_html, updated_dropdown

    except Exception as exc:
        log.error("Error processing query in UI: %s", exc, exc_info=True)
        banner_html = render_patient_banner(patient_id_choice, custom_patient_id)
        err_html = f"<div style='color: #fca5a5; font-weight:600; padding:12px; background:#450a0a; border:1px solid #ef4444; border-radius:8px;'>❌ Error running agent: {exc}</div>"
        fresh_choices = get_known_patients()
        return (
            err_html,
            "",
            f"<div style='color: #fca5a5; font-weight:600; padding: 8px;'>Execution Error: {exc}</div>",
            "<span style='background:#7f1d1d; color:#fecaca; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #ef4444;'>❌ Execution Error</span>",
            banner_html,
            gr.update(choices=[c[0] for c in fresh_choices]),
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
    padding: 22px 26px;
    border-radius: 12px;
    margin-bottom: 16px;
    border: 1px solid #475569;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
.header-box h1 {
    color: #ffffff !important;
    margin: 0 0 6px 0 !important;
    font-size: 26px;
    font-weight: 700;
}
.header-box p {
    color: #cbd5e1 !important;
    margin: 0 !important;
    font-size: 14.5px;
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
    margin-bottom: 12px;
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

    # Top Section — Patient Banner & Selection Controls
    with gr.Row():
        with gr.Column(scale=2):
            patient_choices = get_known_patients()
            patient_dropdown = gr.Dropdown(
                choices=[c[0] for c in patient_choices],
                value=patient_choices[0][0],
                label="Select Active EHR Patient Chart",
                interactive=True,
            )
        with gr.Column(scale=1, visible=False) as custom_id_col:
            custom_id_box = gr.Textbox(
                label="Custom New Patient ID",
                placeholder="e.g. PAT-007",
                value="",
            )

    # Dynamic Patient Banner Display
    patient_banner_box = gr.HTML(
        value=render_patient_banner("PAT-001"),
    )

    # Main Two-Column Row for Input vs SOAP Note Output
    with gr.Row():
        # Left Column — Inputs & Examples
        with gr.Column(scale=1):
            input_box = gr.Textbox(
                label="Transcript or Clinical Query",
                placeholder="Paste transcript or enter a patient command (e.g. 'What did I note for this patient's last visit?')...",
                lines=12,
            )

            with gr.Row():
                clear_btn = gr.Button("Clear", variant="secondary", scale=1)
                submit_btn = gr.Button("Generate Note / Run Query", variant="primary", scale=2)

            gr.Examples(
                examples=[
                    ["Patient reports headache for 3 days, worse in the morning, no nausea. BP 130/85."],
                    ["What did I note for this patient's last visit?"],
                    ["What ICD-10 code fits 'recurrent tension headache'?"],
                    ["Save this note to the patient's chart:\nS: Patient reports 50% improvement in headache frequency.\nO: BP 122/78.\nA: Suggestive of improving tension headache (G44.2).\nP: Continue stress management."],
                    ["The patient has chest pain radiating to the left arm; write the note."],
                    ["Diagnose this patient's condition for me."]
                ],
                inputs=input_box,
                label="Sample Clinical Queries & Transcripts (Click to populate)",
            )

        # Right Column — Structured SOAP Wells & ICD-10 Code Tiles
        with gr.Column(scale=1):
            badge_box = gr.HTML(
                value="<span style='background:#334155; color:#f8fafc; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #475569;'>Status: Ready</span>",
                elem_classes=["badge-container"],
            )

            # High-Contrast Visual SOAP Wells HTML Box
            output_box = gr.HTML(
                value="<div style='color:#cbd5e1; font-style:italic; padding:12px; background:#1e293b; border:1px solid #334155; border-radius:10px;'>Select a patient above and enter a transcript on the left to view the grounded SOAP note response.</div>",
                label="Structured SOAP Clinical Note Wells",
            )

            # Dedicated Section for ICD-10 Suggested Coding Tags / Tiles
            icd10_tiles_box = gr.HTML(
                value="<div style='color:#94a3b8; font-size:13px; font-style:italic; padding:6px;'>Suggested ICD-10 code tiles will appear here.</div>",
                label="ICD-10 Code Tags",
            )

    # Full-Width Section at Bottom — Agent Trace & Memory Log (Minimized by Default)
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Accordion("🔍 Agent Trace & Memory Recall (Tool Execution Log)", open=False):
                trace_box = gr.HTML(
                    value="<div style='color: #94a3b8; font-size: 13.5px; font-style: italic; padding: 6px;'>Tool calls, RAG retrievals, and EHR memory recall events will appear here during query processing.</div>"
                )

    # Helper mapping dropdown label to patient ID
    def resolve_pid_from_dropdown(label: str) -> str:
        if "NEW_PATIENT" in label or "➕ Create New Patient" in label:
            return "NEW_PATIENT"
        current_choices = get_known_patients()
        for choice in current_choices:
            if choice[0] == label:
                return choice[1]
        if "|" in label:
            return label.split("|")[0].strip()
        return "PAT-001"


    # Dropdown change event — updates custom ID visibility, auto-generates next ID, and re-renders banner
    def on_patient_change(selected_label: str, custom_id_val: str):
        pid = resolve_pid_from_dropdown(selected_label)
        show_custom = (pid == "NEW_PATIENT")
        auto_id = generate_next_patient_id() if show_custom else custom_id_val
        banner = render_patient_banner(pid, auto_id)
        return gr.update(visible=show_custom), gr.update(value=auto_id), banner

    patient_dropdown.change(
        fn=on_patient_change,
        inputs=[patient_dropdown, custom_id_box],
        outputs=[custom_id_col, custom_id_box, patient_banner_box],
    )

    custom_id_box.change(
        fn=lambda selected_label, custom_id_val: render_patient_banner(resolve_pid_from_dropdown(selected_label), custom_id_val),
        inputs=[patient_dropdown, custom_id_box],
        outputs=[patient_banner_box],
    )

    submit_btn.click(
        fn=lambda text, sel, custom, sess: process_query(text, resolve_pid_from_dropdown(sel), custom, sess),
        inputs=[input_box, patient_dropdown, custom_id_box, session_state],
        outputs=[output_box, icd10_tiles_box, trace_box, badge_box, patient_banner_box, patient_dropdown],
    )

    clear_btn.click(
        fn=lambda sel, custom: (
            "<div style='color:#cbd5e1; font-style:italic; padding:12px; background:#1e293b; border:1px solid #334155; border-radius:10px;'>Select a patient above and enter a transcript on the left to view the grounded SOAP note response.</div>",
            "<div style='color:#94a3b8; font-size:13px; font-style:italic; padding:6px;'>Suggested ICD-10 code tiles will appear here.</div>",
            "",
            "<div style='color: #94a3b8; font-size: 13.5px; font-style: italic; padding: 6px;'>Tool calls, RAG retrievals, and EHR memory recall events will appear here during query processing.</div>",
            "<span style='background:#334155; color:#f8fafc; padding:5px 12px; border-radius:16px; font-weight:600; font-size:13px; border:1px solid #475569;'>Status: Ready</span>",
            render_patient_banner(resolve_pid_from_dropdown(sel), custom),
            gr.update(choices=[c[0] for c in get_known_patients()]),
        ),
        inputs=[patient_dropdown, custom_id_box],
        outputs=[output_box, icd10_tiles_box, input_box, trace_box, badge_box, patient_banner_box, patient_dropdown],
    )


    gr.Markdown(
        f"<div style='text-align: center; color: #94a3b8; font-size: 12.5px; margin-top: 20px;'>Model: <code>{GROQ_MODEL}</code> | RAG: ChromaDB + MiniLM | Tools: FastMCP EHR Store</div>"
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
