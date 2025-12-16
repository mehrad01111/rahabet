import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import datetime

# 1. تنظیمات و اتصال به هوش مصنوعی
# کلید از Secret های گیت‌هاب خوانده می‌شود
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ---------------------------------------------------------
# بخش اول: دریافت بازی‌های امروز از ورزش 3 (Scraping)
# ---------------------------------------------------------
def get_todays_matches():
    url = "https://www.varzesh3.com/livescore"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'lxml')
        
        # پیدا کردن ستون بازی‌های امروز
        matches_html = ""
        
        # ما فقط 5 بازی اول مهم را برمی‌داریم که شلوغ نشود
        match_rows = soup.select('.match-row')[:5] 
        
        if not match_rows:
            return "<tr><td colspan='4'>بازی مهمی برای امروز یافت نشد.</td></tr>"

        for match in match_rows:
            # استخراج نام تیم‌ها و زمان
            teams = match.select('.team-name')
            time_box = match.select_one('.time')
            
            if len(teams) >= 2 and time_box:
                team_home = teams[0].get_text(strip=True)
                team_away = teams[1].get_text(strip=True)
                match_time = time_box.get_text(strip=True)
                match_name = f"{team_home} - {team_away}"
                
                # ساخت ردیف HTML برای جدول
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
        print(f"Error scraping Varzesh3: {e}")
        # در صورت خطا یک دیتای فیک می‌گذاریم که سایت خالی نماند
        return """
        <tr>
            <td>⚽ فوتبال</td>
            <td>خطا در دریافت اطلاعات</td>
            <td>--:--</td>
            <td>-</td>
        </tr>
        """

# ---------------------------------------------------------
# بخش دوم: تولید محتوا با هوش مصنوعی
# ---------------------------------------------------------
def generate_daily_content():
    prompt = """
    یک مقاله کوتاه و جذاب (حدود 150 کلمه) برای سایت شرط بندی بنویس.
    موضوع باید یکی از این‌ها باشد: استراتژی بازی انفجار، بونوس‌های شرط بندی، یا تحلیل فوتبال.
    فرمت خروجی باید HTML باشد (فقط تگ های <article> و <h2> و <p>).
    از کلمات کلیدی مثل هات بت، رها بت و ضریب بالا استفاده کن.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # مدل اقتصادی و سریع
            messages=[
                {"role": "system", "content": "You are a SEO expert copywriter for a betting site."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error AI: {e}")
        return "<article><h2>خطا در تولید محتوا</h2><p>لطفا بعدا تلاش کنید.</p></article>"

# ---------------------------------------------------------
# بخش سوم: آپدیت فایل HTML اصلی
# ---------------------------------------------------------
def update_html_file():
    # خواندن فایل HTML موجود
    with open("index.html", "r", encoding="utf-8") as file:
        html_content = file.read()

    # دریافت داده‌های تازه
    new_matches = get_todays_matches()
    new_article = generate_daily_content()

    # استفاده از BeautifulSoup برای جایگزینی دقیق در کد HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 1. آپدیت جدول بازی‌ها
    tbody = soup.find(id="matches-body")
    if tbody:
        # تبدیل رشته HTML جدید به تگ‌های سوپ
        new_tbody_soup = BeautifulSoup(new_matches, 'html.parser')
        tbody.clear() # پاک کردن محتوای قبلی
        tbody.append(new_tbody_soup) # اضافه کردن محتوای جدید

    # 2. آپدیت مقاله هوش مصنوعی
    article_section = soup.find(id="ai-articles")
    if article_section:
        new_article_soup = BeautifulSoup(new_article, 'html.parser')
        article_section.clear()
        article_section.append(new_article_soup)

    # ذخیره فایل تغییر یافته
    with open("index.html", "w", encoding="utf-8") as file:
        file.write(str(soup))
    
    print("Website updated successfully!")

if __name__ == "__main__":
    update_html_file()
