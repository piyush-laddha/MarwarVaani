# 🐪 MarwarVaani (मारवाड़ वाणी)

> **Preserving & Celebrating Rajasthani & Marwari Dialect across Generations**

**MarwarVaani** is an automated, AI-powered cultural and language education agent. It generates authentic daily micro-learning cards featuring Marwari vocabulary, idioms (*kahawats*), and colloquial expressions tailored for multi-generational family groups.

Each day's card is delivered with Devanagari script, Latin transliteration, English meanings, cultural context, familial conversational dialogues, and interactive discussion prompts.

---

## 📅 Weekly Thematic Calendar

To ensure diverse cultural topics throughout the week, MarwarVaani follows a scheduled theme cycle:

| Day | Theme | Description |
| :--- | :--- | :--- |
| **Monday (0)** | *Kitchen & Food (Ransoi / Bhojan)* | Regional culinary terms, utensils, and delicacies |
| **Tuesday (1)** | *Daily Expressive Word (Bhaav-Boli)* | Emotion, feelings, and colloquial conversational phrases |
| **Wednesday (2)** | *Humor & Banter (Mehna-Tona / Thitholi)* | Lighthearted teasing, wit, and family banter |
| **Thursday (3)** | *Heritage & Relations (Sagpan / Parampara)* | Kinship terms, customs, and ancestral traditions |
| **Friday (4)** | *Classic Idiom (Kahawat / Muhavra)* | Traditional proverbs, metaphors, and folklore sayings |
| **Saturday (5)** | *Personalities & Quirky Habits (Aadmeyan Ri Fitrat)* | Character traits, individual quirks, and human nature archetypes |
| **Sunday (6)** | *Wisdom & Life Sayings (Gyan Ri Baat)* | Philosophical reflections and timeless elder advice |

---

## 🚀 Key Features

* **AI Generation with Gemini 3.5 / 3.8 Flash:** Produces culturally authentic Marwari phrasing and structured JSON.
* **Smart Deduplication:** Connects to Google Sheets to maintain a rolling history and prevent repeating recently used terms.
* **Multi-Column Logging:** Automatically logs `Date`, `Word`, and `Theme` across Columns A, B, and C in Google Sheets.
* **Google Docs Journal:** Chronologically appends daily cards into a live Google Doc for easy viewing and copy-pasting.
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
python MarwarVaani_Agent.py --theme "Kitchen & Food (Ransoi / Bhojan)"
```

---

## 🔒 Security Note
Private keys (`credentials.json`) and environment secrets (`.env`) are strictly excluded via `.gitignore` and must **never** be committed to version control.

