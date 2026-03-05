# LinkedIn PDF Auto-Poster

Automatically posts PDF cheatsheets/resources to LinkedIn with AI-generated captions — twice daily (9 AM IST & 5 PM IST) via GitHub Actions.

---

## How It Works

```
pdfs/ directory
     │
     ▼
[extract_pdf.py]  ── Extracts text from next unposted PDF
     │
     ▼
[generate_caption.py] ── Sends content to GPT-4o / Gemini → viral LinkedIn caption
     │
     ▼
[post_to_linkedin.py] ── Uploads PDF + caption to LinkedIn API
     │
     ▼
[tracker.py] ── Marks PDF as posted in posted_tracker.json
     │
     ▼
GitHub Actions ── Commits tracker back to repo
```

---

## Setup (One-Time)

### 1. Add your PDFs
Drop your PDF files into the `pdfs/` folder. They are posted in **alphabetical order**, one per schedule run.

### 2. Get LinkedIn credentials

#### A. LinkedIn Access Token
1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/) → Create an App
2. Request the **`w_member_social`** and **`r_liteprofile`** OAuth 2.0 scopes
3. Generate a token using the OAuth 2.0 Authorization Code Flow
   - Or use [LinkedIn's OAuth 2.0 Token Generator](https://www.linkedin.com/developers/tools/oauth) in the Developer Portal
4. Copy the **Access Token** (valid for 60 days — re-generate when expired)

#### B. LinkedIn Person URN
Call this endpoint with your token to get your URN:
```
GET https://api.linkedin.com/v2/me
Authorization: Bearer YOUR_TOKEN
```
The `id` field in the response is your person ID. Your URN = `urn:li:person:<id>`

### 3. Get an LLM API Key (choose one)
- **OpenAI**: [platform.openai.com](https://platform.openai.com) → API Keys → Create new
- **Google Gemini** (free tier available): [aistudio.google.com](https://aistudio.google.com) → Get API Key

### 4. Add GitHub Secrets
Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `LINKEDIN_ACCESS_TOKEN` | Your LinkedIn OAuth access token |
| `LINKEDIN_PERSON_URN` | e.g. `urn:li:person:AbCdEfGhIj` |
| `OPENAI_API_KEY` | Your OpenAI API key (if using GPT) |
| `GEMINI_API_KEY` | Your Gemini API key (if using Gemini) |

> You only need **one** of `OPENAI_API_KEY` or `GEMINI_API_KEY`. OpenAI takes priority if both are set.

### 5. Push to GitHub
```bash
git add .
git commit -m "Initial setup"
git push origin main
```

The workflow runs automatically at **3:30 UTC (9 AM IST)** and **11:30 UTC (5 PM IST)**.

---

## Manual Trigger
Go to **Actions → LinkedIn PDF Auto-Poster → Run workflow** to trigger a post immediately.

---

## File Structure

```
linkcheat/
├── pdfs/                    ← Put your PDFs here
├── .github/
│   └── workflows/
│       └── post_linkedin.yml
├── extract_pdf.py           ← PDF text extraction
├── generate_caption.py      ← LLM caption generation
├── post_to_linkedin.py      ← LinkedIn API posting
├── tracker.py               ← Tracks posted PDFs
├── main.py                  ← Pipeline entrypoint
├── posted_tracker.json      ← Auto-updated by pipeline
└── requirements.txt
```

---

## Notes & Tips

- **Image-only PDFs** (scanned documents without selectable text): The extractor will warn you but the LLM will still generate a caption based on the filename/title.
- **Token expiry**: LinkedIn tokens expire after 60 days. Set a calendar reminder to refresh yours.
- **All PDFs posted?**: The pipeline exits gracefully with a message. Just add more PDFs to `/pdfs`.
- **Schedule**: GitHub Actions schedules can run a few minutes late under load — this is normal.
- **Caption quality**: The prompt is tuned for cheatsheets and informative resources. For best results, name your PDFs descriptively (e.g., `python_decorators_cheatsheet.pdf`).
