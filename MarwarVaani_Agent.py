import os
import sys
import re
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
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME") or "MarwarVaani_Agent_Log"
GOOGLE_DOC_ID = os.getenv("GOOGLE_DOC_ID") or "18P94XOufaM5sv6Wip5zAkFNAMu-VuPQ1xQydIGs1ym8"

# --- WEEKLY THEMATIC SCHEDULE (theme_key for Curated_Words, theme_label for display) ---
THEME_SCHEDULE = {
    0: ("Kitchen & Food", "Kitchen, Food & Street Snacks (Ransoi, Chatkara & Mitthan)"),
    1: ("Expressive Words", "Daily Expressive Words (Bhaav-Boli)"),
    2: ("Humor & Banter", "Humor, Jibes & Teasing (Mehna-Tona / Thitholi)"),
    3: ("Customs & Rituals", "Customs, Rituals & Superstitions (Reet-Rivaz & Shagun)"),
    4: ("Classic Idioms", "Classic Idioms & Witty Sayings (Kahawat & Muhavra)"),
    5: ("Personalities & Habits", "Personalities & Quirky Habits (Aadmeyan Ri Fitrat)"),
    6: ("Vintage Artifacts", "Vintage Artifacts & Sunday Wisdom (Ghar Ri Cheezan & Gyan)")
}

# --- 1. GOOGLE SHEETS CLIENT ---
def get_sheets_client():
    """Initializes and returns an authorized gspread client."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json = os.getenv("GCP_CREDENTIALS_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        creds_path = os.path.join(base_dir, "credentials.json")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)

# --- 2. FETCH FROM CURATED SEED LIST ---
def fetch_curated_or_fallback(client, theme_key):
    """
    Checks the 'Curated_Words' tab for an unused word matching today's theme.
    Returns (worksheet, row_index, word, transliteration) or (None, None, None, None)
    if no unused curated word is available.
    """
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet("Curated_Words")
        rows = worksheet.get_all_values()
        
        # Row 1 is header: ['Theme', 'Word', 'Transliteration', 'Status']
        for idx, row in enumerate(rows[1:], start=2):
            if len(row) >= 2 and row[0].strip().lower() == theme_key.lower():
                status = row[3].strip().upper() if len(row) >= 4 else ""
                if status != "USED":
                    word = row[1].strip()
                    translit = row[2].strip() if len(row) >= 3 else ""
                    return (worksheet, idx, word, translit)
        return (None, None, None, None)
    except Exception as e:
        print(f"[!] Notice: Curated tab check skipped: {e}")
        return (None, None, None, None)

# --- 3. FETCH RECENT LOG HISTORY FOR DEDUPLICATION ---
def get_recent_history(client, max_history=60):
    """Fetches previously used words from Sheet1 (Column B) to prevent repeats."""
    try:
        spreadsheet = client.open(SHEET_NAME)
        sheet1 = spreadsheet.sheet1
        records = sheet1.get_all_values()
        words = [row[1].strip() for row in records[1:] if len(row) > 1 and row[1].strip()]
        return sheet1, words[-max_history:]
    except Exception as e:
        print(f"[!] Warning reading log sheet: {e}")
        return None, []

# --- 4. GENERATE CARD VIA GEMINI (CURATED OR AUTONOMOUS) ---
def generate_marwarvaani_card(theme_label, specific_word=None, specific_translit=None, excluded_words=None):
    """
    Generates an authentic Marwari card.
    - If specific_word is provided: elaborates on that curated word.
    - Otherwise: autonomously discovers an authentic word matching theme_label, avoiding excluded_words.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    if specific_word:
        prompt = f"""
        You are an authentic Rajasthani / Marwari cultural linguist and family educator for Project 'MarwarVaani'.
        Task: Create a daily micro-learning card for this SPECIFIC, HUMAN-CURATED Marwari term:
        Word: {specific_word} ({specific_translit})
        Theme: {theme_label}

        Target Audience: Multi-generational family WhatsApp group (diaspora youth living outside Rajasthan, along with parents and grandparents).
        Provide authentic, culturally rich, and engaging familial context.
        """
    else:
        prompt = f"""
        You are an authentic Rajasthani / Marwari cultural linguist and family educator for Project 'MarwarVaani'.
        Theme: {theme_label}
        Target Audience: Multi-generational family WhatsApp group (diaspora youth living outside Rajasthan, along with parents and grandparents).

        CRITICAL RULES:
        1. Do NOT repeat any of these recently used words:
           {', '.join(excluded_words) if excluded_words else 'None'}
        2. The word or idiom MUST strictly match today's theme: "{theme_label}".

        Select an authentic, culturally recognized Marwari word, idiom (kahawat), or phrase from traditional lexicography.
        """

    prompt += f"""
    Output STRICT JSON matching these exact keys:
    - "word_devanagari": Word or idiom in Devanagari script
    - "word_transliteration": Clean Latin phonetic spelling (clean, without notes)
    - "theme": Clean short theme title (e.g. "{theme_label}")
    - "item_type": "Word", "Idiom", or "Phrase"
    - "meaning": Crisp English meaning (under 15 words)
    - "cultural_vibe": 1-2 lines explaining the cultural sentiment, regional lore, or origin
    - "dialogue_marwari": A realistic home dialogue spoken by elders/family
    - "dialogue_english": Natural English translation of the dialogue
    - "family_prompt": A fun, engaging question to prompt replies in the chat
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

# --- 5. FORMAT FOR WHATSAPP ---
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

# --- 6. APPEND TO GOOGLE DOC JOURNAL ---
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
            raw_text = res.content.decode("utf-8-sig", errors="replace")
            # Normalize CRLF/CR to LF and collapse runs of 3+ newlines to max 2 (\n\n)
            raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
            raw_text = re.sub(r"\n{3,}", "\n\n", raw_text).strip()
            if raw_text and not raw_text.startswith("Test Message from MarwarVaani Agent"):
                existing_text = raw_text

        today_str = datetime.date.today().strftime("%Y-%m-%d (%A)")
        divider = "=" * 54
        clean_message = re.sub(r"\n{3,}", "\n\n", message_text.replace("\r\n", "\n")).strip()
        entry_block = f"📅 Date: {today_str}\n{divider}\n{clean_message}\n{divider}"
        
        if existing_text:
            combined_content = f"{existing_text}\n\n\n{entry_block}\n"
        else:
            combined_content = f"🐪 MARWARVAANI | DAILY MARWARI JOURNAL\n{divider}\n\n{entry_block}\n"
            
        # Ensure the whole combined payload has no redundant empty lines
        combined_content = re.sub(r"\n{3,}", "\n\n", combined_content).strip() + "\n"
            
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

# --- 7. SAVE TO WEB ARCHIVE (GitHub Pages) ---
def save_to_web_archive(card_data):
    """Saves the generated card into docs/data/cards.json for the GitHub Pages web dictionary."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "docs", "data")
        os.makedirs(data_dir, exist_ok=True)
        cards_file = os.path.join(data_dir, "cards.json")
        
        cards = []
        if os.path.exists(cards_file):
            try:
                with open(cards_file, "r", encoding="utf-8") as f:
                    cards = json.load(f)
            except Exception:
                cards = []

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        card_copy = dict(card_data)
        card_copy["date"] = today_str

        exists = any(
            c.get("word_devanagari") == card_copy.get("word_devanagari") 
            and c.get("date") == today_str 
            for c in cards
        )
        if not exists:
            cards.insert(0, card_copy)  # Newest first
            with open(cards_file, "w", encoding="utf-8") as f:
                json.dump(cards, f, ensure_ascii=False, indent=2)
            print(f"[+] Saved '{card_copy.get('word_devanagari')}' to Web Archive (docs/data/cards.json).")
        else:
            print(f"[*] Card '{card_copy.get('word_devanagari')}' already exists in Web Archive.")
        return True
    except Exception as e:
        print(f"[!] Warning: Could not update Web Archive: {e}")
        return False

# --- 8. SEND VIA CALLMEBOT ---
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

# --- 9. LOG ENTRY TO SHEET1 ---
def log_entry(sheet, word, theme):
    """Appends Date (Col A), Word (Col B), and Theme (Col C) to Google Sheet."""
    if sheet:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        sheet.append_row([today_str, word, theme])
        print(f"[+] Saved '{word}' | Theme: '{theme}' across columns A, B, C in {SHEET_NAME} (Sheet1).")

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
    theme_key, theme_label = THEME_SCHEDULE.get(
        weekday, 
        ("Expressive Words", "Daily Expressive Words (Bhaav-Boli)")
    )

    # Allow overriding theme for manual testing: e.g. python MarwarVaani_Agent.py --theme "Kitchen & Food"
    for idx, arg in enumerate(sys.argv):
        if arg == "--theme" and idx + 1 < len(sys.argv):
            override = sys.argv[idx + 1]
            for k, (tk, tl) in THEME_SCHEDULE.items():
                if override.lower() in tk.lower() or override.lower() in tl.lower():
                    theme_key, theme_label = tk, tl
                    break
            else:
                theme_key, theme_label = override, override

    print("====================================")
    print("      PROJECT MARWARVAANI AGENT     ")
    if dry_run:
        print("          [MODE: DRY RUN]           ")
    print("====================================\n")
    
    print(f"[*] Today's Day: {datetime.date.today().strftime('%A')} (Weekday {weekday})")
    print(f"[*] Today's Theme: {theme_label} [Seed Key: {theme_key}]\n")

    if dry_run and not has_callmebot:
        print("[*] Notice: CallMeBot credentials not configured. WhatsApp dispatch skipped.\n")
    elif dry_run:
        print("[*] Notice: Dry Run flag detected. WhatsApp dispatch skipped.\n")

    # 1. Connect to Google Sheets & check Curated list vs History
    print("[1/6] Checking Google Sheets...")
    client = get_sheets_client()
    
    curated_ws, row_idx, picked_word, picked_translit = fetch_curated_or_fallback(client, theme_key)
    log_sheet, recent_history = get_recent_history(client)
    print(f"[*] History log (Sheet1) contains {len(recent_history)} previously used entries.")

    # 2. Generate Card (Curated first, Autonomous fallback)
    if picked_word:
        print(f"\n[2/6] Found curated term in 'Curated_Words' seed list (Row {row_idx}):")
        print(f"      👉 {picked_word} ({picked_translit})")
        print(f"      Generating rich card via Gemini for '{theme_label}'...")
        card_data = generate_marwarvaani_card(theme_label, specific_word=picked_word, specific_translit=picked_translit)
    else:
        print(f"\n[2/6] No unused curated words in 'Curated_Words' for theme '{theme_key}'.")
        print("      Switching to autonomous Gemini generation with deduplication...")
        card_data = generate_marwarvaani_card(theme_label, excluded_words=recent_history)

    # 3. Format Card Preview
    formatted_msg = format_whatsapp_message(card_data)
    print("\n" + "=" * 20 + " CARD PREVIEW " + "=" * 20)
    print(formatted_msg)
    print("=" * 54 + "\n")

    # 4. Append to Google Doc Journal
    print("[3/6] Appending to Google Doc 'MarwarVaani_Msg'...")
    if GOOGLE_DOC_ID:
        append_to_google_doc(GOOGLE_DOC_ID, formatted_msg)
    else:
        print("[!] GOOGLE_DOC_ID not configured in .env.")

    # 5. WhatsApp Dispatch
    print("\n[4/6] WhatsApp Dispatch:")
    if dry_run:
        print("[*] WhatsApp dispatch skipped (CallMeBot not configured / dry run active).")
    else:
        send_whatsapp_alert(CALLMEBOT_PHONE, formatted_msg, CALLMEBOT_APIKEY)

    # 6. Save to Web Archive (docs/data/cards.json)
    print("\n[5/6] Updating Web Archive (docs/data/cards.json)...")
    if dry_run and "--save-log" not in sys.argv:
        print("[*] DRY RUN: Web Archive update skipped (pass --save-log to update).")
    else:
        save_to_web_archive(card_data)

    # 7. Update Google Sheets (Log in Sheet1 & Mark USED in Curated_Words)
    print("\n[6/6] Updating Google Sheets:")
    if dry_run and "--save-log" not in sys.argv:
        print("[*] DRY RUN: Google Sheet updates skipped (keeps seed list and history clean).")
        print("    (Pass --save-log if you want to update Google Sheets during dry run)")
    else:
        # A. Log in Sheet1
        word_entry = card_data.get("word_devanagari", "")
        theme_entry = card_data.get("theme", theme_label)
        log_entry(log_sheet, word_entry, theme_entry)

        # B. Mark as USED in Curated_Words tab
        if curated_ws and row_idx:
            try:
                curated_ws.update_cell(row_idx, 4, "USED")
                print(f"[+] Marked row {row_idx} ('{picked_word}') as 'USED' in Curated_Words tab.")
            except Exception as e:
                print(f"[!] Warning: Could not mark row {row_idx} as USED: {e}")

    print("\nRun complete.")

if __name__ == "__main__":
    main()
