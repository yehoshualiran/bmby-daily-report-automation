import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
TARGET_EMAIL = os.environ.get('TARGET_EMAIL', 'liran@ozblend.co.il')

def get_pdf_from_gmail_directly():
    print("Starting browser automation")
    
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
        print("Opening Gmail")
        driver.get("https://mail.google.com")
        time.sleep(2)
        
        print("Logging in")
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "identifierId"))
        )
        email_field.send_keys(GMAIL_USER)
        
        next_button = driver.find_element(By.ID, "identifierNext")
        next_button.click()
        time.sleep(2)
        
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "Passwd"))
        )
        password_field.send_keys(GMAIL_PASSWORD)
        
        next_button = driver.find_element(By.ID, "passwordNext")
        next_button.click()
        time.sleep(5)
        
        print("Searching for Bmby email")
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.send_keys("from:info@bmby.co.il")
        search_box.submit()
        time.sleep(3)
        
        print("Opening latest email")
        emails = driver.find_elements(By.CSS_SELECTOR, "tr.zA")
        if emails:
            emails[0].click()
            time.sleep(3)
            
            print("Looking for PDF link")
            links = driver.find_elements(By.TAG_NAME, "a")
            pdf_link = None
            
            for link in links:
                href = link.get_attribute("href")
                if href and "uclicks.inforu.net" in href:
                    pdf_link = href
                    break
            
            if pdf_link:
                print("Found tracking link, accessing it")
                driver.get(pdf_link)
                time.sleep(5)
                
                current_url = driver.current_url
                print("After redirect: " + current_url[:50])
                
                if ".pdf" in current_url or "bmby.com" in current_url:
                    driver.get(current_url)
                    time.sleep(3)
                    
                    files = os.listdir(download_dir)
                    if files:
                        pdf_path = os.path.join(download_dir, "report.pdf")
                        downloaded = os.path.join(download_dir, files[0])
                        os.rename(downloaded, pdf_path)
                        print("PDF downloaded")
                        return pdf_path
        
        print("Failed to get PDF")
        return None
        
    except Exception as e:
        print("Error: " + str(e)[:100])
        return None
    finally:
        driver.quit()

def send_email_with_attachment(pdf_path):
    print("Sending email")
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = 'Daily Report - Bmby'
    
    body = "Daily report attached"
    msg.attach(MIMEText(body, 'plain'))
    
    with open(pdf_path, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename=bmby-report.pdf')
        msg.attach(part)
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(GMAIL_USER, GMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()
    
    print("Email sent")

def main():
    print("START")
    
    pdf_path = get_pdf_from_gmail_directly()
    if not pdf_path:
        print("FAILED")
        return
    
    send_email_with_attachment(pdf_path)
    print("SUCCESS")

if __name__ == "__main__":
    main()
