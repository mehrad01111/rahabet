import os
import requests
import json
from bs4 import BeautifulSoup
from openai import OpenAI
import datetime
from datetime import timedelta

# تنظیمات
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ---------------------------------------------------------
# 1. دریافت داده‌ها از API FotMob (بدون نیاز به Scraping)
# ---------------------------------------------------------
def get_fotmob_matches(target_date):
    # فرمت تاریخ برای فوت‌موب: YYYYMMDD
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.fotmob.com/api/matches?date={date_str}"
    
    print(f"Connecting to FotMob API: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Error Code: {response.status_code}")
            return None
            
        data = response.json()
        
        # لیست لیگ‌های مهم که می‌خواهیم نمایش دهیم (ID ها ثابت هستند)
        important_leagues = [
            47,   # Premier League (England)
            87,   # LaLiga (Spain)
            54,   # Bundesliga (Germany)
            55,   # Serie A (Italy)
            53,   # Ligue 1 (France)
            42,   # Champions League
            290,  # Persian Gulf Pro League (Iran) - لیگ ایران
        ]
        
        matches_list = []
        
        for league in data.get('leagues', []):
            league_id = league.get('id')
            
            # اگر لیگ جزو لیست مهم‌ها بود
            if league_id in important_leagues:
                league_name = league.get('name')
                for match in league.get('matches', []):
                    # استخراج نام تیم‌ها و زمان
                    home = match.get('home', {}).get('name')
                    away = match.get('away', {}).get('name')
                    time_str = match.get('time') # فرمت زمان خاصی دارد
                    status = match.get('status', {}).get('started')
                    
                    # فقط بازی‌هایی که کنسل نشده‌اند
                    if home and away and not match.get('status', {}).get('cancelled'):
                        matches_list.append(f"{league_name}: {home} vs {away} at {time_str}")

        # اگر هیچ بازی مهمی نبود (مثلا وسط هفته)، 5 بازی اول لیست کلی را بردار
        if not matches_list and data.get('leagues'):
            for league in data['leagues'][:2]: # 2 لیگ اول
                for match in league.get('matches', [])[:3]:
                    home = match.get('home', {}).get('name')
                    away = match.get('away', {}).get('name')
                    time_str = match.get('time')
                    matches_list.append(f"Global: {home} vs {away} at {time_str}")

        return matches_list[:8] # حداکثر 8 بازی

    except Exception as e:
        print(f"Error fetching FotMob: {e}")
        return None

# ---------------------------------------------------------
# 2. ترجمه و تنظیم زمان با هوش مصنوعی
# ---------------------------------------------------------
def translate_and_format(matches_list):
    if not matches_list:
        return None

    matches_str = "\n".join(matches_list)
    
    prompt = f"""
    I have a list of football matches (from FotMob).
    Tasks:
    1. Translate League names and Team names to Persian.
    2. The time provided is usually UTC or local. Convert it to 'Tehran Time'.
    3. Return a clean JSON list.
    
    Input List:
    {matches_str}
    
    Output Format (JSON Only):
    [
        {{"league": "لیگ برتر", "match": "تیم‌یک - تیم‌دو", "time": "HH:MM"}}
    ]
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a useful assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        result = response.choices[0].message.content
        data = json.loads(result)
        
        # هندل کردن خروجی
        if "matches" in data:
            return data["matches"]
        if isinstance(data, list):
            return data
        return list(data.values())[0]

    except Exception as e:
        print(f"AI Translation Error: {e}")
        return None

# ---------------------------------------------------------
# 3. تولید HTML
# ---------------------------------------------------------
def create_html_rows(json_data):
    if not json_data:
        return "<tr><td colspan='4'>اطلاعات بازی‌ها در حال بروزرسانی است...</td></tr>"
    
    html_output = ""
    for item in json_data:
        league = item.get('league', 'فوتبال')
        match_name = item.get('match', '')
        match_time = item.get('time', '--:--')
        
        if match_name:
            html_output += f"""
            <tr>
                <td style="font-size:0.8rem; color:#f59e0b;">{league}</td>
                <td>{match_name}</td>
                <td>{match_time}</td>
                <td><button class="history-btn" onclick="openModal('{match_name}')">آمار</button></td>
            </tr>
            """
    return html_output

# ---------------------------------------------------------
# 4. تابع اصلی آپدیت
# ---------------------------------------------------------
def update_site():
    print("--- Starting FotMob Update ---")
    
    today = datetime.date.today()
    tomorrow = today + timedelta(days=1)
    
    # --- امروز ---
    raw_today = get_fotmob_matches(today)
    print(f"Matches found for today: {len(raw_today) if raw_today else 0}")
    
    persian_today = translate_and_format(raw_today)
    html_today = create_html_rows(persian_today)
    
    # --- فردا ---
    raw_tomorrow = get_fotmob_matches(tomorrow)
    print(f"Matches found for tomorrow: {len(raw_tomorrow) if raw_tomorrow else 0}")
    
    persian_tomorrow = translate_and_format(raw_tomorrow)
    html_tomorrow = create_html_rows(persian_tomorrow)
    
    # --- مقاله هوش مصنوعی ---
    try:
        ai_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "یک مقاله کوتاه HTML (تگ article) درباره ترفندهای پیش‌بینی فوتبال بنویس."}]
        )
        ai_article = ai_resp.choices[0].message.content
    except:
        ai_article = None

    # --- ذخیره در فایل HTML ---
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        # جایگذاری امروز
        target_today = soup.find(id="matches-body")
        if target_today:
            target_today.clear()
            target_today.append(BeautifulSoup(html_today, 'html.parser'))

        # جایگذاری فردا
        target_tomorrow = soup.find(id="tomorrow-matches-body")
        if target_tomorrow:
            target_tomorrow.clear()
            target_tomorrow.append(BeautifulSoup(html_tomorrow, 'html.parser'))
        
        # جایگذاری مقاله
        if ai_article:
            target_art = soup.find(id="ai-articles")
            if target_art:
                target_art.clear()
                target_art.append(BeautifulSoup(ai_article, 'html.parser'))

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
            
        print("--- Update Finished Successfully ---")
        
    except Exception as e:
        print(f"File Error: {e}")

if __name__ == "__main__":
    update_site()
