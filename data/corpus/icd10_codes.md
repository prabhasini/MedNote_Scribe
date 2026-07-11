# ICD-10-CM Code Reference Subset

Public ICD-10-CM diagnosis codes (US Clinical Modification), FY2026 edition, covering the
conditions represented in this project's synthetic transcript dataset. Each entry below is
written as a self-contained chunk so retrieval can surface one code at a time with its context.

---

## R51.9 — Headache, unspecified
Category: R00–R99, Symptoms and signs not classified elsewhere.
Use when: the provider's documentation does not specify the type or cause of the headache.
This is a billable, non-specific code — prefer a more specific G43/G44 code when the headache
type is documented (tension-type, migraine, etc.).

---

## G44.2 — Tension-type headache (category header)
Category: G40–G47, Episodic and paroxysmal disorders.
Note: G44.2 itself is a non-billable category header. A common primary headache disorder,
characterized by dull, non-pulsatile, band-like or vice-like pressure of mild-to-moderate
intensity, often related to stress or muscle tension. Use one of the billable subcodes below
for actual documentation.

---

## G44.209 — Tension-type headache, unspecified, not intractable
Category: G40–G47, Episodic and paroxysmal disorders, subcategory of G44.2.
Use when: tension-type headache is documented but frequency (episodic vs. chronic) is not
specified, and the headache is not treatment-resistant ("not intractable").
Billable: Yes.

---

## G44.219 — Episodic tension-type headache, not intractable
Category: G40–G47, subcategory of G44.2.
Use when: tension-type headache occurring fewer than 15 days per month, not intractable.
Billable: Yes.

---

## G44.229 — Chronic tension-type headache, not intractable
Category: G40–G47, subcategory of G44.2.
Use when: tension-type headache occurring 15 or more days per month, not intractable.
Billable: Yes.

---

## G43.909 — Migraine, unspecified, not intractable, without status migrainosus
Category: G40–G47, Episodic and paroxysmal disorders.
Use when: migraine is documented (recurrent, often unilateral, pulsatile headache, sometimes
with nausea, vomiting, or light sensitivity) but subtype (with/without aura) is not specified.
Documentation caution: a patient's self-reported "migraine" without physician confirmation of
migrainous features should default to R51.9, not G43.909 — the diagnosis belongs to the
provider's assessment, not the patient's self-report.
Billable: Yes.

---

## R07.9 — Chest pain, unspecified
Category: R00–R99, Symptoms and signs not classified elsewhere.
Use when: chest pain is documented without a confirmed cause. Standard default code before
diagnostic workup (ECG, troponin, imaging) confirms or rules out a cardiac cause.
Billable: Yes.
Clinical note: chest pain radiating to the arm/jaw with shortness of breath or diaphoresis is
a red-flag symptom combination requiring urgent evaluation, independent of coding.

---

## I21.9 — Acute myocardial infarction, unspecified
Category: I20–I25, Ischemic heart diseases.
Use when: acute MI is confirmed but the specific site/type (STEMI vs. NSTEMI, wall location)
is not documented. This code should only be assigned after diagnostic confirmation — never
from symptom presentation alone.
Billable: Yes.

---

## I10 — Essential (primary) hypertension
Category: I10–I16, Hypertensive diseases.
Use when: hypertension is documented without an identified secondary cause. Most frequently
billed cardiovascular code in primary care.
Billable: Yes.

---

## E11.9 — Type 2 diabetes mellitus without complications
Category: E08–E13, Diabetes mellitus.
Use when: type 2 diabetes is documented with no associated complications (neuropathy,
nephropathy, retinopathy, etc.) noted in the encounter.
Billable: Yes.

---

## N39.0 — Urinary tract infection, site not specified
Category: N30–N39, Other diseases of the urinary system.
Use when: UTI is documented (dysuria, urinary frequency, suprapubic discomfort) without a
specified site (e.g., cystitis vs. pyelonephritis) or without urine culture confirmation yet.
Billable: Yes.

---

## J20.9 — Acute bronchitis, unspecified
Category: J20–J22, Acute lower respiratory infections.
Use when: acute bronchitis is documented (acute cough with/without sputum, fever, congestion)
but the infectious agent (viral, bacterial, etc.) is not specified.
Billable: Yes.

---

## S93.401A — Sprain of unspecified ligament of right ankle, initial encounter
Category: S90–S99, Injuries to the ankle and foot.
Use when: sprain of the right ankle is documented (tenderness over ATFL, swelling, difficulty
bearing weight) but the specific ligament involved is not specified, initial encounter.
Billable: Yes.

---

## S93.402A — Sprain of unspecified ligament of left ankle, initial encounter
Category: S90–S99, Injuries to the ankle and foot.
Use when: sprain of the left ankle is documented (tenderness, swelling, difficulty bearing weight)
but the specific ligament involved is not specified, initial encounter.
Billable: Yes.

---

## S93.409A — Sprain of unspecified ligament of unspecified ankle, initial encounter
Category: S90–S99, Injuries to the ankle and foot.
Use when: ankle sprain is documented but the side (right or left) and specific ligament are
not specified, initial encounter.
Billable: Yes.