from pydantic import BaseModel, RootModel
from typing import List, Optional


class ClaimResult(BaseModel):
    label: str  # "True" or "False"
    evidence: str


# Root model holding a JSON array of strings
class ExtractedClaims(RootModel[list[str]]):
    pass


class AdditionalInfoItem(BaseModel):
    question: str  # Question to extract the needed information
    purpose: str  # What this information is needed for


class FactCheckPlan(BaseModel):
    prerequisites: List[str]  # List of prerequisite statements to validate
    additional_info_needed: List[AdditionalInfoItem]  # Information that needs to be extracted
    final_claim_template: str  # Template for final claim once all info is gathered
