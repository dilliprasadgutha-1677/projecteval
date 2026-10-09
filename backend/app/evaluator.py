import json, os

CRITERIA = {
    "innovation": ("Innovation", "Originality and differentiation"),
    "feasibility": ("Feasibility", "Technical and delivery feasibility"),
    "impact": ("Impact", "User value and measurable outcomes"),
    "execution": ("Execution", "Completeness, clarity, and evidence"),
    "scalability": ("Scalability", "Ability to grow and maintain responsibly"),
}

def evaluate_rules(project, weights):
    fields = [project.problem, project.solution, project.description, project.impact, project.tech_stack]
    text = " ".join(fields).lower()
    scores = {
        "innovation": 45 + min(35, len(set(text.split())) / 4),
        "feasibility": 40 + min(40, len(project.tech_stack.split(",")) * 10 + (15 if project.solution else 0)),
        "impact": 35 + min(50, len(project.impact.split()) * 3),
        "execution": 35 + min(50, sum(bool(x.strip()) for x in fields) * 10),
        "scalability": 40 + min(40, (15 if any(w in text for w in ["scale", "users", "cloud", "api"]) else 0) + len(project.tech_stack.split(",")) * 5),
    }
    scores = {k: round(min(100, v), 1) for k, v in scores.items()}
    total = round(sum(scores[k] * weights[k] for k in CRITERIA) / 100, 1)
    gaps = [CRITERIA[k][0] for k, v in scores.items() if v < 65]
    feedback = ("Strongest next step: add specific evidence, metrics, or a working demo. Focus on " + ", ".join(gaps[:2]) + ".") if gaps else "Well-rounded submission. Validate the expected impact with users and document the implementation trade-offs."
    return total, scores, feedback

def evaluate(project, weights):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return evaluate_rules(project, weights)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        prompt = {"project": {"name": project.name, "team": project.team, "problem": project.problem, "solution": project.solution, "description": project.description, "impact": project.impact, "tech_stack": project.tech_stack}, "criteria": {k: {"label": v[0], "description": v[1], "weight_percent": weights[k]} for k, v in CRITERIA.items()}, "instructions": "Evaluate only evidence in the submission. Score each criterion 0-100, give concise constructive feedback, never invent facts. Return JSON with keys breakdown (criterion: numeric score), feedback (string)."}
        result = client.chat.completions.create(model="gpt-4o-mini", temperature=0.2, response_format={"type": "json_object"}, messages=[{"role": "system", "content": "You are a fair, consistent project evaluator. Return valid JSON."}, {"role": "user", "content": json.dumps(prompt)}])
        data = json.loads(result.choices[0].message.content)
        breakdown = {k: max(0, min(100, float(data["breakdown"][k]))) for k in CRITERIA}
        score = round(sum(breakdown[k] * weights[k] for k in CRITERIA) / 100, 1)
        return score, breakdown, str(data.get("feedback", "Evaluation complete."))[:1200]
    except Exception:
        return evaluate_rules(project, weights)
