import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# Try to import pdfplumber
try:
    import pdfplumber
except ImportError:
    print("pdfplumber not installed")
    sys.exit(1)

GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
TARGET_EMAIL = os.environ.get('TARGET_EMAIL', 'liran@ozblend.co.il')

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber"""
    print(f"Reading PDF: {pdf_path}")
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        print(f"Extracted {len(text)} characters")
        return text
    except Exception as e:
        print(f"Error: {e}")
        return None

def parse_report_simple(text):
    """Simple parsing - count key metrics"""
    summary = {
        'total_meetings': 0,
        'total_tasks': 0,
        'new_leads': 0
    }
    
    lines = text.split('\n')
    
    # Count specific indicators
    for line in lines:
        # Count meetings
        if 'פגישה' in line or 'פגישות' in line:
            nums = [int(s) for s in line.split() if s.isdigit()]
            if nums:
                summary['total_meetings'] += nums[0]
        
        # Count new leads
        if 'מתעניין חדש' in line:
            summary['new_leads'] += 1
        
        # Count tasks
        if 'משימה' in line or 'משימות' in line:
            nums = [int(s) for s in line.split() if s.isdigit()]
            if nums:
                summary['total_tasks'] += nums[0]
    
    return summary

def create_simple_email(summary, report_date):
    """Create simple HTML email"""
    
    html = f"""
    <html>
    <body style="font-family: Arial; direction: rtl;">
        <h2 style="color: #2196F3;">דוח יומי - {report_date}</h2>
        
        <div style="background: #f5f5f5; padding: 20px; border-radius: 5px;">
            <h3>סיכום מהיר:</h3>
            <ul style="font-size: 16px; line-height: 1.8;">
                <li><strong>פגישות:</strong> {summary['total_meetings']}</li>
                <li><strong>משימות:</strong> {summary['total_tasks']}</li>
                <li><strong>לידים חדשים:</strong> {summary['new_leads']}</li>
            </ul>
        </div>
        
        <p style="margin-top: 20px; color: #666;">
            הדוח המלא נמצא בקובץ המקורי
        </p>
    </body>
    </html>
    """
    
    return html

def send_email(summary, report_date):
    """Send email with summary"""
    print("Sending email...")
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = f'דוח יומי במבי - {report_date}'
    
    html = create_simple_email(summary, report_date)
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("SUCCESS - Email sent!")
    except Exception as e:
        print(f"Email error: {e}")

def main():
    print("=== Starting Report Processor ===")
    
    # Find PDF
    reports_dir = "reports"
    pdfs = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
    
    if not pdfs:
        print("No PDF found")
        return
    
    latest = max(pdfs, key=lambda f: os.path.getmtime(os.path.join(reports_dir, f)))
    pdf_path = os.path.join(reports_dir, latest)
    
    print(f"Processing: {latest}")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("Failed to extract text")
        return
    
    # Parse
    summary = parse_report_simple(text)
    print(f"Summary: {summary}")
    
    # Send
    report_date = datetime.now().strftime("%d/%m/%Y")
    send_email(summary, report_date)
    
    print("=== DONE ===")

if __name__ == "__main__":
    main()
