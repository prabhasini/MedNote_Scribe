"""EHR tool implementations for the MedNote Scribe agent."""
from .ehr_tools import EHR_TOOLS, get_patient_history, save_note

__all__ = ["save_note", "get_patient_history", "EHR_TOOLS"]
