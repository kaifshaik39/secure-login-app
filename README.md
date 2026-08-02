# Secure Login Authentication System (Flask + SQLite)

A complete username/password authentication system with:
- Password hashing (Werkzeug's `generate_password_hash` / `check_password_hash` — PBKDF2)
- Server-side sessions (Flask `session`, 30-minute timeout)
- Registration with email/password validation (strong password policy)
- Brute-force protection (account locks after 5 failed login attempts)
- Protected dashboard route (`@login_required` decorator)
- Flash messages for user feedback
- Clean, responsive HTML/CSS UI (no external frameworks required)

## Project structure
```
secure_login_app/
├── app.py                 # Flask app: routes, auth logic, DB helpers
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
├── static/
│   └── css/
│       └── style.css
└── users.db                # created automatically on first run
```

## 1. Run it locally

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) set a real secret key
export SECRET_KEY="change-this-to-a-long-random-string"   # Windows: set SECRET_KEY=...

# 4. Run the app
python app.py
```

Visit **http://127.0.0.1:5000** — the SQLite database (`users.db`) is created automatically the first time the app runs.

## 2. How the security pieces work

| Feature | Where | Notes |
|---|---|---|
| Password hashing | `generate_password_hash` / `check_password_hash` | Never store plaintext passwords |
| Session cookies | `app.config['SECRET_KEY']`, `session.permanent` | Signed, 30-min expiry |
| Input validation | `is_valid_email`, `is_strong_password` | Server-side, not just HTML `required` |
| SQL injection protection | Parameterized queries (`?` placeholders) | Never string-format SQL |
| Brute-force lockout | `failed_attempts` / `locked` columns | Locks after 5 bad attempts |
| Route protection | `login_required` decorator | Redirects unauthenticated users |

**Before production use**, also add: HTTPS (via your host or a reverse proxy), CSRF protection (e.g. `Flask-WTF`), rate limiting (e.g. `Flask-Limiter`), and a password-reset flow.

---

## 3. Step-by-step deployment

### Option A — Deploy to Render.com (free tier, easiest)

1. Push this project to a GitHub repository:
   ```bash
   cd secure_login_app
   git init
   git add .
   git commit -m "Initial commit: secure login app"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
2. Go to https://render.com → **New +** → **Web Service** → connect your GitHub repo.
3. Configure the service:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Under **Environment Variables**, add:
   - `SECRET_KEY` = a long random string
5. Click **Create Web Service**. Render builds and deploys automatically; you'll get a live URL like `https://your-app.onrender.com`.
6. Every future `git push` to `main` auto-redeploys.

> Note: Render's free tier disk is ephemeral — for a persistent database in production, switch to Render's free PostgreSQL add-on rather than local SQLite (see Option D below for the code change).

### Option B — Deploy to PythonAnywhere (good for SQLite, free tier)

1. Create a free account at https://www.pythonanywhere.com.
2. Open a **Bash console** and upload/clone your project:
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   pip install --user -r requirements.txt
   ```
3. Go to the **Web** tab → **Add a new web app** → choose **Flask** → select your Python version.
4. Set the **source code** path to your project folder and edit the generated **WSGI file** so it imports your app:
   ```python
   import sys
   path = '/home/<your-username>/<your-repo>'
   if path not in sys.path:
       sys.path.append(path)
   from app import app as application
   ```
5. Set `SECRET_KEY` as an environment variable in the **Web** tab (or hardcode temporarily for testing).
6. Click **Reload** on the Web tab. Your app is live at `https://<your-username>.pythonanywhere.com`.

### Option C — Deploy with Docker (portable, works on any cloud VM)

1. Add a `Dockerfile` to the project root:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   ENV SECRET_KEY=change-this-in-production
   EXPOSE 8000
   CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
   ```
2. Build and run locally to verify:
   ```bash
   docker build -t secure-login-app .
   docker run -p 8000:8000 -e SECRET_KEY="your-secret" secure-login-app
   ```
3. Push the image to a registry (Docker Hub, GitHub Container Registry, AWS ECR, etc.) and deploy it to any container host: AWS ECS/Fargate, Google Cloud Run, Azure App Service, DigitalOcean App Platform, or a plain VPS with Docker installed.

### Option D — Move from SQLite to PostgreSQL for production

SQLite is fine for demos, but on most cloud hosts the filesystem is ephemeral (data resets on redeploy). For production:

1. Add to `requirements.txt`: `psycopg2-binary`
2. Provision a managed PostgreSQL database (Render, Railway, Supabase, AWS RDS, etc.) and copy its connection URL.
3. Replace the `sqlite3` calls in `app.py` with `psycopg2` (or migrate to `Flask-SQLAlchemy` for a database-agnostic ORM) and set the connection string from an environment variable, e.g. `DATABASE_URL`.
4. Update the table-creation SQL to PostgreSQL syntax (e.g. `SERIAL PRIMARY KEY` instead of `INTEGER PRIMARY KEY AUTOINCREMENT`).

### Quick checklist before going live
- [ ] Set a strong, random `SECRET_KEY` via environment variable (never commit it)
- [ ] Use HTTPS (most platforms above provide this automatically)
- [ ] Switch `debug=True` off in production (Gunicorn/production servers already don't use the Flask dev server)
- [ ] Move from SQLite to a managed database if your host has an ephemeral filesystem
- [ ] Add CSRF protection and rate limiting before accepting real users
