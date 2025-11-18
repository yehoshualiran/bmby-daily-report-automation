name: Process Daily Reports

on:
  push:
    paths:
      - 'reports/*.pdf'
  workflow_dispatch:

jobs:
  process-report:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install pdfplumber
        run: |
          pip install pdfplumber
      
      - name: Process report
        env:
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_PASSWORD: ${{ secrets.GMAIL_PASSWORD }}
          TARGET_EMAIL: ${{ secrets.TARGET_EMAIL }}
          PYTHONIOENCODING: utf-8
        run: |
          python process_report.py
