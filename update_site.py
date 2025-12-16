import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import datetime
from datetime import timedelta
import json

# تنظیمات
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ---------------------------------------------------------
# 1. دریافت بازی‌ها از منبع خارجی (Sky Sports)
# ---------------------------------------------------------
def get_english_matches(is_tomorrow=False):
    # تعیین تاریخ برای لینک
    target_date = datetime.date.today()
    if is_tomorrow:
        target_date = target_date + timedelta(days=1)
    
    # فرمت تاریخ اسکای اسپورت: yyyy-mm-dd (مثلا 2024-12-05)
    date_str = target_date.strftime("%Y-%m-%d")
    url = f"https://www.skysports.com/football-fixtures/{date_str}"
    
    print(f"Fetching from SkySports: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        matches_list = []
        
        # پیدا کردن باکس بازی‌ها
        # ساختار اسکای اسپورت: هر بازی در یک کلاس fixres__item است
        match_items = soup.select('.fixres__item')
        
        count = 0
        for item in match_items:
            if count >= 6: break # فقط 6 بازی مهم
            
            # استخراج نام تیم‌ها
            participant_1 = item.select_one('.matches__participant--side1 .matches__participant-text')
            participant_2 = item.select_one('.matches__participant--side2 .matches__participant-text')
            time_el = item.select_one('.matches__date')
            
            if participant_1 and participant_2 and time_el:
                p1_text = participant_1.get_text(strip=True)
                p2_text = participant_2.get_text(strip=True)
                time_text = time_el.get_text(strip=True) # زمان به وقت انگلیس است
                
                # فیلتر کردن لیگ‌های ناشناس (اختیاری - هوش مصنوعی هم می‌تواند فیلتر کند)
                matches_list.append(f"{p1_text} vs {p2_text} at {time_text} (UK Time)")
                count += 1
                
        if not matches_list:
            print("No matches found on SkySports page.")
            return None
            
        return matches_list

    except Exception as e:
        print(f"Error scraping SkySports: {e}")
        return None

# ---------------------------------------------------------
# 2. تبدیل به فارسی توسط هوش مصنوعی
# ---------------------------------------------------------
def translate_matches_to_persian(matches_list):
    if not matches_list:
        return None

    matches_str = "\n".join(matches_list)
    
    prompt = f"""
    I have a list of football matches in English (UK Time).
    Your task:
    1. Translate team names to Persian.
    2. Convert the time from UK Time to Tehran Time (+3.5 hours).
    3. Return the result ONLY as a JSON list of objects.
    
    Format:
    [
        {{"match": "تیم یک - تیم دو", "time": "HH:MM"}}
    ]

    Here is the list:
    {matches_str}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # مدل ارزان و سریع
            messages=[
                {"role": "system", "content": "You are a helpful translator assistant. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" } # تضمین خروجی جیسون
        )
        
        result = response.choices[0].message.content
        data = json.loads(result)
        
        # اگر خروجی داخل کلید خاصی بود آن را بردار، اگر لیست بود خود لیست
        if "matches" in data:
            return data["matches"]
        # گاهی AI مستقیم لیست برنمی‌گرداند، باید مدیریت شود.
        # اما با response_format معمولا آبجکت برمیگردد.
        # فرض میکنیم AI خروجی { "matches": [...] } داده است.
        return list(data.values())[0] # اولین ولیو را برمیگرداند که لیست است

    except Exception as e:
        print(f"AI Translation Error: {e}")
        return None

# ---------------------------------------------------------
# 3. تولید HTML نهایی
# ---------------------------------------------------------
def create_html_rows(json_data):
    if not json_data:
        return "<tr><td colspan='4'>بازی مهمی یافت نشد (بروزرسانی می‌شود)</td></tr>"
    
    html_output = ""
    for item in json_data:
        # هندل کردن فرمت‌های مختلف جیسون احتمالی
        match_name = item.get('match') or item.get('game')
        match_time = item.get('time') or item.get('clock')
        
        if match_name and match_time:
            row = f"""
            <tr>
                <td>⚽ فوتبال</td>
                <td>{match_name}</td>
                <td>{match_time}</td>
                <td><button class="history-btn" onclick="openModal('{match_name}')">مشاهده</button></td>
            </tr>
            """
            html_output += row
            
    return html_output

# ---------------------------------------------------------
# 4. آپدیت سایت
# ---------------------------------------------------------
def update_site():
    print("--- Starting International Update ---")
    
    # --- امروز ---
    english_today = get_english_matches(is_tomorrow=False)
    persian_today_data = translate_matches_to_persian(english_today)
    html_today = create_html_rows(persian_today_data)
    
    # --- فردا ---
    english_tomorrow = get_english_matches(is_tomorrow=True)
    persian_tomorrow_data = translate_matches_to_persian(english_tomorrow)
    html_tomorrow = create_html_rows(persian_tomorrow_data)
    
    # --- مقاله هوش مصنوعی ---
    try:
        article_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "یک مقاله کوتاه HTML (تگ article) درباره استراتژی مدیریت سرمایه در شرط بندی بنویس."}]
        )
        ai_article = article_resp.choices[0].message.content
    except:
        ai_article = None

    # --- ذخیره در فایل ---
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

if __name__ == "__main__":
    update_site()
