# How to Run — 開會小助手 Web Version

## 1. Install Python dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY to any random string
```

## 3. Start the server

```bash
uvicorn main:app --reload
```

Open http://localhost:8000 in your browser.

---

## Switching to Supabase (production)

1. Go to https://supabase.com → create a project
2. In Project Settings → Database → Connection string → copy the URI
3. Paste it into `.env` as `DATABASE_URL=postgresql://...`
4. Restart the server — tables will be created automatically

## Email notifications (Resend)

1. Go to https://resend.com → sign up free → get an API key
2. Add `RESEND_API_KEY=your_key` to `.env`
3. Add `FROM_EMAIL=you@yourdomain.com` (or use `onboarding@resend.dev` for testing)

## Deploy to Render

1. Push this folder to a GitHub repo
2. Go to https://render.com → New Web Service → connect repo
3. Set Build Command: `pip install -r backend/requirements.txt`
4. Set Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (DATABASE_URL, SECRET_KEY, RESEND_API_KEY) in Render dashboard
