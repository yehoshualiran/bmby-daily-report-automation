import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
try:
    import PyPDF2
except ImportError:
    print("PyPDF2 not installed")
    sys.exit(1)

GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
TARGET_EMAIL = os.environ.get('TARGET_EMAIL', 'liran@ozblend.co.il')

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    print(f"Reading PDF: {pdf_path}")
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

def parse_report(text):
    """Parse the report and extract key information"""
    summary = {
        'total_meetings': 0,
        'total_tasks': 0,
        'new_customers': 0,
        'urgent_tasks': []
    }
    
    lines = text.split('\n')
    
    # Count key metrics
    for line in lines:
        if 'פגישות שבוצעו' in line or 'פגישה' in line:
            try:
                # Try to extract numbers
                nums = [int(s) for s in line.split() if s.isdigit()]
                if nums:
                    summary['total_meetings'] += sum(nums)
            except:
                pass
        
        if 'משימות' in line:
            try:
                nums = [int(s) for s in line.split() if s.isdigit()]
                if nums:
                    summary['total_tasks'] += sum(nums)
            except:
                pass
        
        if 'מתעניין חדש' in line or 'לקוח חדש' in line:
            summary['new_customers'] += 1
    
    return summary

def create_email_body(summary, report_date):
    """Create a formatted email with the summary"""
    
    html = f"""
    <html dir="rtl">
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; direction: rtl; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .summary-box {{ background-color: #f9f9f9; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .metric {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
            .label {{ font-size: 14px; color: #666; }}
            .footer {{ margin-top: 30px; padding: 10px; background-color: #f0f0f0; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 סיכום דוח יומי - במבי</h1>
            <p>תאריך: {report_date}</p>
        </div>
        
        <div class="summary-box">
            <h2>📈 נתונים עיקריים:</h2>
            
            <p>
                <span class="metric">{summary['total_meetings']}</span><br>
                <span class="label">פגישות שבוצעו היום</span>
            </p>
            
            <p>
                <span class="metric">{summary['total_tasks']}</span><br>
                <span class="label">משימות בטיפול</span>
            </p>
            
            <p>
                <span class="metric">{summary['new_customers']}</span><br>
                <span class="label">לקוחות חדשים</span>
            </p>
        </div>
        
        <div class="footer">
            <p>נשלח אוטומטית על ידי מערכת ניהול דוחות במבי</p>
            <p>📱 לצפייה בדוח המלא - ראה קובץ מצורף במייל המקורי</p>
        </div>
    </body>
    </html>
    """
    
    return html

def send_summary_email(summary, report_date):
    """Send the summary via email"""
    print("Sending summary email...")
    
    msg = MIMEMultipart('alternative')
    msg['From'] = GMAIL_USER
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = f'סיכום דוח יומי במבי - {report_date}'
    
    html_body = create_email_body(summary, report_date)
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    print("Starting report processor...")
    
    # Find the latest PDF in reports folder
    reports_dir = "reports"
    pdf_files = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found in reports folder")
        return
    
    # Get the most recent file
    latest_pdf = max(pdf_files, key=lambda f: os.path.getmtime(os.path.join(reports_dir, f)))
    pdf_path = os.path.join(reports_dir, latest_pdf)
    
    print(f"Processing: {latest_pdf}")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("Failed to extract text from PDF")
        return
    
    # Parse report
    summary = parse_report(text)
    
    # Get report date (from filename or current date)
    report_date = datetime.now().strftime("%d/%m/%Y")
    
    # Send email
    send_summary_email(summary, report_date)
    
    print("Processing complete!")

if __name__ == "__main__":
    main()
