import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import datetime
from datetime import timedelta

# تنظیمات و اتصال به هوش مصنوعی
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ---------------------------------------------------------
# تابع کمکی: دریافت بازی‌ها بر اساس تاریخ
# ---------------------------------------------------------
def fetch_matches_from_varzesh3(date_query=None):
    """
    اگر date_query داده نشود، بازی‌های امروز را می‌گیرد.
    اگر داده شود (فرمت YYYY-MM-DD)، بازی‌های آن تاریخ را می‌گیرد.
    """
    url = "https://www.varzesh3.com/livescore"
    if date_query:
        url = f"https://www.varzesh3.com/livescore?date={date_query}"
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'lxml')
        
        matches_html = ""
        # انتخاب 5 بازی اول مهم
        match_rows = soup.select('.match-row')[:5] 
        
        if not match_rows:
            return "<tr><td colspan='4'>بازی مهمی یافت نشد.</td></tr>"

        for match in match_rows:
            teams = match.select('.team-name')
            time_box = match.select_one('.time')
            
            if len(teams) >= 2 and time_box:
                team_home = teams[0].get_text(strip=True)
                team_away = teams[1].get_text(strip=True)
                match_time = time_box.get_text(strip=True)
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
                
        return matches_html

    except Exception as e:
        print(f"Error scraping Varzesh3 ({url}): {e}")
        return "<tr><td colspan='4'>خطا در دریافت اطلاعات</td></tr>"

# ---------------------------------------------------------
# بخش تولید محتوا با هوش مصنوعی (بدون تغییر)
# ---------------------------------------------------------
def generate_daily_content():
    prompt = """
    یک مقاله کوتاه و جذاب (حدود 150 کلمه) برای سایت شرط بندی بنویس.
    موضوع باید یکی از این‌ها باشد: استراتژی بازی انفجار، بونوس‌های شرط بندی، یا تحلیل فوتبال.
    فرمت خروجی HTML باشد (<article>, <h2>, <p>).
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a SEO expert copywriter."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error AI: {e}")
        return "<article><h2>خطا</h2><p>محتوا در حال بروزرسانی است.</p></article>"

# ---------------------------------------------------------
# بخش اصلی: آپدیت فایل HTML
# ---------------------------------------------------------
def update_html_file():
    # 1. محاسبه تاریخ‌ها
    today = datetime.date.today()
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d") # فرمت مورد نیاز ورزش 3

    print(f"Fetching matches for Today and Tomorrow ({tomorrow_str})...")

    # 2. دریافت اطلاعات
    matches_today_html = fetch_matches_from_varzesh3() # امروز
    matches_tomorrow_html = fetch_matches_from_varzesh3(tomorrow_str) # فردا
    new_article = generate_daily_content()

    # 3. باز کردن فایل HTML
    with open("index.html", "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # 4. جایگذاری جدول امروز
    tbody_today = soup.find(id="matches-body")
    if tbody_today:
        tbody_today.clear()
        tbody_today.append(BeautifulSoup(matches_today_html, 'html.parser'))

    # 5. جایگذاری جدول فردا (بخش جدید)
    tbody_tomorrow = soup.find(id="tomorrow-matches-body")
    if tbody_tomorrow:
        tbody_tomorrow.clear()
        tbody_tomorrow.append(BeautifulSoup(matches_tomorrow_html, 'html.parser'))

    # 6. جایگذاری مقاله
    article_section = soup.find(id="ai-articles")
    if article_section:
        article_section.clear()
        article_section.append(BeautifulSoup(new_article, 'html.parser'))

    # 7. ذخیره نهایی
    with open("index.html", "w", encoding="utf-8") as file:
        file.write(str(soup))
    
    print("Website updated successfully with TWO tables!")

if __name__ == "__main__":
    update_html_file()
