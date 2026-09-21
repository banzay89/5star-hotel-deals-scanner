import os
import requests
import time
from datetime import datetime, timedelta

# Configurazione Variabili d'Ambiente
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Sconto minimo per far scattare la notifica (es. 30%)
MIN_DISCOUNT_PERCENT = 30

# Principali destinazioni europee luxury da monitorare
DESTINATIONS = [
    {"name": "Santorini, Grecia", "dest_id": "-3000632", "search_type": "city"},
    {"name": "Costa Smeralda / Olbia, Italia", "dest_id": "-123963", "search_type": "city"},
    {"name": "Costa Azzurra / Nizza, Francia", "dest_id": "-1454848", "search_type": "city"},
    {"name": "Maiorca, Spagna", "dest_id": "-388339", "search_type": "city"},
    {"name": "Amalfi / Positano, Italia", "dest_id": "-125028", "search_type": "city"},
    {"name": "Parigi, Francia", "dest_id": "-1456928", "search_type": "city"},
    {"name": "Vienna, Austria", "dest_id": "-1984137", "search_type": "city"},
    {"name": "Mykonos, Grecia", "dest_id": "-1086880", "search_type": "city"},
]

def send_telegram_alert(message):
    """Invia una notifica Markdown via Bot Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Token Telegram o Chat ID mancanti.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[!] Errore nell'invio del messaggio Telegram: {e}")

def search_deals(dest_id, checkin, checkout, duration_days):
    """Esegue la ricerca hotel 5 stelle tramite RapidAPI (Booking.com API)"""
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
    
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "booking-com15.p.rapidapi.com"
    }
    
    querystring = {
        "dest_id": dest_id,
        "search_type": "CITY",
        "arrival_date": checkin,
        "departure_date": checkout,
        "adults": "2",
        "room_qty": "1",
        "page_number": "1",
        "categories_filter_ids": "class::5", # Filtro 5 Stelle
        "sort_by": "PRICE_LOW_TO_HIGH",
        "currency_code": "EUR"
    }

    try:
        res = requests.get(url, headers=headers, params=querystring, timeout=15)
        if res.status_code != 200:
            print(f"[!] Errore API {res.status_code}: {res.text[:100]}")
            return []
        
        data = res.json()
        hotels = data.get("data", {}).get("hotels", [])
        
        found_deals = []
        for hotel in hotels:
            property_info = hotel.get("property", {})
            name = property_info.get("name")
            
            # Estrazione Prezzi
            price_breakdown = property_info.get("priceBreakdown", {})
            gross_price = price_breakdown.get("grossPrice", {}).get("value")
            strikethrough_price = price_breakdown.get("strikethroughPrice", {}).get("value")
            
            if gross_price and strikethrough_price and strikethrough_price > gross_price:
                discount_pct = int(((strikethrough_price - gross_price) / strikethrough_price) * 100)
                
                if discount_pct >= MIN_DISCOUNT_PERCENT:
                    hotel_url = f"https://www.booking.com/hotel/{property_info.get('countryCode', 'eu')}/{property_info.get('checkout', '')}.html"
                    found_deals.append({
                        "name": name,
                        "discount": discount_pct,
                        "price": round(gross_price, 2),
                        "original_price": round(strikethrough_price, 2),
                        "review_score": property_info.get("reviewScore", "N/A"),
                        "duration": duration_days,
                        "checkin": checkin,
                        "checkout": checkout,
                        "url": hotel_url
                    })
        return found_deals

    except Exception as e:
        print(f"[!] Eccezione durante la ricerca: {e}")
        return []

def main():
    print("=== Avvio Scan Hotel 5 Stelle in Europa ===")
    
    # Date di test: Prossimi 30 e 60 giorni per soggiorni da 4 e 7 giorni
    today = datetime.now()
    checkin_offsets = [30, 45, 60] # giorni a partire da oggi
    durations = [4, 7] # Soggiorni di 4 e 7 giorni
    
    total_deals = 0
    
    for dest in DESTINATIONS:
        print(f"\nScanning: {dest['name']}...")
        for offset in checkin_offsets:
            checkin_dt = today + timedelta(days=offset)
            
            for duration in durations:
                checkout_dt = checkin_dt + timedelta(days=duration)
                
                checkin_str = checkin_dt.strftime("%Y-%m-%d")
                checkout_str = checkout_dt.strftime("%Y-%m-%d")
                
                print(f"  -> Periodo {duration} GG ({checkin_str} / {checkout_str})")
                
                deals = search_deals(dest["dest_id"], checkin_str, checkout_str, duration)
                
                for deal in deals:
                    total_deals += 1
                    msg = (
                        f"🚨 *SUPER OFFERTA 5 STELLE ({deal['discount']}% SCONTO)* 🚨\n\n"
                        f"🏨 *Hotel:* {deal['name']}\n"
                        f"📍 *Destinazione:* {dest['name']}\n"
                        f"📅 *Durata:* {deal['duration']} Notti ({deal['checkin']} -> {deal['checkout']})\n"
                        f"⭐ *Punteggio Recensioni:* {deal['review_score']}/10\n\n"
                        f"💰 *Prezzo Scontato:* ~{deal['original_price']}€~ **{deal['price']}€** totali\n\n"
                        f"🔗 [Vedi Offerta su Booking.com]({deal['url']})"
                    )
                    send_telegram_alert(msg)
                    time.sleep(1) # evita rate-limit
                    
                time.sleep(2) # Pausa tra richieste API

    print(f"\nScansione completata. Offerte trovate: {total_deals}")

if __name__ == "__main__":
    main()
