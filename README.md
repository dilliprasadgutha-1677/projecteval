# ProjectEval

An AI-assisted bulk project evaluator for cohorts, hackathons, and review panels. Import up to **500 projects per CSV**, adjust a five-part weighted rubric, score every submission, review criterion scores and feedback, then export results.

## Stack
- Frontend: Next.js 14 on Vercel
- API: FastAPI on Render
- Database recommendation: **Supabase PostgreSQL** for a managed relational database with SQL editor, backups, and connection pooling. It is a strong fit for structured project submissions and can also be used with other PostgreSQL providers.
- AI: OpenAI `gpt-4o-mini` when `OPENAI_API_KEY` is set. With no key, a rule-based evidence heuristic keeps the app usable. Human reviewers should review scores before consequential decisions.

If any OpenAI request fails during a batch, all partial AI scores are discarded and every project in that batch is rescored using the same deterministic backup rubric. The selected method is shown for each evaluated project and in the batch result, so one batch never mixes scoring engines.

Rubric criteria are innovation, feasibility, impact, execution, and scalability. Default weights: 20%, 20%, 25%, 20%, and 15%. The backend creates its table at startup.

The deployed reviewer dashboard requires verified Supabase email or SMS OTP login. For local testing only, an explicit development flag can skip login when the browser and API are both accessed through localhost. The local bypass is disabled by default and must remain disabled on Render and Vercel.

Organizers can copy a participant submission link from the dashboard. Participants submit project details, a **public GitHub repository URL**, and an optional demo URL without creating an account; their submissions appear in the organizer's workspace. The GitHub reviewer checks repository metadata, README, languages, file structure, manifests, test paths, and a small sample of source files. It never runs participant code. Review the demo link to see the project running. Private repositories are not accepted by this submission flow.

When OpenAI scoring is enabled, submitted project details and sampled public repository files are sent to OpenAI for evaluation. Do not submit secrets or private information.

## Local setup
Requirements: Node.js 20+, Python 3.11+, PostgreSQL 15+ (or a Supabase project).

### Create a PostgreSQL database
In `psql` as a database administrator:

```sql
CREATE USER projecteval WITH PASSWORD 'change-this-password';
CREATE DATABASE projecteval OWNER projecteval;
GRANT ALL PRIVILEGES ON DATABASE projecteval TO projecteval;
```

For Supabase, create a project, open **Connect**, and copy its Session Pooler URI; replace the password and URL-encode special characters. A dedicated SQL user can be granted:

```sql
CREATE USER projecteval WITH PASSWORD 'change-this-password';
GRANT CONNECT ON DATABASE postgres TO projecteval;
GRANT USAGE, CREATE ON SCHEMA public TO projecteval;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO projecteval;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO projecteval;
```

Tables are automatically created by the API. Inspect data with:

```sql
\dt
SELECT id, name, team, score, status FROM projects ORDER BY id DESC;
```

### Start the API (PowerShell)

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set DATABASE_URL; optionally set OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Local `DATABASE_URL`: `postgresql+psycopg://projecteval:password@localhost:5432/projecteval`. SQLite is used if no URL is configured.

### Start the frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:3000. API docs: http://localhost:8000/docs. CSV headers: `name` (or `project_name`), `team`, `description`, `problem`, `solution`, `impact`, `tech_stack`. Maximum 500 project rows per upload.

## Local-only login bypass

To open the dashboard directly on your own computer, set `ALLOW_LOCAL_DEMO_AUTH=true` in `backend/.env` and `NEXT_PUBLIC_LOCAL_DEMO_MODE=true` in `frontend/.env.local`, then restart both servers. The bypass works only when the browser uses `localhost` or `127.0.0.1` and the API receives the request from localhost. Do not enable either flag in Render or Vercel. Deployment continues to require OTP login.

Use a managed PostgreSQL database such as Supabase to persist submissions across deployments. The reviewer dashboard still scopes project data to the authenticated organizer.

## Configure verified email and phone OTP

1. In Supabase **Authentication → Sign In / Providers**, enable Email and Phone.
2. Set the Supabase project URL and **publishable/anon key** in both frontend and backend environment variables. Never put a `service_role` key in the frontend.
3. Configure an SMS provider under Supabase phone authentication (for example Twilio), with your provider credentials; use international format such as `+14155550123`.
4. Set a GitHub fine-grained token with read-only access to public repository contents as `GITHUB_TOKEN` on Render.

Email OTP templates can be customized after setting up custom SMTP. The local development bypass avoids OTP only on localhost; it does not change the deployed login flow.

## Deploy to GitHub, Render, Vercel

### Push to GitHub
Create an empty GitHub repository, then run at the repository root:

```bash
git init
git add .
git commit -m "Build ProjectEval bulk project evaluator"
git branch -M main
git remote add origin https://github.com/dilliprasadgutha-1677/projecteval.git
git push -u origin main
```

Or, after `gh auth login`, run `gh repo create projecteval --source . --private --push`. Keep `.env` and credentials out of Git.

### Supabase
Create a PostgreSQL project and copy its **Session pooler** connection string from **Connect**. Keep its database password private. The API normalizes `postgresql://` URLs and creates the `projects` table at startup.

### Render API
Create a **Blueprint** in Render and connect the GitHub repo; choose `backend/render.yaml` (or create a Python web service with root `backend`). Set:

- `DATABASE_URL`: Supabase pooler URI.
- `OPENAI_API_KEY`: optional; omit for fallback scoring.
- `FRONTEND_ORIGIN`: your Vercel URL, e.g. `https://projecteval.vercel.app`.
- `SUPABASE_URL`: your Supabase project URL.
- `SUPABASE_ANON_KEY`: the Supabase publishable/anon key used to validate organizer sessions.
- `ALLOW_LOCAL_DEMO_AUTH=false`: keep the local-only bypass disabled on Render.
- `GITHUB_TOKEN`: a server-side GitHub token with read-only access to public repository contents; never expose it in Vercel.

Deploy and confirm `https://YOUR-API.onrender.com/health` returns `{"ok":true}`. Free instances can sleep while idle; for consistently fast batches, use an always-on service.

### Vercel frontend
Import the repository in Vercel. Set **Root Directory** to `frontend`, framework to Next.js, and add:

- `NEXT_PUBLIC_API_URL=https://YOUR-API.onrender.com` (no trailing slash)
- `NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY`
- `NEXT_PUBLIC_LOCAL_DEMO_MODE=false`

Deploy. If using a custom frontend domain, update Render's `FRONTEND_ORIGIN` and redeploy. The CSV upload sends the file directly to your API.

