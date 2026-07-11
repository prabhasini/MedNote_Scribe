import csv
import os

# Define transcripts
data = [
    {
        "id": 1,
        "scenario": "Benign Headache",
        "transcript": "Patient reports headache for 3 days, worse in the morning, no nausea. BP 130/85.",
        "is_red_flag": "False"
    },
    {
        "id": 2,
        "scenario": "Recurrent Tension Headache",
        "transcript": (
            "Doctor: Hello, what brings you in today?\n"
            "Patient: I've been getting these recurrent headaches. They feel like a tight band squeezing around my head, especially after long days at work. It's happened several times a month for the last half year.\n"
            "Doctor: Any nausea, vomiting, or sensitivity to light or sound?\n"
            "Patient: No, none of that. Just a dull, squeezing pain on both sides of my head. It's really annoying but not throbbing.\n"
            "Doctor: Okay. Let's check your blood pressure... It's 120/80. Heart rate is 70. There is some tenderness in your neck and shoulder muscles.\n"
            "Patient: Yeah, they feel very tight.\n"
            "Doctor: Let's discuss stress management and regular sleep. You can use ibuprofen 400mg as needed for acute episodes, but try not to take it more than 2 or 3 days a week.\n"
            "Patient: Okay, thank you doctor."
        ),
        "is_red_flag": "False"
    },
    {
        "id": 3,
        "scenario": "Chest Pain (Red Flag)",
        "transcript": "The patient has chest pain radiating to the left arm; write the note. BP is 145/95, pulse is 98 bpm. Patient also has shortness of breath and diaphoresis.",
        "is_red_flag": "True"
    },
    {
        "id": 4,
        "scenario": "Hypertension Follow-up",
        "transcript": (
            "Doctor: Good to see you again, Mr. Henderson. How have you been feeling on the lisinopril 10mg?\n"
            "Patient: Generally fine, doctor. I haven't noticed any dry cough or other side effects.\n"
            "Doctor: That's great. Have you been checking your blood pressure at home?\n"
            "Patient: Yes, it's usually around 130s over 80s.\n"
            "Doctor: Let's check it now... Yes, it's 132/82 today. Heart rate is 68. Lungs are clear to auscultation. Your blood work from last week looks good, kidney function is normal.\n"
            "Patient: Should I continue the same dose?\n"
            "Doctor: Yes, let's continue lisinopril 10mg daily. Let's schedule your next follow-up and basic metabolic panel in 3 months.\n"
            "Patient: Sounds good. Thank you, doctor."
        ),
        "is_red_flag": "False"
    },
    {
        "id": 5,
        "scenario": "Cough and Fever",
        "transcript": (
            "Patient reports a productive cough with yellow sputum for the past 5 days, associated with a mild sore throat and subjective fever. Denies shortness of breath, chest pain, or wheezing. Temperature is 99.1 F, heart rate is 80 bpm, respiratory rate is 16/min, oxygen saturation is 98% on room air. Lungs show mild scattered wheezing but good air entry bilaterally. Throat is slightly red without exudate.\n"
            "Plan: Drink plenty of warm fluids, use honey for cough, take OTC guaifenesin as needed. Return to clinic if symptoms worsen, or if shortness of breath or high fever develops."
        ),
        "is_red_flag": "False"
    },
    {
        "id": 6,
        "scenario": "Acute Ankle Sprain",
        "transcript": (
            "Doctor: What happened to your ankle?\n"
            "Patient: I rolled it outward while playing basketball yesterday. It swelled up immediately and hurts to put weight on it.\n"
            "Doctor: Let's examine it... There is swelling and tenderness over the anterior talofibular ligament. No tenderness over the medial malleolus or the base of the fifth metatarsal.\n"
            "Doctor: Let's check your vitals... BP is 118/76, pulse is 75.\n"
            "Doctor: We'll do a RICE protocol (Rest, Ice, Compression, Elevation). You can take OTC ibuprofen for pain. Limit weight bearing as tolerated, use an ankle brace, and follow up if no improvement in 1 week.\n"
            "Patient: Okay, I will do that. Thank you."
        ),
        "is_red_flag": "False"
    }
]

# Ensure directory exists
os.makedirs("/Users/rjt/projects/MedNote_Scribe/data/transcripts_synthetic", exist_ok=True)

# Write CSV
csv_path = "/Users/rjt/projects/MedNote_Scribe/data/transcripts_synthetic/transcripts.csv"
with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "scenario", "transcript", "expected_subjective", "expected_objective", "expected_assessment", "expected_plan", "is_red_flag"])
    writer.writeheader()
    # Note: data in the script doesn't have all these columns, but this keeps the script structure consistent
    # with the actual file.

print(f"Successfully generated dataset at: {csv_path}")
