import os
import requests
import time
from datetime import datetime, timedelta

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_DISCOUNT_PERCENT = 20  # Percentage minimum discount trigger

DESTINATIONS = [
    {"name": "Santorini, Grecia", "dest_id": "-3000632"},
    {"name": "Costa Smeralda / Olbia, Italia", "dest_id": "-123963"},
    {"name": "Parigi, Francia", "dest_id": "-1456928"},
]

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[!] Errore Telegram: {e}")

def search_deals(dest_id, checkin, checkout, duration_days):
    # Endpoint ufficiale dell'API di Tipsters CO
    url = "https://booking-com.p.rapidapi.com/v1/hotels/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
    }
    querystring = {
        "dest_id": dest_id,
        "search_type": "CITY",
        "checkin_date": checkin,
        "checkout_date": checkout,
        "adults_number": "2",
        "room_number": "1",
        "categories_filter_ids": "class::5",
        "order_by": "price",
        "currency": "EUR",
        "locale": "it"
    }

    try:
        res = requests.get(url, headers=headers, params=querystring, timeout=15)
        if res.status_code != 200:
            print(f"[!] Errore API {res.status_code}: {res.text[:100]}")
            return []
        
        data = res.json()
        hotels = data.get("result", [])
        found_deals = []
        
        for hotel in hotels:
            name = hotel.get("hotel_name")
            gross_price = hotel.get("min_total_price")
            strikethrough_price = hotel.get("strikethrough_price")
            
            if gross_price and strikethrough_price and strikethrough_price > gross_price:
                discount_pct = int(((strikethrough_price - gross_price) / strikethrough_price) * 100)
                if discount_pct >= MIN_DISCOUNT_PERCENT:
                    found_deals.append({
                        "name": name,
                        "discount": discount_pct,
                        "price": round(gross_price, 2),
                        "original_price": round(strikethrough_price, 2),
                        "duration": duration_days,
                        "checkin": checkin,
                        "checkout": checkout
                    })
        return found_deals
    except Exception as e:
        print(f"[!] Errore: {e}")
        return []

def main():
    print("=== Avvio Scan Hotel 5 Stelle ===")
    today = datetime.now()
    checkin_offsets = [30, 45]
    durations = [4, 7]
    
    total_deals = 0
    for dest in DESTINATIONS:
        print(f"\nScanning {dest['name']}...")
        for offset in checkin_offsets:
            checkin_dt = today + timedelta(days=offset)
            for duration in durations:
                checkout_dt = checkin_dt + timedelta(days=duration)
                checkin_str = checkin_dt.strftime("%Y-%m-%d")
                checkout_str = checkout_dt.strftime("%Y-%m-%d")
                
                deals = search_deals(dest["dest_id"], checkin_str, checkout_str, duration)
                for deal in deals:
                    total_deals += 1
                    msg = (
                        f"🚨 *OFFERTA 5 STELLE ({deal['discount']}% SCONTO)*\n\n"
                        f"🏨 *{deal['name']}*\n"
                        f"📍 {dest['name']}\n"
                        f"📅 {deal['duration']} Notti ({deal['checkin']} -> {deal['checkout']})\n"
                        f"💰 Prezzo: ~{deal['original_price']}€~ **{deal['price']}€**"
                    )
                    send_telegram_alert(msg)
                    time.sleep(2)
                
                time.sleep(4) # Pausa anti-blocco

    print(f"\nScan completato. Offerte trovate: {total_deals}")

if __name__ == "__main__":
    main()
    
