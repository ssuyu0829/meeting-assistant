# 本機啟動與部署 — 開會小助手

## 1. 安裝 Python 套件

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt   # 含 pytest 與 ruff；只跑服務可改裝 requirements.txt
```

Python 版本以 `.python-version`（3.11.9）為準。

## 2. 設定環境變數

```bash
cp .env.example .env
# 打開 .env，至少把 SECRET_KEY 填成任意一串隨機字串
```

`DATABASE_URL` 留空會用本地 SQLite（`backend/meeting_assistant.db`），第一次啟動自動建表。

## 3. 啟動伺服器

```bash
uvicorn main:app --reload
```

開啟 http://localhost:8000 。改程式後伺服器會自動重載。

## 4. 跑測試與 Lint

```bash
ruff check .
SECRET_KEY=test-secret python -m pytest tests -q
```

---

## 改接 Supabase（正式環境）

1. 到 https://supabase.com 建立專案
2. Project Settings → Database → Connection string，選 **Session pooler**（port 5432），複製 URI
3. 貼進 `.env` 的 `DATABASE_URL=postgresql://...`
4. 重新啟動伺服器，表格會自動建立
5. （選用）在 Supabase SQL Editor 執行 `backend/migrations/` 裡的索引

## Email 通知（Resend）

1. 到 https://resend.com 免費註冊並取得 API key
2. 在 `.env` 加 `RESEND_API_KEY=你的金鑰`
3. 加 `FROM_EMAIL=you@yourdomain.com`（測試可用 `onboarding@resend.dev`）

沒設 `RESEND_API_KEY` 時，決定開會時間仍會成功，只是略過寄信並寫一行 log。

## 部署到 Render

1. 把專案推到 GitHub
2. 到 https://render.com → New Web Service → 連結 repo（`render.yaml` 會自動帶入以下設定）
3. Build Command：`pip install -r backend/requirements.txt`
4. Start Command：`cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. 在 Render Dashboard 的 Environment 設定 `DATABASE_URL`、`SECRET_KEY`、`RESEND_API_KEY`、`FROM_EMAIL`
6. 之後每次 `git push` Render 會自動重新部署；只改環境變數時要手動按 **Manual Deploy**
