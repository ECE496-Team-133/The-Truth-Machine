from pydantic import BaseModel, RootModel


class ClaimResult(BaseModel):
    label: str  # "True" or "False"
    evidence: str


# Root model holding a JSON array of strings
class ExtractedClaims(RootModel[list[str]]):
    pass
