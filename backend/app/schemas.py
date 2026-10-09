from pydantic import BaseModel, Field

class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    team: str = "Unassigned"
    submitted_by: str = "Workspace owner"
    description: str = ""
    problem: str = ""
    solution: str = ""
    impact: str = ""
    tech_stack: str = ""
    github_url: str = ""
    demo_url: str = ""
    repository_review: str = ""

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

class PublicSubmission(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    team: str = Field(default="Unassigned", max_length=240)
    submitted_by: str = Field(default="Participant", max_length=240)
    description: str = Field(default="", max_length=10000)
    problem: str = Field(default="", max_length=10000)
    solution: str = Field(default="", max_length=10000)
    impact: str = Field(default="", max_length=10000)
    tech_stack: str = Field(default="", max_length=500)
    github_url: str = Field(min_length=1, max_length=500)
    demo_url: str = ""
