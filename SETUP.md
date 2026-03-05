# One-Time Setup Guide

Follow these 4 steps to get the LinkedIn PDF Auto-Poster running.

---

## Step 1 — Add Your PDFs

1. Open the `pdfs/` folder in this repository.
2. Copy your PDF files (cheatsheets, guides, infographics) into it.
3. **Naming tip:** Use descriptive, keyword-rich filenames — the filename becomes the post title.
   - ✅ `python_decorators_cheatsheet.pdf`
   - ✅ `sql_joins_reference_guide.pdf`
   - ❌ `document1.pdf`
4. PDFs are posted in **alphabetical order**, one per scheduled run.
5. Commit and push the PDFs to GitHub:
   ```bash
   git add pdfs/
   git commit -m "add PDFs for posting"
   git push origin main
   ```

> **Note:** If you add more PDFs later, just drop them in the `pdfs/` folder and push. The tracker remembers what's already been posted and picks up from where it left off.

---

## Step 2 — Get Your LinkedIn Credentials

You need two things from LinkedIn: an **Access Token** and your **Person URN**.

### 2A. Create a LinkedIn Developer App

1. Go to [https://www.linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
2. Click **Create App**.
3. Fill in the required fields:
   - **App name**: anything (e.g. `PDF Auto Poster`)
   - **LinkedIn Page**: associate it with your personal or company page
   - **App logo**: upload any image
4. Click **Create App**.

### 2B. Request the Required OAuth Scopes

1. Inside your app, go to the **Auth** tab.
2. Under **OAuth 2.0 Scopes**, request the following:
   - `r_liteprofile` — read your basic profile (needed to get your URN)
   - `w_member_social` — post content on your behalf
3. Save changes.

### 2C. Generate an Access Token

1. Still on the **Auth** tab, scroll down to **OAuth 2.0 tools**.
2. Click **OAuth 2.0 Token Generator** (or go to [https://www.linkedin.com/developers/tools/oauth](https://www.linkedin.com/developers/tools/oauth)).
3. Select your app.
4. Check both scopes: `r_liteprofile` and `w_member_social`.
5. Click **Request access token**.
6. Authorize the app when prompted.
7. Copy the **Access Token** shown — save it somewhere safe.

> ⚠️ LinkedIn tokens **expire after 60 days**. Set a calendar reminder to regenerate it before expiry. The pipeline will fail silently if the token is expired.

### 2D. Find Your Person URN

Your Person URN looks like `urn:li:person:AbCdEfGhIj`. To find it:

1. Open a terminal or tool like [Postman](https://www.postman.com/) or [curl](https://curl.se/).
2. Run the following request (replace `YOUR_TOKEN` with the token you just generated):

   **Using curl:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" https://api.linkedin.com/v2/me
   ```

   **Using PowerShell:**
   ```powershell
   Invoke-RestMethod -Uri "https://api.linkedin.com/v2/me" `
     -Headers @{ Authorization = "Bearer YOUR_TOKEN" }
   ```

3. The response will look like this:
   ```json
   {
     "id": "AbCdEfGhIj",
     "localizedFirstName": "Your",
     "localizedLastName": "Name"
   }
   ```
4. Your Person URN = `urn:li:person:` + the `id` value.
   - Example: `urn:li:person:AbCdEfGhIj`

---

## Step 3 — Get an LLM API Key

You need **one** of the following (not both):

### Option A — OpenAI (GPT-4o) — Recommended

1. Go to [https://platform.openai.com](https://platform.openai.com) and sign in.
2. Click your profile → **API Keys** → **Create new secret key**.
3. Give it a name (e.g. `linkedin-poster`) and click **Create**.
4. Copy the key — it starts with `sk-...`

> Pricing: GPT-4o costs roughly $0.005 per caption (very cheap).

### Option B — Google Gemini (Free Tier Available)

1. Go to [https://aistudio.google.com](https://aistudio.google.com) and sign in with your Google account.
2. Click **Get API Key** → **Create API key in new project**.
3. Copy the generated key.

> Gemini 1.5 Flash has a generous **free tier** (15 requests/minute, 1 million tokens/day).

---

## Step 4 — Add Secrets to GitHub

GitHub Actions reads credentials from **repository secrets** — they are encrypted and never exposed in logs.

### How to Add a Secret

1. Go to your repository on GitHub.
2. Click **Settings** (top menu).
3. In the left sidebar, click **Secrets and variables** → **Actions**.
4. Click **New repository secret**.
5. Enter the **Name** and **Value**, then click **Add secret**.

### Required Secrets

Add all of the following:

| Secret Name | Where to get it | Example value |
|---|---|---|
| `LINKEDIN_ACCESS_TOKEN` | Step 2C above | `AQX...long token...` |
| `LINKEDIN_PERSON_URN` | Step 2D above | `urn:li:person:AbCdEfGhIj` |
| `OPENAI_API_KEY` | Step 3A (if using OpenAI) | `sk-proj-...` |
| `GEMINI_API_KEY` | Step 3B (if using Gemini) | `AIzaSy...` |

> You only need **one** of `OPENAI_API_KEY` or `GEMINI_API_KEY`. If both are set, OpenAI will be used.

---

## You're Done!

Once all 4 steps are complete, push your changes to GitHub:

```bash
git add .
git commit -m "setup: add secrets and PDFs"
git push origin main
```

The pipeline will now run automatically:

| Time (IST) | Time (UTC) | Action |
|---|---|---|
| 9:00 AM | 3:30 AM | Posts next PDF to LinkedIn |
| 5:00 PM | 11:30 AM | Posts next PDF to LinkedIn |

### Manual Trigger

To post immediately without waiting for the schedule:
1. Go to your GitHub repo → **Actions** tab.
2. Click **LinkedIn PDF Auto-Poster** in the left sidebar.
3. Click **Run workflow** → **Run workflow**.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| `401 Unauthorized` from LinkedIn | Token expired or wrong | Regenerate token (Step 2C) and update the secret |
| `403 Forbidden` from LinkedIn | Missing scope | Re-authorize with `w_member_social` scope |
| `EnvironmentError: No LLM API key found` | Secret not added | Add `OPENAI_API_KEY` or `GEMINI_API_KEY` in GitHub Secrets |
| `No unposted PDFs found` | All PDFs are posted | Add more PDFs to the `pdfs/` folder |
| Workflow doesn't run on schedule | GitHub Actions delay | Normal — can be 5–15 min late. Use manual trigger to test. |
| Very little text extracted from PDF | PDF is image/scan-based | The caption is still generated from the filename. For better results, use text-based PDFs. |
