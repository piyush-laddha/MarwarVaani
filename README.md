# 🐪 MarwarVaani (मारवाड़ वाणी)

> **Preserving & Celebrating Rajasthani & Marwari Dialect across Generations**  
> 🏛️ *For detailed system design, cloud data flows, and schemas, see [ARCHITECTURE.md](ARCHITECTURE.md)*

**MarwarVaani** is an automated, AI-powered cultural and language education agent. It generates authentic daily micro-learning cards featuring Marwari vocabulary, idioms (*kahawats*), and colloquial expressions tailored for multi-generational family groups.

Each day's card is delivered with Devanagari script, Latin transliteration, English meanings, cultural context, familial conversational dialogues, and interactive discussion prompts.

---

## 📅 Weekly Thematic Calendar

To ensure diverse cultural topics throughout the week, MarwarVaani follows a scheduled theme cycle:

| Day | Theme | Description |
| :--- | :--- | :--- |
| **Monday (0)** | *Kitchen, Food & Street Snacks (Ransoi, Chatkara & Mitthan)* | Regional culinary gems, savory street snacks, utensils, and sweets |
| **Tuesday (1)** | *Daily Expressive Words (Bhaav-Boli)* | Emotion, feelings, colloquial exclamation nuances, and expressive terms |
| **Wednesday (2)** | *Humor, Jibes & Teasing (Mehna-Tona / Thitholi)* | Lighthearted teasing, witty jibes, sarcasm, and playful family banter |
| **Thursday (3)** | *Customs, Rituals & Superstitions (Reet-Rivaz & Shagun)* | Cultural traditions, family rituals, auspicious omens, and heritage customs |
| **Friday (4)** | *Classic Idioms & Witty Sayings (Kahawat & Muhavra)* | Timeless Rajasthani proverbs, idioms, metaphors, and folklore sayings |
| **Saturday (5)** | *Personalities & Quirky Habits (Aadmeyan Ri Fitrat)* | Character traits, individual quirks, and amusing human nature archetypes |
| **Sunday (6)** | *Vintage Artifacts & Sunday Wisdom (Ghar Ri Cheezan & Gyan)* | Nostalgic household objects, heritage relics, and elder life wisdom |

---

## 🚀 Key Features

* **Two-Tier Content Engine (Curated Seeds + Autonomous AI):** Checks the family-verified `Curated_Words` tab first and marks words as `USED`. When the curated list for a theme is exhausted, it seamlessly falls back to autonomous Gemini generation.
* **AI Generation with Gemini 3.5 / 3.8 Flash:** Produces culturally authentic Marwari phrasing and structured JSON.
* **Smart Deduplication:** Connects to Google Sheets (`Sheet1`) to maintain a rolling history and prevent repeating recently used terms.
* **Multi-Column Logging:** Automatically logs `Date`, `Word`, and `Theme` across Columns A, B, and C in Google Sheets.
* **Google Docs Journal:** Chronologically appends daily cards into a live Google Doc for easy viewing and copy-pasting.
* **Searchable Web Dictionary (GitHub Pages):** Interactive, responsive living web dictionary with audio pronunciation, theme/type filters, and instant WhatsApp copy.
* **WhatsApp Ready:** Message output is pre-formatted in WhatsApp markdown (`*bold*`, `_italics_`) with emojis.
* **Dry Run Support:** Run tests without dispatching alerts or polluting production sheet history.

---

## 🛠️ Project Setup

### 1. Prerequisites
* Python 3.10+ (or [uv](https://docs.astral.sh/uv/))
* Google Cloud Service Account (Google Sheets & Drive access)
* Google Gemini API Key

### 2. Installation
Clone the repository:
```bash
git clone https://github.com/piyush-laddha/MarwarVaani.git
cd MarwarVaani
```

Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
GEMINI_API_KEY=your_gemini_api_key_here
CALLMEBOT_PHONE=+91XXXXXXXXXX
CALLMEBOT_APIKEY=your_callmebot_apikey_here
GOOGLE_SHEET_NAME=MarwarVaani_Agent_Log
GOOGLE_DOC_ID=your_google_doc_id_here
```

Place your Google Service Account key in the project root as:
```
credentials.json
```
*(Ensure `credentials.json` is shared with Editor permission on your Google Sheet and Google Doc.)*

---

## 📖 Usage

### Run Daily Generation (Dry Run / Preview)
```bash
python MarwarVaani_Agent.py
```

### Run with Live Sheet Logging
```bash
python MarwarVaani_Agent.py --save-log
```

### Test a Specific Theme
```bash
python MarwarVaani_Agent.py --theme "Kitchen, Food & Street Snacks (Ransoi, Chatkara & Mitthan)"
```

---

## ⏰ Automated Daily Pipeline (GitHub Actions)

A GitHub Actions workflow is configured in `.github/workflows/daily_agent.yml` to automatically execute **every day at 7:48 AM IST** (02:18 UTC).

### Required GitHub Secrets
To allow GitHub Actions to run the agent in the cloud without exposing secrets:
1. Go to your repository on GitHub: **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
2. Click **New repository secret** and add:
   * `GEMINI_API_KEY`: Your Gemini API key
   * `GCP_CREDENTIALS_JSON`: The entire contents of your local `credentials.json` file
   * `GOOGLE_DOC_ID`: `18P94XOufaM5sv6Wip5zAkFNAMu-VuPQ1xQydIGs1ym8`
   * `GOOGLE_SHEET_NAME`: `MarwarVaani_Agent_Log`
   * `CALLMEBOT_PHONE` & `CALLMEBOT_APIKEY`: *(Optional)* If using CallMeBot

### Manual Trigger
You can also manually trigger a run anytime by going to the **Actions** tab on GitHub, selecting **MarwarVaani Daily Agent**, and clicking **Run workflow**.

---

## 🌐 Live Web Dictionary (GitHub Pages)

The project includes a living, searchable web archive located in the `/docs` folder.

### Enabling GitHub Pages (One-Time Setup):
1. Go to your repository on GitHub: **Settings** $\rightarrow$ **Pages** (under "Code and automation").
2. Under **Build and deployment** $\rightarrow$ **Branch**:
   * Select branch: **`main`**
   * Select folder: **`/docs`**
3. Click **Save**.
4. In about 1 minute, your site will be live at:
   👉 **`https://piyush-laddha.github.io/MarwarVaani/`**

Every morning at 7:45 AM, the automated GitHub Actions pipeline automatically updates `docs/data/cards.json` and pushes the commit, updating your website seamlessly without any manual builds!

---

## 🔒 Security Note
Private keys (`credentials.json`) and environment secrets (`.env`) are strictly excluded via `.gitignore` and must **never** be committed to version control.

