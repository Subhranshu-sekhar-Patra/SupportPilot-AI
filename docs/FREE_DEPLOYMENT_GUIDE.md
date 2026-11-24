# SupportPilot AI — 100% Free Production Deployment Guide
## Vercel (Frontend) + Render (Backend) + Supabase (PostgreSQL)

This guide takes you through deploying **SupportPilot AI** to the cloud **100% free of charge**, with **zero credit card required**, using industry-standard free tiers:

| Component | Platform | Free Tier Specifications | Cost |
| :--- | :--- | :--- | :--- |
| **Database** | [Supabase](https://supabase.com) | Managed PostgreSQL 15+, 500 MB storage, pgvector support | **$0/month** (Free Forever) |
| **Backend API** | [Render](https://render.com) | 512 MB RAM, 0.1 CPU, free HTTPS (`*.onrender.com`), automatic git deploy | **$0/month** (Free Forever) |
| **Frontend UI** | [Vercel](https://vercel.com) | Unlimited deployments, global edge CDN, free HTTPS (`*.vercel.app`) | **$0/month** (Free Forever) |
| **AI Engine** | [Google AI Studio](https://aistudio.google.com) | Gemini 2.0 Flash (15 RPM, 1,500 requests/day, 1M tokens/min free) | **$0/month** (Free Forever) |

---

## 📋 Table of Contents
1. [Step 1: Set up Free PostgreSQL on Supabase](#step-1-set-up-free-postgresql-on-supabase)
2. [Step 2: Deploy Backend to Render](#step-2-deploy-backend-to-render)
3. [Step 3: Deploy Frontend to Vercel](#step-3-deploy-frontend-to-vercel)
4. [Step 4: Seed Initial Data or Create Admin Account](#step-4-seed-initial-data-or-create-admin-account)
5. [Step 5: Verify Your Live Deployment](#step-5-verify-your-live-deployment)

---

## Step 1: Set up Free PostgreSQL on Supabase

1. Visit **[https://supabase.com](https://supabase.com)** and click **Start your project** (sign in with your GitHub account).
2. Click **New Project**:
   - **Name:** `supportpilot-db`
   - **Database Password:** Enter a secure password (e.g., `MySecureDbPass2026!`) and **save it somewhere safe**.
   - **Region:** Select the region closest to you (e.g., `US East (North Virginia)` or `EU Central`).
   - **Pricing Plan:** Choose **Free Plan ($0/month)**.
3. Click **Create new project** and wait ~60 seconds for provisioning.
4. Retrieve your connection URLs:
   - In the left sidebar, click the **Settings (gear icon)** → **Database**.
   - Scroll down to the **Connection string** section.
   - Click the **URI** tab.
   - It will show a string like:
     ```
     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
   - For Supabase, the **Session Pooler** (port `5432`) is recommended for Alembic and asyncpg:
     ```
     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
     ```
   - You will use this in Step 2:
     - `DATABASE_URL`: `postgresql+asyncpg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres`
     - `DATABASE_URL_SYNC`: `postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres`

---

## Step 2: Deploy Backend to Render

1. Visit **[https://render.com](https://render.com)** and click **Get Started** (sign in with GitHub).
2. Click the **New +** button in the dashboard and select **Web Service**.
3. Under **Connect a repository**, find and select your `SupportPilot-AI` repository.
4. Fill in the service configuration:
   - **Name:** `supportpilot-api` (or any unique name you like)
   - **Region:** Choose the region closest to your Supabase DB (e.g., `Oregon (US West)` or `Frankfurt (EU)`)
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     bash start.sh
     ```
   - **Instance Type:** Select **Free** (0.1 CPU, 512 MB RAM)

5. Scroll down to **Environment Variables** and add the following keys:

   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `APP_ENV` | `production` | Enables production mode |
   | `LOG_FORMAT` | `json` | Structured production logging |
   | `SECRET_KEY` | *(generate any 32-char hex string, e.g. `openssl rand -hex 32`)* | JWT signing key |
   | `DATABASE_URL` | `postgresql+asyncpg://...` *(from Step 1)* | Async database URL |
   | `DATABASE_URL_SYNC` | `postgresql://...` *(from Step 1)* | Sync database URL for Alembic migrations |
   | `GEMINI_API_KEY` | *(your key from [Google AI Studio](https://aistudio.google.com/app/apikey))* | Gemini AI Engine |
   | `CORS_ORIGINS` | `*` | Allows connections from your Vercel domain |
   | `STORAGE_BACKEND` | `local` | Uses lightweight local container storage |
   | `CHROMA_PERSIST_DIR` | `./chroma_data` | Vector database directory |

6. Click **Create Web Service**.
7. Render will now automatically clone your code, install dependencies, run `alembic upgrade head` to create all tables in Supabase, and start Uvicorn!
8. Once deployment finishes (status shows **Live**), copy your public API URL from the top of the Render dashboard:
   ```text
   https://supportpilot-api.onrender.com
   ```
9. Test it by opening `https://supportpilot-api.onrender.com/health` in your browser. You should see:
   ```json
   {"status":"healthy","version":"1.0.0","env":"production","service":"supportpilot-backend"}
   ```

---

## Step 3: Deploy Frontend to Vercel

1. Visit **[https://vercel.com](https://vercel.com)** and sign in with GitHub.
2. Click **Add New...** → **Project**.
3. Find your `SupportPilot-AI` repository and click **Import**.
4. In the configuration window:
   - **Project Name:** `supportpilot` (or your choice)
   - **Framework Preset:** `Next.js` (automatically detected)
   - **Root Directory:** Click **Edit** and choose `frontend`.
5. Expand **Environment Variables** and add:

   | Key | Value |
   | :--- | :--- |
   | `NEXT_PUBLIC_API_URL` | `https://supportpilot-api.onrender.com` *(paste your Render backend URL from Step 2, without a trailing slash)* |

6. Click **Deploy**.
7. Vercel will build and optimize your Next.js frontend in about 60 seconds.
8. Once finished, click **Go to Dashboard** or **Visit** to see your live application URL:
   ```text
   https://supportpilot.vercel.app
   ```

---

## Step 4: Create Your Admin Account

Now that both frontend and backend are live:
1. Open your Vercel URL in your browser (`https://supportpilot.vercel.app`).
2. Click **Register** / **Sign Up**.
3. Create your company organization name and your administrator email/password.
4. Once registered, log in to access the full SupportPilot AI dashboard!

*(Optional: To elevate your user account to Super Admin, you can run the CLI script via Render's **Shell** tab):*
```bash
python -m app.scripts.create_superadmin --email "your_email@example.com" --password "YourPassword123!" --name "Platform Admin"
```

---

## Step 5: Test the Embeddable Chat Widget

SupportPilot AI provides a 1-line script that can be embedded into any website:

```html
<script 
  src="https://supportpilot-api.onrender.com/api/v1/widget/loader.js" 
  data-org-slug="your-org-slug" 
  data-primary-color="#2563eb"
  defer>
</script>
```

Replace `your-org-slug` with your organization's slug from the dashboard settings.

---

## 💡 Free Tier Tips & Best Practices
- **Render Cold Starts:** Render's free tier puts web services to sleep after 15 minutes of inactivity. When a new request arrives, it takes ~30 seconds to wake up. To keep it awake 24/7 for free, you can set up a free monitor at **[cron-job.org](https://cron-job.org)** or **[UptimeRobot](https://uptimerobot.com)** to ping `https://supportpilot-api.onrender.com/health` every 10 minutes!
- **Supabase Free Limits:** Supabase provides 500 MB of storage and 50,000 monthly active users on the free tier, which is more than enough for thousands of customer support tickets.
- **Gemini Free Quota:** Google AI Studio provides 15 requests per minute and 1,500 requests per day for Gemini 2.0 Flash completely free.
