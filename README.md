# ProjectEval

An AI-assisted bulk project evaluator for cohorts, hackathons, and review panels. Import up to **500 projects per CSV**, adjust a five-part weighted rubric, score every submission, review criterion scores and feedback, then export results.

## Stack
- Frontend: Next.js 14 on Vercel
- API: FastAPI on Render
- Database recommendation: **Supabase PostgreSQL** for a managed relational database with SQL editor, backups, and connection pooling. It is a strong fit for structured project submissions and can also be used with other PostgreSQL providers.
- AI: OpenAI `gpt-4o-mini` when `OPENAI_API_KEY` is set. With no key, a rule-based evidence heuristic keeps the app usable. Human reviewers should review scores before consequential decisions.

If any OpenAI request fails during a batch, all partial AI scores are discarded and every project in that batch is rescored using the same deterministic backup rubric. The selected method is shown for each evaluated project and in the batch result, so one batch never mixes scoring engines.

Rubric criteria are innovation, feasibility, impact, execution, and scalability. Default weights: 20%, 20%, 25%, 20%, and 15%. The backend creates its table at startup.

Sign-in supports verified email or SMS one-time codes through Supabase Auth. The API validates the Supabase access token on every project request and stores each project under its verified user id, so users only see their own workspace.

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

## Configure verified email and phone OTP

1. In Supabase **Authentication → Providers**, enable Email and Phone.
2. In **Authentication → Email Templates**, change the sign-in/magic-link template to include the numeric `{{ .Token }}` code. The sign-in screen verifies this code, not an email link.
3. Configure an SMS provider under Supabase phone authentication (for example Twilio), with your provider credentials. Phone OTP cannot deliver until an SMS provider is configured; use international format such as `+14155550123`.
4. Set the Supabase project URL and **publishable/anon key** in both frontend and backend environment variables below. Never put a `service_role` key in the frontend.

Supabase sends the code and verifies it through Auth. New users can register by entering an email or phone number and verifying their first code. OTP expiry and send limits are controlled by Supabase Auth.

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
- `SUPABASE_ANON_KEY`: the Supabase publishable/anon key used to validate logged-in users.

Deploy and confirm `https://YOUR-API.onrender.com/health` returns `{"ok":true}`. Free instances can sleep while idle; for consistently fast batches, use an always-on service.

### Vercel frontend
Import the repository in Vercel. Set **Root Directory** to `frontend`, framework to Next.js, and add:

- `NEXT_PUBLIC_API_URL=https://YOUR-API.onrender.com` (no trailing slash)
- `NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY`

Deploy. If using a custom frontend domain, update Render's `FRONTEND_ORIGIN` and redeploy. The CSV upload sends the file directly to your API.
