from pydantic import BaseModel, Field

class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    team: str = "Unassigned"
    description: str = ""
    problem: str = ""
    solution: str = ""
    impact: str = ""
    tech_stack: str = ""

class ProjectOut(ProjectInput):
    id: int
    score: float | None = None
    breakdown: dict = {}
    feedback: str = ""
    status: str
    created_at: str | None = None
    class Config:
        from_attributes = True

class EvaluateRequest(BaseModel):
    project_ids: list[int] | None = None
    weights: dict[str, float] | None = None
