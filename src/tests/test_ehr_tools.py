"""Smoke test for Task #11 — save_note and get_patient_history tools."""
import json
import sys

sys.path.insert(0, "src")

from tools.ehr_tools import get_patient_history, save_note

results = []

# Test 1: successful save
r = save_note.invoke({"patient_id": "PAT-001", "note": "S: Test note\nO: BP 120/80\nA: ...\nP: ..."})
assert r["status"] == "success", f"Test 1 failed: {r}"
assert "note_id" in r
assert "Awaiting physician sign-off" in r["message"]
results.append(("Test 1: save success", "PASS", r["note_id"]))

# Test 2: empty note
r = save_note.invoke({"patient_id": "PAT-001", "note": "   "})
assert r["status"] == "error"
assert r["error_code"] == "EMPTY_NOTE"
results.append(("Test 2: empty note", "PASS", r["error_code"]))

# Test 3: new/unknown patient auto-register on save
r = save_note.invoke({"patient_id": "PAT-999", "note": "S: something"})
assert r["status"] == "success", f"Test 3 failed: {r}"
assert "note_id" in r
results.append(("Test 3: new patient auto-registered on save", "PASS", r["note_id"]))

# Test 4: invalid date
r = save_note.invoke({"patient_id": "PAT-001", "note": "S: note", "visit_date": "not-a-date"})
assert r["status"] == "error"
assert r["error_code"] == "INVALID_DATE"
results.append(("Test 4: invalid date", "PASS", r["error_code"]))

# Test 5: history for known patient (PAT-001 has 1 seeded visit + 1 just saved above)
r = get_patient_history.invoke({"patient_id": "PAT-001"})
assert r["status"] == "success"
assert r["visit_count"] >= 1
results.append(("Test 5: history PAT-001", "PASS", f"visit_count={r['visit_count']}"))

# Test 6: patient with zero visits — no history
r = get_patient_history.invoke({"patient_id": "PAT-006"})
assert r["status"] == "success"
assert r["visit_count"] == 0
assert "new patient" in r["message"].lower()
results.append(("Test 6: patient with 0 visits PAT-006", "PASS", r["message"][:60]))


# Test 7: unknown patient ID in get_patient_history returns empty history gracefully
r = get_patient_history.invoke({"patient_id": "PAT-888"})
assert r["status"] == "success"
assert r["visit_count"] == 0
results.append(("Test 7: unknown patient history returns 0 visits", "PASS", f"visit_count={r['visit_count']}"))


print("\n" + "=" * 60)
print("EHR Tools Smoke Test Results")
print("=" * 60)
for name, status, detail in results:
    print(f"  [{status}]  {name}  →  {detail}")
print("=" * 60)
print(f"All {len(results)} tests passed.\n")
