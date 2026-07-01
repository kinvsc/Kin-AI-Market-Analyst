from datetime import datetime
import hashlib
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SHEET_NAME = "14mnieuDpeoMGf693uCLzR8e7oK1nsalbQS-GINBCOYo"
WORKSHEET_NAME = "Sheet1"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["GOOGLE_SERVICE_ACCOUNT"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
    return sheet

def make_hash(ticker, summary):
    raw = f"{ticker}-{summary}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def save_memory(ticker, memory_type, source, score, summary, version="v4.4"):
    sheet = get_sheet()

    memory_hash = make_hash(ticker, summary)

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ticker,
        memory_type,
        source,
        score,
        summary,
        memory_hash,
        version
    ]

    sheet.append_row(row)
    return memory_hash