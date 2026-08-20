# Deployment Plan: AI-Powered Myntra Wishlist Discovery Engine

---

## 1. Overview & Free-Tier Architecture

This deployment plan provides an exact, step-by-step guide to deploy the entire Discovery Engine to free-tier cloud infrastructure.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             FREE-TIER CLOUD TOPOLOGY                             │
├─────────────────────────┬──────────────────────────┬─────────────────────────────┤
│ Service                 │ Free-Tier Resource       │ Responsibility              │
├─────────────────────────┼──────────────────────────┼─────────────────────────────┤
│ 1. Supabase             │ Free PostgreSQL Project  │ 24/7 Database & Data Lake   │
│ 2. GitHub Actions       │ Free Public Runner Mins  │ Scheduled Daily Ingestion   │
│ 3. Vercel               │ Free Hobby Plan          │ Next.js Web App & API Hosting│
│ 4. Apify & Groq         │ Free Monthly Quotas      │ Reddit/App Scrapers & AI LLM│
└─────────────────────────┴──────────────────────────┴─────────────────────────────┘
```

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Push Codebase to GitHub
Open your terminal in the root project folder (`c:\Users\shrut\Downloads\M`) and run:

```bash
# 1. Initialize Git repository
git init

# 2. Stage all project files (secrets in .env are protected by .gitignore)
git add .

# 3. Create initial commit
git commit -m "feat: complete myntra wishlist discovery engine"

# 4. Set main branch
git branch -M main

# 5. Link to your GitHub repo
git remote add origin https://github.com/shruti7jain/Myntra.git

# 6. Push code to GitHub
git push -u origin main
```

---

### Step 2: Configure GitHub Repository Secrets (For Daily Automation)

To allow GitHub Actions to run your scrapers automatically every day without hardcoding credentials in the code:

1. Open your repository on GitHub: `https://github.com/shruti7jain/Myntra`.
2. Go to **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
3. Click **New repository secret** and add the following 4 secrets (values from your `.env` file):

| Secret Name | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase Project URL |
| `SUPABASE_SERVICE_KEY` | Your Supabase Service Role Key |
| `APIFY_API_TOKEN` | Your Apify API Token |
| `GROQ_API_KEY` | Your Groq Cloud API Key |

---

### Step 3: Deploy Web Dashboard to Vercel

1. Open **[vercel.com/new](https://vercel.com/new)** and log in with GitHub.
2. Select your `Myntra` repository and click **Import**.
3. In the project configuration:
   - **Framework Preset**: Next.js (detected automatically).
   - **Root Directory**: Click *Edit* and select **`frontend`**.
4. Expand **Environment Variables** and add the following:
   - `NEXT_PUBLIC_SUPABASE_URL`: `<YOUR_SUPABASE_URL>`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: `<YOUR_SUPABASE_ANON_KEY>`
   - `SUPABASE_SERVICE_KEY`: `<YOUR_SUPABASE_SERVICE_KEY>`
   - `GROQ_API_KEY`: `<YOUR_GROQ_API_KEY>`
5. Click **Deploy**. Vercel will build and launch your public URL within ~60 seconds!

---

## 3. Automated Operation & Daily Keep-Alive

* **Schedule**: GitHub Actions automatically triggers at **03:00 UTC (08:30 AM IST)** daily.
* **Pipeline Sequence**:
  1. Pulls newest reviews and discussions across Google Play Store, Reddit, Apple App Store, and YouTube.
  2. Deduplicates against `raw_feedback` in Supabase.
  3. Tags newly added feedback and recalculates the `insights` table.
  4. The Vercel web app automatically displays the fresh numbers on next visit.
* **Zero Ongoing Maintenance**: Stays live and self-updating with $0 operational cost.
