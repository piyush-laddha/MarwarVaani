import os
import sys
import json
import urllib.parse
import datetime
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Ensure Windows terminal handles UTF-8 (Devanagari characters)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Load variables from .env
load_dotenv()

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CALLMEBOT_PHONE = os.getenv("CALLMEBOT_PHONE")
CALLMEBOT_APIKEY = os.getenv("CALLMEBOT_APIKEY")
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "MarwarVaani_Agent_Log")
GOOGLE_DOC_ID = os.getenv("GOOGLE_DOC_ID", "18P94XOufaM5sv6Wip5zAkFNAMu-VuPQ1xQydIGs1ym8")

# --- WEEKLY THEMATIC SCHEDULE ---
THEME_SCHEDULE = {
    0: "Kitchen & Food (Ransoi / Bhojan)",
    1: "Daily Expressive Word (Bhaav-Boli)",
    2: "Humor & Banter (Mehna-Tona / Thitholi)",
    3: "Heritage & Family Relations (Sagpan / Parampara)",
    4: "Classic Idiom (Kahawat / Muhavra)",
    5: "Desert Life & Nature (Maru-Dhara / Prakriti)",
    6: "Wisdom & Life Sayings (Gyan Ri Baat)"
}

# --- 1. CONNECT TO GOOGLE SHEETS & FETCH LOGS ---
def get_recent_words(sheet_name, max_history=60):
    """Fetches previously used words from Google Sheet (Column B) to avoid repetition."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Check if running in CI/CD with JSON string, otherwise load local credentials.json
        creds_json = os.getenv("GCP_CREDENTIALS_JSON")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            creds_path = os.path.join(base_dir, "credentials.json")
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)

        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        records = sheet.get_all_values()
        
        # Column B (index 1) stores headwords, row 1 is header ['Date', 'Word', 'Theme']
        words = [row[1].strip() for row in records[1:] if len(row) > 1 and row[1].strip()]
        return sheet, words[-max_history:]
    except Exception as e:
        print(f"[!] Notice: Could not access Google Sheet '{sheet_name}' ({e}). Proceeding without remote history.")
        return None, []

# --- 2. GENERATE DAILY CARD VIA GEMINI ---
def generate_marwarvaani_card(excluded_words, theme_name):
    """Generates authentic Marwari card strictly aligned with today's scheduled theme."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are an authentic Rajasthani / Marwari cultural linguist and family educator for Project 'MarwarVaani'.
    Today's Theme: {theme_name}

    Target Audience: Multi-generational family WhatsApp group (diaspora youth living outside Rajasthan, along with parents and grandparents).

    CRITICAL RULES:
    1. Do NOT repeat any of these recently covered words/idioms:
       {', '.join(excluded_words) if excluded_words else 'None'}
    2. The word or idiom MUST strictly match today's theme: "{theme_name}".

    Select an authentic, culturally rich Marwari word, idiom (kahawat), or phrase matching today's theme.

    Output STRICT JSON matching these exact keys:
    - "word_devanagari": Word or idiom in Devanagari script (e.g. ओळभो, लापसी, मेहणो)
    - "word_transliteration": Clean Latin phonetic spelling (e.g. Olbho, Laapsi, Mehno)
    - "theme": Clean, short theme label (e.g. "{theme_name}")
    - "item_type": "Word", "Idiom", or "Phrase"
    - "meaning": Crisp English meaning (under 15 words)
    - "cultural_vibe": 1-2 lines explaining the cultural sentiment, regional nuance, or origin
    - "dialogue_marwari": A realistic home dialogue spoken by elders/family
    - "dialogue_english": Natural English translation of the dialogue
    - "family_prompt": A fun, engaging question to prompt replies in the family chat
    """

    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
    last_err = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            last_err = e
            continue
    raise last_err

# --- 3. FORMAT FOR WHATSAPP / GOOGLE DOC ---
def format_whatsapp_message(data):
    """Formats output using standard WhatsApp Markdown (asterisks for bold, underscores for italic)."""
    theme = data.get("theme", "")
    theme_line = f"🎯 *Today's Theme:* {theme}\n\n" if theme else "\n"
    
    return (
        f"🐪 *MarwarVaani | Daily Marwari*\n"
        f"{theme_line}"
        f"📖 *{data['word_devanagari']}* ({data['word_transliteration']})\n"
        f"🏷️ *Type:* {data['item_type']}\n\n"
        f"🔹 *Meaning:* {data['meaning']}\n"
        f"🔹 *Cultural Vibe:* {data['cultural_vibe']}\n\n"
        f"🗣️ *Ghar Ri Boli (In Conversation):*\n"
        f"\"{data['dialogue_marwari']}\"\n"
        f"↳ _{data['dialogue_english']}_\n\n"
        f"💬 *Family Question:* {data['family_prompt']}\n\n"
        f"—\n"
        f"✨ _Keep our roots alive with MarwarVaani_"
    )

# --- 4. APPEND TO GOOGLE DOC ---
def append_to_google_doc(doc_id, message_text):
    """
    Appends the formatted card to the bottom of the Google Doc with its date.
    Preserves all previous days' entries in chronological order (journal format).
    """
    try:
        scope = ["https://www.googleapis.com/auth/drive"]
        
        creds_json = os.getenv("GCP_CREDENTIALS_JSON")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            creds_path = os.path.join(base_dir, "credentials.json")
            creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scope)
            
        creds.refresh(Request())
        headers = {"Authorization": f"Bearer {creds.token}"}
        
        existing_text = ""
        export_url = f"https://www.googleapis.com/drive/v3/files/{doc_id}/export?mimeType=text/plain"
        res = requests.get(export_url, headers=headers, timeout=20)
        if res.status_code == 200:
            raw_text = res.content.decode("utf-8-sig", errors="replace").strip()
            # Filter out any initial placeholder if present
            if raw_text and not raw_text.startswith("Test Message from MarwarVaani Agent"):
                existing_text = raw_text

        today_str = datetime.date.today().strftime("%Y-%m-%d (%A)")
        divider = "=" * 54
        entry_block = f"📅 Date: {today_str}\n{divider}\n{message_text}\n{divider}"
        
        if existing_text:
            combined_content = f"{existing_text}\n\n\n{entry_block}\n"
        else:
            combined_content = f"🐪 MARWARVAANI - DAILY MESSAGE JOURNAL\n{divider}\n\n{entry_block}\n"
            
        upload_url = f"https://www.googleapis.com/upload/drive/v3/files/{doc_id}?uploadType=media"
        upload_headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "text/plain; charset=utf-8"
        }
        
        upload_res = requests.patch(
            upload_url, 
            headers=upload_headers, 
            data=combined_content.encode("utf-8"), 
            timeout=20
        )
        
        if upload_res.status_code == 200:
            print(f"[+] Successfully appended to Google Doc 'MarwarVaani_Msg'!")
            print(f"    👉 View journal: https://docs.google.com/document/d/{doc_id}/edit")
            return True
        else:
            print(f"[-] Google Doc publish failed: HTTP {upload_res.status_code} - {upload_res.text}")
            return False
    except Exception as e:
        print(f"[-] Error appending to Google Doc: {e}")
        return False

# --- 5. SEND VIA CALLMEBOT ---
def send_whatsapp_alert(phone, message_text, apikey):
    """Sends preview to personal WhatsApp via CallMeBot."""
    if not phone or not apikey:
        print("[!] Notice: CallMeBot credentials missing. WhatsApp dispatch skipped.")
        return False

    encoded_text = urllib.parse.quote(message_text)
    endpoint = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_text}&apikey={apikey}"
    
    try:
        response = requests.get(endpoint, timeout=20)
        if response.status_code == 200:
            print("[+] MarwarVaani update successfully sent to personal WhatsApp!")
            return True
        else:
            print(f"[-] Dispatch failed: HTTP {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[-] Dispatch error: {e}")
        return False

# --- 6. LOG ENTRY TO SHEETS (Columns: Date, Word, Theme) ---
def log_entry(sheet, word, theme):
    """Appends Date (Col A), Word (Col B), and Theme (Col C) to Google Sheet."""
    if sheet:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        sheet.append_row([today_str, word, theme])
        print(f"[+] Saved '{word}' | Theme: '{theme}' across columns A, B, C in {SHEET_NAME}.")

# --- MAIN EXECUTION ---
def main():
    has_callmebot = bool(
        CALLMEBOT_PHONE 
        and CALLMEBOT_APIKEY 
        and CALLMEBOT_PHONE.strip() 
        and CALLMEBOT_APIKEY.strip()
        and CALLMEBOT_APIKEY.strip() != "your_callmebot_apikey_here"
    )
    
    dry_run = ("--dry-run" in sys.argv) or not has_callmebot

    # Determine theme based on current weekday
    weekday = datetime.date.today().weekday()
    current_theme = THEME_SCHEDULE.get(weekday, "Daily Expressive Word (Bhaav-Boli)")

    # Allow overriding theme for manual testing: e.g. python MarwarVaani_Agent.py --theme "Kitchen & Food"
    for idx, arg in enumerate(sys.argv):
        if arg == "--theme" and idx + 1 < len(sys.argv):
            current_theme = sys.argv[idx + 1]

    print("====================================")
    print("      PROJECT MARWARVAANI AGENT     ")
    if dry_run:
        print("          [MODE: DRY RUN]           ")
    print("====================================\n")
    
    print(f"[*] Today's Day: {datetime.date.today().strftime('%A')} (Weekday {weekday})")
    print(f"[*] Today's Theme: {current_theme}\n")

    if dry_run and not has_callmebot:
        print("[*] Notice: CallMeBot credentials not configured. WhatsApp dispatch skipped.\n")
    elif dry_run:
        print("[*] Notice: Dry Run flag detected. WhatsApp dispatch skipped.\n")

    print("[1/5] Checking history in Google Sheets...")
    sheet, recent_history = get_recent_words(SHEET_NAME)
    print(f"[*] Live Google Sheet '{SHEET_NAME}' connected. Found {len(recent_history)} previously logged words.")
    
    print(f"\n[2/5] Generating MarwarVaani card via Gemini for theme '{current_theme}'...")
    card_data = generate_marwarvaani_card(recent_history, current_theme)
    
    formatted_msg = format_whatsapp_message(card_data)
    print("\n" + "=" * 20 + " CARD PREVIEW " + "=" * 20)
    print(formatted_msg)
    print("=" * 54 + "\n")
    
    # 3. Append to Google Doc
    print("[3/5] Appending to Google Doc 'MarwarVaani_Msg'...")
    if GOOGLE_DOC_ID:
        append_to_google_doc(GOOGLE_DOC_ID, formatted_msg)
    else:
        print("[!] GOOGLE_DOC_ID not configured in .env.")

    # 4. WhatsApp Dispatch
    print("\n[4/5] WhatsApp Dispatch:")
    if dry_run:
        print("[*] WhatsApp dispatch skipped (CallMeBot not configured / dry run active).")
    else:
        send_whatsapp_alert(CALLMEBOT_PHONE, formatted_msg, CALLMEBOT_APIKEY)
    
    # 5. Google Sheets Logging
    print("\n[5/5] Google Sheets Logging (Columns: Date, Word, Theme):")
    if dry_run and "--save-log" not in sys.argv:
        print("[*] DRY RUN: Google Sheet logging skipped (keeps production history clean).")
        print("    (Pass --save-log if you want to write to Google Sheets during dry run)")
    else:
        word_entry = card_data.get("word_devanagari", "")
        theme_entry = card_data.get("theme", current_theme)
        log_entry(sheet, word_entry, theme_entry)
    
    print("\nRun complete.")

if __name__ == "__main__":
    main()
