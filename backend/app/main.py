import csv, io, os, secrets
from fastapi import FastAPI, Depends, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from .models import Project, Workspace
from .schemas import ProjectInput, EvaluateRequest, PublicSubmission
from .evaluator import CRITERIA, evaluate_batch
from .github_review import review_repository
import httpx
import logging

Base.metadata.create_all(bind=engine)
if "user_id" not in {c["name"] for c in inspect(engine).get_columns("projects")}:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE projects ADD COLUMN user_id VARCHAR(128)"))
if "evaluation_method" not in {c["name"] for c in inspect(engine).get_columns("projects")}:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE projects ADD COLUMN evaluation_method VARCHAR(32)"))
for column,sql_type in (("submitted_by","VARCHAR(240)"),("github_url","VARCHAR(500)"),("demo_url","VARCHAR(1000)"),("repository_review","TEXT")):
    if column not in {c["name"] for c in inspect(engine).get_columns("projects")}:
        with engine.begin() as conn: conn.execute(text(f"ALTER TABLE projects ADD COLUMN {column} {sql_type}"))
with engine.begin() as conn:
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_user_id ON projects (user_id)"))
app = FastAPI(title="ProjectEval API", version="1.0.0", description="Evidence-based bulk project evaluation.")
logger=logging.getLogger(__name__)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")], allow_origin_regex=r"https://.*\.vercel\.app", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def out(p):
    return {"id":p.id,"name":p.name,"team":p.team,"submitted_by":p.submitted_by,"description":p.description,"problem":p.problem,"solution":p.solution,"impact":p.impact,"tech_stack":p.tech_stack,"github_url":p.github_url,"demo_url":p.demo_url,"score":p.score,"breakdown":p.breakdown or {},"feedback":p.feedback or "","status":p.status,"evaluation_method":p.evaluation_method,"created_at":p.created_at.isoformat() if p.created_at else None}

def current_user(authorization: str | None = Header(default=None)):
    url=os.getenv("SUPABASE_URL","").rstrip("/"); anon=os.getenv("SUPABASE_ANON_KEY","")
    if not url or not anon: raise HTTPException(503,"Authentication is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401,"Sign in to continue")
    try:
        response=httpx.get(f"{url}/auth/v1/user",headers={"apikey":anon,"Authorization":authorization},timeout=8)
        if response.status_code!=200: raise HTTPException(401,"Session expired. Please sign in again.")
        user=response.json()
        if not user.get("id"): raise HTTPException(401,"Invalid user session")
        return user["id"]
    except httpx.HTTPError: raise HTTPException(503,"Authentication service is temporarily unavailable")

@app.get("/health")
def health(): return {"ok":True}

@app.get("/api/rubric")
def rubric(): return {k:{"label":v[0],"description":v[1]} for k,v in CRITERIA.items()}

@app.post("/api/workspace/share-link")
def create_share_link(db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    workspace=db.query(Workspace).filter(Workspace.user_id==user_id).first()
    if not workspace:
        workspace=Workspace(user_id=user_id,share_code=secrets.token_urlsafe(32)); db.add(workspace); db.commit(); db.refresh(workspace)
    return {"share_code":workspace.share_code}

@app.post("/api/public-submissions/{share_code}")
def public_submission(share_code:str,item:PublicSubmission,db:Session=Depends(get_db)):
    workspace=db.query(Workspace).filter(Workspace.share_code==share_code).first()
    if not workspace: raise HTTPException(404,"This submission link is invalid or has been revoked")
    try: repo_review=review_repository(item.github_url)
    except ValueError as exc: raise HTTPException(400,str(exc))
    except Exception as exc:
        logger.warning("GitHub repository review unavailable for submission: %s",exc)
        repo_review="GitHub review unavailable. Review this repository manually before scoring."
    data=item.model_dump(); data["repository_review"]=repo_review
    project=Project(**data,user_id=workspace.user_id,status="pending"); db.add(project); db.commit(); db.refresh(project)
    return {"id":project.id,"name":project.name,"message":"Submission received. Your project is now in the evaluator's review queue."}

@app.get("/api/projects")
def list_projects(db:Session=Depends(get_db),user_id:str=Depends(current_user)): return [out(p) for p in db.query(Project).filter(Project.user_id==user_id).order_by(Project.id.desc()).limit(1000).all()]

@app.post("/api/projects")
def add_project(item:ProjectInput,db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    p=Project(**item.model_dump(),user_id=user_id); db.add(p); db.commit(); db.refresh(p); return out(p)

@app.post("/api/projects/import")
async def import_projects(file:UploadFile=File(...),db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    if not file.filename.lower().endswith(".csv"): raise HTTPException(400,"Upload a CSV file")
    try:
        content=(await file.read()).decode("utf-8-sig"); reader=csv.DictReader(io.StringIO(content))
        if not reader.fieldnames or not ({x.strip().lower().replace(" ","_") for x in reader.fieldnames}&{"name","project_name"}): raise HTTPException(400,"CSV needs a name or project_name column")
        rows=list(reader)
        if not rows: raise HTTPException(400,"CSV has no project rows")
        if len(rows)>500: raise HTTPException(400,"Import limit is 500 projects per file")
        allowed={"name","team","description","problem","solution","impact","tech_stack"}; projects=[]
        for raw in rows:
            row={k.strip().lower().replace(" ","_"):(v or "").strip() for k,v in raw.items() if k}
            name=row.get("name") or row.get("project_name")
            if name:
                data={k:row.get(k,"") for k in allowed}; data["name"]=name; data["team"]=data["team"] or "Unassigned"; projects.append(Project(**data,user_id=user_id))
        if not projects: raise HTTPException(400,"No rows had a project name")
        db.add_all(projects); db.commit(); return {"imported":len(projects),"message":f"Imported {len(projects)} projects"}
    except UnicodeDecodeError: raise HTTPException(400,"CSV must use UTF-8 encoding")

@app.post("/api/evaluate")
def evaluate_projects(req:EvaluateRequest,db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    weights=req.weights or {"innovation":20,"feasibility":20,"impact":25,"execution":20,"scalability":15}
    if set(weights)!=set(CRITERIA) or any(v<0 for v in weights.values()) or abs(sum(weights.values())-100)>.01: raise HTTPException(400,"Provide all five non-negative rubric weights totaling 100")
    q=db.query(Project).filter(Project.user_id==user_id)
    if req.project_ids is not None: q=q.filter(Project.id.in_(req.project_ids))
    projects=q.filter(Project.status!="evaluated").all() if req.project_ids is None else q.all()
    for p in projects: p.status="evaluating"
    db.commit()
    # Pick one evaluator for the entire batch. Discard partial AI results on any failure.
    results,method,fallback_reason=evaluate_batch(projects,weights,bool(os.getenv("OPENAI_API_KEY")))
    if fallback_reason:
        logger.warning("OpenAI batch evaluation failed; using backup rubric for all %d projects: %s",len(projects),fallback_reason)
    for p,result in zip(projects,results):
        p.score,p.breakdown,p.feedback=result; p.evaluation_method=method; p.status="evaluated"
    db.commit(); return {"evaluated":sum(p.status=="evaluated" for p in projects),"failed":sum(p.status=="failed" for p in projects),"evaluation_method":method}

@app.get("/api/stats")
def stats(db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    items=db.query(Project).filter(Project.user_id==user_id).all(); scored=[p for p in items if p.score is not None]
    return {"total":len(items),"evaluated":len(scored),"pending":len(items)-len(scored),"average":round(sum(p.score for p in scored)/len(scored),1) if scored else 0,"top_score":max((p.score for p in scored),default=0)}

