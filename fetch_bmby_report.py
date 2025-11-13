import imaplib
import email
from email.header import decode_header
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
from datetime import datetime, timedelta

# הגדרות מתוך environment variables
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
TARGET_EMAIL = os.environ.get('TARGET_EMAIL', 'liran@ozblend.co.il')

def fetch_latest_bmby_email():
    """מחבר ל-Gmail ומוצא את המייל האחרון מבמבי"""
    print(f"🔍 מתחבר ל-Gmail: {GMAIL_USER}")
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASSWORD)
    mail.select("inbox")
    
    # חיפוש מיילים מבמבי מהיום האחרון
    search_criteria = '(FROM "info@bmby.co.il" SUBJECT "דוח פעילות יומי")'
    _, search_data = mail.search(None, search_criteria)
    
    mail_ids = search_data[0].split()
    
    if not mail_ids:
        print("❌ לא נמצאו מיילים מבמבי")
        return None
    
    # לקיחת המייל האחרון
    latest_email_id = mail_ids[-1]
    _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    
    email_body = msg_data[0][1]
    email_message = email.message_from_bytes(email_body)
    
    print(f"✅ נמצא מייל מתאריך: {email_message['Date']}")
    
    # חילוץ תוכן המייל
    body = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True).decode()
                break
    else:
        body = email_message.get_payload(decode=True).decode()
    
    mail.logout()
    return body

def extract_tracking_url(email_body):
    """מחלץ את קישור המעקב מהמייל"""
    match = re.search(r'https://uclicks\.inforu\.net/[^\s"\'<>]+', email_body)
    if match:
        url = match.group(0)
        print(f"🔗 נמצא קישור מעקב: {url}")
        return url
    return None

def download_pdf_with_selenium(tracking_url):
    """משתמש ב-Selenium כדי לפתוח את הקישור ולהוריד את ה-PDF"""
    print("🌐 פותח דפדפן...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # הגדרת תיקיית הורדות
    download_dir = "/tmp/bmby_downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"📄 ניגש לקישור: {tracking_url}")
        driver.get(tracking_url)
        
        # המתנה לטעינת הדף
        time.sleep(3)
        
        # חיפוש כפתור "לצפייה"
        try:
            # ניסיון למצוא קישור או כפתור
            wait = WebDriverWait(driver, 10)
            
            # נסה למצוא קישור עם טקסט רלוונטי
            possible_selectors = [
                "//a[contains(text(), 'לצפייה')]",
                "//a[contains(text(), 'לחץ כאן')]",
                "//a[contains(@href, 'pdf')]",
                "//a[contains(@href, 'bmby.com')]"
            ]
            
            clicked = False
            for selector in possible_selectors:
                try:
                    element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    print(f"✅ נמצא כפתור/קישור, לוחץ...")
                    element.click()
                    clicked = True
                    break
                except:
                    continue
            
            if not clicked:
                print("⚠️ לא נמצא כפתור ספציפי, ממתין ל-redirect אוטומטי...")
            
            # המתנה ל-redirect או הורדה
            time.sleep(5)
            
            # בדיקה אם יש PDF ב-URL הנוכחי
            current_url = driver.current_url
            print(f"🔗 URL נוכחי: {current_url}")
            
            if '.pdf' in current_url or 'bmby.com' in current_url:
                # הורדת ה-PDF
                pdf_response = driver.execute_script("""
                    var xhr = new XMLHttpRequest();
                    xhr.open('GET', arguments[0], false);
                    xhr.send();
                    return xhr.responseText;
                """, current_url)
                
                pdf_path = os.path.join(download_dir, "דוח-יומי-bmby.pdf")
                
                # שמירת הקובץ
                if '.pdf' in current_url:
                    driver.get(current_url)
                    time.sleep(3)
                    
                    # בדיקה אם הקובץ הורד
                    files = os.listdir(download_dir)
                    if files:
                        downloaded_file = os.path.join(download_dir, files[0])
                        os.rename(downloaded_file, pdf_path)
                        print(f"✅ PDF הורד בהצלחה: {pdf_path}")
                        return pdf_path
                
            print("❌ לא הצלחנו להוריד את ה-PDF")
            return None
            
        except Exception as e:
            print(f"❌ שגיאה בניסיון להוריד: {str(e)}")
            return None
            
    finally:
        driver.quit()

def send_email_with_attachment(pdf_path):
    """שולח את ה-PDF במייל"""
    print(f"📧 שולח מייל ל-{TARGET_EMAIL}")
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = 'דוח פעילות יומי – במבי מערכות תוכנה'
    
    body = "מצורף דוח הפעילות היומי מבמבי.\n\nנשלח אוטומטית על ידי GitHub Actions."
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # צירוף הקובץ
    with open(pdf_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename=דוח-יומי-bmby.pdf')
        msg.attach(part)
    
    # שליחה
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()
    
    print("✅ המייל נשלח בהצלחה!")

def main():
    print("=" * 50)
    print("🚀 מתחיל תהליך העברת דוח במבי")
    print("=" * 50)
    
    # שלב 1: מציאת המייל
    email_body = fetch_latest_bmby_email()
    if not email_body:
        print("❌ כישלון: לא נמצא מייל")
        return
    
    # שלב 2: חילוץ הקישור
    tracking_url = extract_tracking_url(email_body)
    if not tracking_url:
        print("❌ כישלון: לא נמצא קישור במייל")
        return
    
    # שלב 3: הורדת ה-PDF
    pdf_path = download_pdf_with_selenium(tracking_url)
    if not pdf_path:
        print("❌ כישלון: לא הצלחנו להוריד את ה-PDF")
        return
    
    # שלב 4: שליחת המייל
    send_email_with_attachment(pdf_path)
    
    print("=" * 50)
    print("🎉 התהליך הושלם בהצלחה!")
    print("=" * 50)

if __name__ == "__main__":
    main()
