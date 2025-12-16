import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import datetime
from datetime import timedelta
import random

# تنظیمات هوش مصنوعی
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ---------------------------------------------------------
# تنظیمات هدر برای شبیه‌سازی مرورگر واقعی
# ---------------------------------------------------------
def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fa-IR,fa;q=0.9",
        "Referer": "https://www.google.com/",
    }

# ---------------------------------------------------------
# منبع 1: طرفداری (شانس موفقیت بالا)
# ---------------------------------------------------------
def scrape_tarafdari(date_str=None):
    # طرفداری معمولا آدرسش به این صورته: /livescore
    url = "https://www.tarafdari.com/livescore"
    # نکته: طرفداری آرشیو روزهای آینده رو سخت‌تر میده، پس فقط برای امروز تست میکنیم
    # اگر تاریخ فردا بود شاید جواب نده، ولی برای امروز عالیه
    
    print(f"Trying Source 1 (Tarafdari): {url}")
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        matches_html = ""
        # پیدا کردن ردیف‌های بازی در طرفداری
        # کلاس‌های طرفداری ممکن است فرق کند، این یک سلکتور عمومی است
        rows = soup.select('.livescore-match-row') 
        
        if not rows:
             # تلاش دوم برای ساختار موبایل یا قدیمی
             rows = soup.select('.match-row')

        count = 0
        for row in rows:
            if count >= 5: break
            
            teams = row.select('.team-name')
            time_el = row.select_one('.match-time') or row.select_one('.time')
            
            if len(teams) >= 2 and time_el:
                home = teams[0].get_text(strip=True)
                away = teams[1].get_text(strip=True)
                m_time = time_el.get_text(strip=True)
                
                match_name = f"{home} - {away}"
                
                matches_html += f"""
                <tr>
                    <td>⚽ فوتبال</td>
                    <td>{match_name}</td>
                    <td>{m_time}</td>
                    <td><button class="history-btn" onclick="openModal('{match_name}')">مشاهده</button></td>
                </tr>
                """
                count += 1
        
        return matches_html if matches_html else None

    except Exception as e:
        print(f"Tarafdari failed: {e}")
        return None

# ---------------------------------------------------------
# منبع 2: ورزش 3 (اگر طرفداری نشد)
# ---------------------------------------------------------
def scrape_varzesh3(date_str):
    url = f"https://www.varzesh3.com/livescore?date={date_str}"
    print(f"Trying Source 2 (Varzesh3): {url}")
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')
        rows = soup.select('.match-row')
        
        matches_html = ""
        count = 0
        for row in rows:
            if count >= 5: break
            teams = row.select('.team-name')
            time_el = row.select_one('.time')
            
            if len(teams) >= 2 and time_el:
                home = teams[0].get_text(strip=True)
                away = teams[1].get_text(strip=True)
                m_time = time_el.get_text(strip=True)
                match_name = f"{home} - {away}"
                
                matches_html += f"""
                <tr>
                    <td>⚽ فوتبال</td>
                    <td>{match_name}</td>
                    <td>{m_time}</td>
                    <td><button class="history-btn" onclick="openModal('{match_name}')">مشاهده</button></td>
                </tr>
                """
                count += 1
        return matches_html if matches_html else None
    except Exception as e:
        print(f"Varzesh3 failed: {e}")
        return None

# ---------------------------------------------------------
# منبع 3: داده‌های زاپاس (Backup) - برای اینکه سایت خالی نباشد
# ---------------------------------------------------------
def get_backup_data(is_tomorrow=False):
    print("Using Backup Data (Fake Data)")
    if is_tomorrow:
        return """
        <tr><td>⚽ فوتبال</td><td>منچستر سیتی - لیورپول</td><td>18:30</td><td><button class="history-btn">مشاهده</button></td></tr>
        <tr><td>⚽ فوتبال</td><td>بایرن مونیخ - دورتموند</td><td>21:00</td><td><button class="history-btn">مشاهده</button></td></tr>
        <tr><td>⚽ فوتبال</td><td>سپاهان - پرسپولیس</td><td>16:00</td><td><button class="history-btn">مشاهده</button></td></tr>
        """
    else:
        return """
        <tr><td>⚽ فوتبال</td><td>رئال مادرید - بارسلونا</td><td>22:30</td><td><button class="history-btn">مشاهده</button></td></tr>
        <tr><td>⚽ فوتبال</td><td>استقلال - تراکتور</td><td>17:30</td><td><button class="history-btn">مشاهده</button></td></tr>
        <tr><td>⚽ فوتبال</td><td>آرسنال - چلسی</td><td>20:00</td><td><button class="history-btn">مشاهده</button></td></tr>
        """

# ---------------------------------------------------------
# هوش مصنوعی (مقاله نویسی)
# ---------------------------------------------------------
def generate_ai_content():
    prompt = """
    یک مقاله خیلی کوتاه (3 پاراگراف) درباره "رازهای برد در پیش‌بینی فوتبال" بنویس.
    خروجی فقط HTML باشد (<article>, <h2>, <p>).
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except:
        return None

# ---------------------------------------------------------
# تابع اصلی آپدیت
# ---------------------------------------------------------
def update_site():
    today = datetime.date.today().strftime("%Y-%m-%d")
    tomorrow = (datetime.date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # دریافت بازی‌های امروز (اولویت: طرفداری -> ورزش3 -> بک‌آپ)
    today_html = scrape_tarafdari() 
    if not today_html:
        today_html = scrape_varzesh3(today)
    if not today_html:
        today_html = get_backup_data(is_tomorrow=False)

    # دریافت بازی‌های فردا (اولویت: ورزش3 -> بک‌آپ)
    # چون طرفداری لینک فردایش سخت است، اول ورزش 3 را چک میکنیم
    tomorrow_html = scrape_varzesh3(tomorrow)
    if not tomorrow_html:
        tomorrow_html = get_backup_data(is_tomorrow=True)

    # دریافت مقاله
    ai_content = generate_ai_content()

    # اعمال تغییرات
    with open("index.html", "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # جایگذاری امروز
    target_today = soup.find(id="matches-body")
    if target_today:
        target_today.clear()
        target_today.append(BeautifulSoup(today_html, 'html.parser'))

    # جایگذاری فردا
    target_tomorrow = soup.find(id="tomorrow-matches-body")
    if target_tomorrow:
        target_tomorrow.clear()
        target_tomorrow.append(BeautifulSoup(tomorrow_html, 'html.parser'))
    
    # جایگذاری مقاله
    if ai_content:
        target_article = soup.find(id="ai-articles")
        if target_article:
            target_article.clear()
            target_article.append(BeautifulSoup(ai_content, 'html.parser'))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(str(soup))
    
    print("Site Updated Successfully!")

if __name__ == "__main__":
    update_site()
