import json, os, re

CRITERIA = {
    "innovation": ("Innovation", "Originality and differentiation"),
    "feasibility": ("Feasibility", "Technical and delivery feasibility"),
    "impact": ("Impact", "User value and measurable outcomes"),
    "execution": ("Execution", "Completeness, clarity, and evidence"),
    "scalability": ("Scalability", "Ability to grow and maintain responsibly"),
}

def evaluate_rules(project, weights):
    """Deterministic backup rubric. Every score is based on the same evidence signals and 0–100 scale."""
    problem=(project.problem or "").strip(); solution=(project.solution or "").strip()
    description=(project.description or "").strip(); impact=(project.impact or "").strip()
    stack=(project.tech_stack or "").strip(); text=" ".join([problem,solution,description,impact,stack]).lower()
    words=set(re.findall(r"[a-z0-9]+",text)); metrics=bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:(?:percent|users|customers|hours|days|weeks|months|seconds|ms|x)\b|%)",text))
    signal=lambda terms:any(term in text for term in terms)
    breakdown={
      "innovation":min(100,35+min(20,len(words)//5)+12*signal(["novel","innovative","unique","first-of-its-kind","differentiat","new approach"])+10*signal(["alternative","existing solution","competitor","unlike"])),
      "feasibility":min(100,30+18*bool(stack)+12*bool(solution)+12*signal(["prototype","built","implemented","proof of concept","api","framework"])+14*signal(["milestone","timeline","risk","constraint","roadmap","week "])),
      "impact":min(100,28+12*bool(impact)+12*signal(["student","user","customer","community","patient","teacher","developer"])+18*metrics+15*signal(["survey","interview","pilot","tested with","feedback","validated"])),
      "execution":min(100,25+10*bool(problem)+10*bool(solution)+10*bool(description)+10*bool(impact)+10*bool(stack)+15*signal(["demo","prototype","working","deployed","tested","test result"])+10*signal(["task","milestone","completed","delivered"])),
      "scalability":min(100,30+15*signal(["scale","scalable","growth","million users","high availability"])+14*signal(["cloud","distributed","api","database","queue"])+14*signal(["maintain","modular","monitoring","security","privacy"])+12*signal(["cost","performance","reliability","capacity"])),
    }
    breakdown={k:round(float(v),1) for k,v in breakdown.items()}
    score=round(sum(breakdown[k]*weights[k] for k in CRITERIA)/100,1)
    gaps=[CRITERIA[k][0] for k,v in breakdown.items() if v<60]
    feedback=("Backup rubric: add concrete evidence for "+", ".join(gaps[:3])+".") if gaps else "Backup rubric: evidence is balanced across the criteria; validate outcomes with users and document delivery risks."
    return score,breakdown,feedback

def evaluate_openai(project, weights):
    key=os.getenv("OPENAI_API_KEY")
    if not key: raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import OpenAI
    client=OpenAI(api_key=key)
    prompt={"project":{"name":project.name,"team":project.team,"problem":project.problem,"solution":project.solution,"description":project.description,"impact":project.impact,"tech_stack":project.tech_stack},"criteria":{k:{"label":v[0],"description":v[1],"weight_percent":weights[k]} for k,v in CRITERIA.items()},"instructions":"Evaluate only evidence in the submission. Score each criterion 0-100, give concise constructive feedback, never invent facts. Return JSON with keys breakdown (criterion: numeric score), feedback (string)."}
    result=client.chat.completions.create(model="gpt-4o-mini",temperature=0.2,response_format={"type":"json_object"},messages=[{"role":"system","content":"You are a fair, consistent project evaluator. Return valid JSON."},{"role":"user","content":json.dumps(prompt)}])
    data=json.loads(result.choices[0].message.content)
    breakdown={k:max(0,min(100,float(data["breakdown"][k]))) for k in CRITERIA}
    score=round(sum(breakdown[k]*weights[k] for k in CRITERIA)/100,1)
    return score,breakdown,str(data.get("feedback","Evaluation complete."))[:1200]
