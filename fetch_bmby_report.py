# -*- coding: utf-8 -*-
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

# Environment variables
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
TARGET_EMAIL = os.environ.get('TARGET_EMAIL', 'liran@ozblend.co.il')

def fetch_latest_bmby_email():
    """Connect to Gmail and find the latest Bmby email"""
    print("Connecting to Gmail: {}".format(GMAIL_USER))
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASSWORD)
    mail.select("inbox")
    
    # Search for Bmby emails - no Hebrew in search to avoid encoding issues
    search_criteria = '(FROM "info@bmby.co.il")'
    _, search_data = mail.search(None, search_criteria)
    
    mail_ids = search_data[0].split()
    
    if not mail_ids:
        print("No emails found from Bmby")
        return None
    
    # Get the latest email
    latest_email_id = mail_ids[-1]
    _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    
    email_body = msg_data[0][1]
    email_message = email.message_from_bytes(email_body)
    
    print("Found email from date: {}".format(email_message['Date']))
    
    # Extract email content
    body = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
    else:
        body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
    
    mail.logout()
    return body

def extract_tracking_url(email_body):
    """Extract tracking URL from email"""
    match = re.search(r'https://uclicks\.inforu\.net/[^\s"\'<>]+', email_body)
    if match:
        url = match.group(0)
        print("Found tracking URL: {}".format(url))
        return url
    return None

def download_pdf_with_selenium(tracking_url):
    """Use Selenium to open the link and download the PDF"""
    print("Opening browser...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Set download directory
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
        print("Accessing URL: {}".format(tracking_url))
        driver.get(tracking_url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Try to find and click the button
        try:
            wait = WebDriverWait(driver, 10)
            
            # Try to find link with relevant text
            possible_selectors = [
                "//a[contains(@href, 'pdf')]",
                "//a[contains(@href, 'bmby.com')]",
                "//a[contains(@href, 'MailReports')]"
            ]
            
            clicked = False
            for selector in possible_selectors:
                try:
                    element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    print("Found button/link, clicking...")
                    element.click()
                    clicked = True
                    break
                except:
                    continue
            
            if not clicked:
                print("No specific button found, waiting for auto-redirect...")
            
            # Wait for redirect or download
            time.sleep(5)
            
            # Check if current URL contains PDF
            current_url = driver.current_url
            print("Current URL: {}".format(current_url))
            
            if '.pdf' in current_url or 'bmby.com' in current_url:
                # Download the PDF
                driver.get(current_url)
                time.sleep(3)
                
                pdf_path = os.path.join(download_dir, "report.pdf")
                
                # Check if file was downloaded
                files = os.listdir(download_dir)
                if files:
                    downloaded_file = os.path.join(download_dir, files[0])
                    os.rename(downloaded_file, pdf_path)
                    print("PDF downloaded successfully: {}".format(pdf_path))
                    return pdf_path
                
            print("Failed to download PDF")
            return None
            
        except Exception as e:
            print("Error while trying to download: {}".format(str(e)))
            return None
            
    finally:
        driver.quit()

def send_email_with_attachment(pdf_path):
    """Send the PDF via email"""
    print("Sending email to {}".format(TARGET_EMAIL))
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = 'Daily Activity Report - Bmby Systems'
    
    body = "Attached is the daily activity report from Bmby.\n\nSent automatically by GitHub Actions."
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # Attach the file
    with open(pdf_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename=bmby-daily-report.pdf')
        msg.attach(part)
    
    # Send
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()
    
    print("Email sent successfully!")

def main():
    print("=" * 50)
    print("Starting Bmby report automation")
    print("=" * 50)
    
    # Step 1: Find the email
    email_body = fetch_latest_bmby_email()
    if not email_body:
        print("FAILED: No email found")
        return
    
    # Step 2: Extract the link
    tracking_url = extract_tracking_url(email_body)
    if not tracking_url:
        print("FAILED: No tracking URL found in email")
        return
    
    # Step 3: Download the PDF
    pdf_path = download_pdf_with_selenium(tracking_url)
    if not pdf_path:
        print("FAILED: Could not download PDF")
        return
    
    # Step 4: Send the email
    send_email_with_attachment(pdf_path)
    
    print("=" * 50)
    print("Process completed successfully!")
    print("=" * 50)

if __name__ == "__main__":
    main()
