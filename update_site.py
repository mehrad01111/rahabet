import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import datetime
from datetime import timedelta
import time
import random

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ---------------------------------------------------------
# تنظیمات حرفه‌ای برای جلوگیری از بلاک شدن توسط ورزش 3
# ---------------------------------------------------------
def get_headers():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.varzesh3.com/",
        "Connection": "keep-alive"
    }

def fetch_matches_from_varzesh3(date_query=None):
    base_url = "https://www.varzesh3.com/livescore"
    url = base_url
    if date_query:
        url = f"{base_url}?date={date_query}"
        
    print(f"Connecting to: {url}")
    
    try:
        # استفاده از Session برای پایداری بیشتر
        session = requests.Session()
        response = session.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code != 200:
            print(f"Error Code: {response.status_code}")
            return "<tr><td colspan='4'>عدم دسترسی به سرور ورزش 3</td></tr>"

        soup = BeautifulSoup(response.content, 'lxml')
        
        matches_html = ""
        # تلاش برای پیدا کردن کلاس‌های مختلف (چون گاهی ورزش 3 تغییر می‌دهد)
        match_rows = soup.select('.match-row')
        
        # اگر لیست خالی بود، شاید ساختار صفحه عوض شده یا بازی نیست
        if not match_rows:
            print("No .match-row found in HTML.")
            # چک کردن برای پیام 'بازی وجود ندارد'
            if "بازی وجود ندارد" in response.text:
                return "<tr><td colspan='4'>بازی مهمی برای این تاریخ ثبت نشده است.</td></tr>"
            return "<tr><td colspan='4'>در حال حاضر اطلاعات در دسترس نیست.</td></tr>"

        # محدود کردن به 6 بازی اول برای شلوغ نشدن
        count = 0
        for match in match_rows:
            if count >= 6: break
            
            teams = match.select('.team-name')
            time_box = match.select_one('.time')
            
            # فقط بازی‌هایی که نام دو تیم و زمان دارند را بردار
            if len(teams) >= 2 and time_box:
                team_home = teams[0].get_text(strip=True)
                team_away = teams[1].get_text(strip=True)
                match_time = time_box.get_text(strip=True)
                
                # فیلتر کردن بازی‌های نامعتبر (اختیاری)
                if not team_home or not team_away:
                    continue

                match_name = f"{team_home} - {team_away}"
                
                row = f"""
                <tr>
                    <td>⚽ فوتبال</td>
                    <td>{match_name}</td>
                    <td>{match_time}</td>
                    <td><button class="history-btn" onclick="openModal('{match_name}')">مشاهده</button></td>
                </tr>
                """
                matches_html += row
                count += 1
        
        if matches_html == "":
            return "<tr><td colspan='4'>بازی مهمی یافت نشد.</td></tr>"
            
        return matches_html

    except Exception as e:
        print(f"Exception Error: {e}")
        return "<tr><td colspan='4'>خطا در بروزرسانی اطلاعات</td></tr>"

def generate_daily_content():
    # اگر هوش مصنوعی خطا داد، محتوای قبلی خراب نشود
    prompt = """
    یک مقاله کوتاه (100 کلمه) درباره استراتژی برد در شرط بندی فوتبال بنویس. 
    فرمت HTML ساده باشد (<article>, <h2>, <p>).
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a betting expert."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI Error: {e}")
        return None # برگرداندن None یعنی دست نزن

def update_html_file():
    today = datetime.date.today()
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    print("--- Starting Update ---")
    
    # دریافت بازی‌ها
    matches_today = fetch_matches_from_varzesh3(today.strftime("%Y-%m-%d"))
    time.sleep(2) # وقفه کوتاه برای اینکه ربات تشخیص داده نشود
    matches_tomorrow = fetch_matches_from_varzesh3(tomorrow_str)
    
    # دریافت مقاله
    new_article = generate_daily_content()

    with open("index.html", "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # آپدیت جدول امروز
    if "خطا" not in matches_today: # فقط اگر خطا نداشت آپدیت کن
        tbody_today = soup.find(id="matches-body")
        if tbody_today:
            tbody_today.clear()
            tbody_today.append(BeautifulSoup(matches_today, 'html.parser'))

    # آپدیت جدول فردا
    if "خطا" not in matches_tomorrow:
        tbody_tomorrow = soup.find(id="tomorrow-matches-body")
        if tbody_tomorrow:
            tbody_tomorrow.clear()
            tbody_tomorrow.append(BeautifulSoup(matches_tomorrow, 'html.parser'))

    # آپدیت مقاله
    if new_article:
        article_section = soup.find(id="ai-articles")
        if article_section:
            article_section.clear()
            article_section.append(BeautifulSoup(new_article, 'html.parser'))

    with open("index.html", "w", encoding="utf-8") as file:
        file.write(str(soup))
    
    print("--- Update Finished Successfully ---")

if __name__ == "__main__":
    update_html_file()
