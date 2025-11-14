import imaplib
import email
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os

# Environment variables
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
TARGET_EMAIL = os.environ.get('TARGET_EMAIL', 'liran@ozblend.co.il')

def fetch_latest_bmby_email():
    """Connect to Gmail and find the latest Bmby email"""
    print("Connecting to Gmail")
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASSWORD)
    mail.select("inbox")
    
    # Search for emails from Bmby
    _, search_data = mail.search(None, '(FROM "info@bmby.co.il")')
    
    mail_ids = search_data[0].split()
    
    if not mail_ids:
        print("No emails found from Bmby")
        return None
    
    # Get the latest email
    latest_email_id = mail_ids[-1]
    _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    
    email_body = msg_data[0][1]
    email_message = email.message_from_bytes(email_body)
    
    print("Found email from Bmby")
    
    # Extract email content - read as bytes to avoid encoding issues
    body_bytes = b""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/html":
                body_bytes = part.get_payload(decode=True)
                break
    else:
        body_bytes = email_message.get_payload(decode=True)
    
    mail.logout()
    
    # Convert bytes to string, ignoring any problematic characters
    body = body_bytes.decode('utf-8', errors='ignore')
    return body

def extract_tracking_url(email_body):
    """Extract tracking URL from email"""
    match = re.search(r'https://uclicks\.inforu\.net/[^\s"\'<>]+', email_body)
    if match:
        url = match.group(0)
        print("Found tracking URL")
        return url
    return None

def download_pdf_with_selenium(tracking_url):
    """Use Selenium to open the link and download the PDF"""
    print("Opening browser")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
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
        print("Accessing tracking URL")
        driver.get(tracking_url)
        time.sleep(5)
        
        current_url = driver.current_url
        print("Current URL after redirect: " + current_url[:50])
        
        if '.pdf' in current_url or 'bmby.com' in current_url:
            driver.get(current_url)
            time.sleep(3)
            
            pdf_path = os.path.join(download_dir, "report.pdf")
            files = os.listdir(download_dir)
            
            if files:
                downloaded_file = os.path.join(download_dir, files[0])
                if os.path.exists(downloaded_file):
                    os.rename(downloaded_file, pdf_path)
                    print("PDF downloaded successfully")
                    return pdf_path
        
        print("Failed to download PDF")
        return None
        
    except Exception as e:
        print("Error: " + str(e)[:100])
        return None
    finally:
        driver.quit()

def send_email_with_attachment(pdf_path):
    """Send the PDF via email"""
    print("Sending email")
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = 'Daily Activity Report - Bmby Systems'
    
    body = "Attached is the daily activity report from Bmby."
    msg.attach(MIMEText(body, 'plain'))
    
    with open(pdf_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename=bmby-daily-report.pdf')
        msg.attach(part)
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()
    
    print("Email sent successfully")

def main():
    print("Starting Bmby report automation")
    
    email_body = fetch_latest_bmby_email()
    if not email_body:
        print("FAILED: No email found")
        return
    
    tracking_url = extract_tracking_url(email_body)
    if not tracking_url:
        print("FAILED: No tracking URL found")
        return
    
    pdf_path = download_pdf_with_selenium(tracking_url)
    if not pdf_path:
        print("FAILED: Could not download PDF")
        return
    
    send_email_with_attachment(pdf_path)
    print("Process completed successfully")

if __name__ == "__main__":
    main()
