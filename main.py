import os
import requests
from datetime import datetime

# --- CONFIGURATION (Environment Variables) ---
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- EMOJI MAPPING ---
# Ders isimlerine göre emoji atar. Notion'daki "Ders" property'si ile eşleşmeli.
EMOJIS = {
    "Matematik": "🧮",
    "Tarih": "📜",
    "Coğrafya": "🌍",
    "Vatandaşlık": "⚖️",
    "Türkçe": "📘",
    "Genel Tekrar": "🔄",
    "Deneme": "📝"
}

def get_tasks_for_today():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Notion filtreleme: Tarih = Bugün
    today_str = datetime.now().strftime("%Y-%m-%d")
    # Test hali (3 Şubat verisini çekmesi için):
    #today_str = "2026-02-03"
    
    payload = {
        "filter": {
            "property": "Tarih", # Notion'daki tarih sütununun adı
            "date": {
                "equals": today_str
            }
        },
        "sorts": [
            {
                "property": "Ders",
                "direction": "ascending"
            }
        ]
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"Hata: Notion API yanıt vermedi. Kod: {response.status_code}")
        print(response.text)
        return []
        
    return response.json().get("results", [])

def format_telegram_message(tasks):
    if not tasks:
        return "🎉 Bugün planlı bir çalışman yok! Dinlenme günü."
    
    today_date = datetime.now().strftime("%d.%m.%Y")
    message = f"📅 *KPSS Günlük Plan - {today_date}*\n\n"
    
    total_minutes = 0
    
    for task in tasks:
        props = task["properties"]
        
        # Notion verilerini güvenli şekilde çekme (Safe parsing)
        try:
            # DEBUG: Mevcut anahtarları görelim
            # print(f"Sütunlar: {list(props.keys())}")  # <-- Bunu açarsan tüm sütun adlarını görürsün

            # Ders (Select Property)
            ders = props["Ders"]["select"]["name"]
            emoji = EMOJIS.get(ders, "📌")
            
            # --- HATANIN OLDUĞU YER ---
            # Önce "Konu" var mı kontrol edelim, yoksa alternatiflere bakalım
            if "Konu" in props:
                konu_obj = props["Konu"]
            elif "Name" in props:  # Notion varsayılan olarak "Name" kullanır
                konu_obj = props["Name"]
            elif "konu" in props: # Küçük harf ihtimali
                konu_obj = props["konu"]
            else:
                # Hiçbiri yoksa, hatayı yakalamak için log basalım
                print(f"KRİTİK HATA: 'Konu' sütunu bulunamadı! Mevcut sütunlar: {list(props.keys())}")
                continue # Bu satırı atla

            # Şimdi içeriği almayı deneyelim (Title veya Rich Text olabilir)
            konu_list = konu_obj.get("title", [])
            if not konu_list:
                konu_list = konu_obj.get("rich_text", []) # Belki Text property'dir
            
            if not konu_list:
                 konu = "Konu belirtilmemiş"
            else:
                 konu = konu_list[0]["text"]["content"]
            
            # Süre (Number Property)
            sure = props["Süre"]["number"]
            total_minutes += sure if sure else 0
            
            message += f"{emoji} *{ders}* ({sure} dk)\n└ _{konu}_\n\n"
            
        except Exception as e:
            print(f"Veri işlenirken hata: {e}")
            # Hata anında tüm satırın yapısını görelim ki neyin yanlış olduğunu anlayalım
            print(f"Hatalı Satırın Anahtarları: {list(props.keys())}") 
            continue
            # Ders (Select Property)
            ders = props["Ders"]["select"]["name"]
            emoji = EMOJIS.get(ders, "📌")
            
            # Konu (Title Property - Veritabanının ana sütunu genelde title olur)
            # Eğer "Konu" sütunu Title değil de Text ise ["rich_text"] kullanılır.
            # Notion'da ana sütun hangisiyse (Name/Konu) onu title olarak al.
            konu_list = props["Konu"].get("title", [])
            if not konu_list: # Eğer boşsa
                 konu = "Konu belirtilmemiş"
            else:
                 konu = konu_list[0]["text"]["content"]
            
            # Süre (Number Property)
            sure = props["Süre"]["number"]
            total_minutes += sure if sure else 0
            
            message += f"{emoji} *{ders}* ({sure} dk)\n└ _{konu}_\n\n"
            
        except Exception as e:
            print(f"Veri işlenirken hata: {e}")
            continue
            
    # Toplam çalışma süresi
    hours = total_minutes // 60
    minutes = total_minutes % 60
    message += f"⏱️ *Toplam:* {hours} saat {minutes} dakika"
    
    return message

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    
    # HATA AYIKLAMA KISMI
    if response.status_code == 200:
        print("✅ Telegram Başarılı: Mesaj iletildi.")
    else:
        print(f"❌ Telegram Hatası! Kod: {response.status_code}")
        print(f"Detay: {response.text}")

if __name__ == "__main__":
    print("Notion taranıyor...")
    tasks = get_tasks_for_today()
    print(f"{len(tasks)} görev bulundu.")
    
    msg = format_telegram_message(tasks)
    send_telegram_message(msg)
    print("Telegram mesajı gönderildi.")