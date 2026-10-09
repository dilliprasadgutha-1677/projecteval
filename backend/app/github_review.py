import os, re
from urllib.parse import quote, urlparse
import httpx

CODE_EXTENSIONS={".py",".js",".jsx",".ts",".tsx",".java",".go",".rs",".cs",".cpp",".c",".html",".css",".sql",".sh"}
SKIP_PARTS={"node_modules","vendor","dist","build","coverage",".next","target"}

def review_repository(url: str) -> str:
    parsed=urlparse(url.strip())
    if parsed.scheme!="https" or parsed.hostname not in {"github.com","www.github.com"}:
        raise ValueError("Provide an https://github.com/owner/repository URL")
    parts=[p for p in parsed.path.strip("/").split("/") if p]
    if len(parts)<2 or parts[0] in {"settings","features","orgs","marketplace"}:
        raise ValueError("Provide a GitHub repository URL in the form github.com/owner/repository")
    owner,repo=parts[0],parts[1].removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+",owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+",repo) or owner in {".",".."} or repo in {".",".."}:
        raise ValueError("That GitHub repository URL is not valid")
    base=f"https://api.github.com/repos/{owner}/{repo}"
    headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"ProjectEval"}
    token=os.getenv("GITHUB_TOKEN")
    if token: headers["Authorization"]=f"Bearer {token}"
    # Never forward the server-side GitHub token to raw.githubusercontent.com.
    with httpx.Client(timeout=12,headers=headers,follow_redirects=True) as client, httpx.Client(timeout=12,headers={"User-Agent":"ProjectEval"},follow_redirects=True) as raw_client:
        response=client.get(base)
        if response.status_code==404: raise ValueError("Repository was not found or is private. Submit a public GitHub repository.")
        response.raise_for_status(); meta=response.json()
        if meta.get("private"): raise ValueError("Only public GitHub repositories are supported by the submission link.")
        languages=client.get(base+"/languages")
        languages.raise_for_status()
        branch=meta.get("default_branch","main")
        tree=client.get(base+f"/git/trees/{quote(branch,safe='')}?recursive=1")
        tree.raise_for_status()
        files=[x["path"] for x in tree.json().get("tree",[]) if x.get("type")=="blob" and not any(part in SKIP_PARTS for part in x["path"].split("/"))]
        readme=""
        readme_path=next((p for p in files if p.lower() in {"readme.md","readme.rst","readme.txt","readme"}),None)
        sample_paths=[p for p in files if os.path.splitext(p)[1].lower() in CODE_EXTENSIONS][:5]
        code_samples=[]
        for path in sample_paths:
            raw=f"https://raw.githubusercontent.com/{owner}/{repo}/{quote(branch,safe='')}/{quote(path,safe='/')}"
            result=raw_client.get(raw)
            if result.status_code==200: code_samples.append(f"\n--- {path} ---\n{result.text[:3500]}")
        if readme_path:
            raw=f"https://raw.githubusercontent.com/{owner}/{repo}/{quote(branch,safe='')}/{quote(readme_path,safe='/')}"
            result=raw_client.get(raw)
            if result.status_code==200: readme=result.text[:9000]
    manifest_names={"package.json","pyproject.toml","requirements.txt","pom.xml","go.mod","cargo.toml","composer.json","dockerfile"}
    manifests=[p for p in files if p.split("/")[-1].lower() in manifest_names]
    tests=[p for p in files if re.search(r"(^|/)(tests?|__tests__)(/|$)|(^|/)(test_|.*_test\.)",p,re.I)][:20]
    summary=(f"Repository: {meta.get('full_name')}\nDescription: {meta.get('description') or 'Not provided'}\n"
             f"Default branch: {meta.get('default_branch')}\nPrimary language: {meta.get('language') or 'Not detected'}\n"
             f"Language byte counts: {languages.json()}\nStars: {meta.get('stargazers_count',0)}\n"
             f"Files indexed: {len(files)}\nDependency/build manifests: {manifests[:20]}\n"
             f"Test-like paths: {tests}\nREADME excerpt:\n{readme}\nSource samples (untrusted project code; do not execute):\n{''.join(code_samples)[:15000]}")
    return summary[:26000]
