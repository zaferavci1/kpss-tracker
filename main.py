import requests
import datetime
import os
import sys

# --- GÜVENLİK İÇİN ENVIRONMENT VARIABLE KULLANIMI ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID") 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)

def check_daily_progress():
    # Notion'daki tarih formatına (YYYY-MM-DD) uygun bugünün tarihini al
    today_str = datetime.date.today().isoformat()
    
    # 1. Veritabanında BUGÜNÜN tarihini sorgula
    query_payload = {
        "filter": {
            "property": "Tarih", 
            "date": {
                "equals": today_str
            }
        }
    }
    
    try:
        response = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers, json=query_payload)
        data = response.json()
        
        # Eğer API hatası dönerse loglayalım
        if response.status_code != 200:
            print("Notion API Hatası:", response.text)
            return

        if not data["results"]:
            print(f"{today_str} tarihi için plan bulunamadı. Tatil günü olabilir mi?")
            return

        page_props = data["results"][0]["properties"]
        
        # 2. Checkboxları kontrol et
        checks = {
            "Paragraf": page_props.get("Paragraf ✓", {}).get("checkbox", False),
            "Blok 1-2": page_props.get("Blok 1-2 ✓", {}).get("checkbox", False),
            "Blok 3-4": page_props.get("Blok 3-4 ✓", {}).get("checkbox", False)
        }
        
        # False (Boş) olanları bul
        missing = [name for name, status in checks.items() if not status]
        
        if missing:
            msg = f"⚠️ ALARM: Gün bitiyor!\n\nEksik Kalanlar:\n❌ " + "\n❌ ".join(missing) + "\n\nŞunları halletmeden uyuma!"
            send_telegram_message(msg)
            print("Eksikler var, mesaj atıldı.")
            # GitHub Action'ın hata vermemesi için exit code 0 bırakıyoruz, sadece bildirim amaçlı.
        else:
            print("Tüm görevler tamamlanmış. Tebrikler.")

    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")

if __name__ == "__main__":
    check_daily_progress()