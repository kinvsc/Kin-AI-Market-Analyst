from datetime import datetime
import hashlib
import requests
import streamlit as st

try:
    GOOGLE_MEMORY_URL = st.secrets["GOOGLE_MEMORY_URL"]
except Exception:
    from config import GOOGLE_MEMORY_URL

def make_hash(ticker, summary):
    raw = f"{ticker}-{summary}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def save_memory(ticker, memory_type, source, score, summary, version="v4.6", entry_price=None):
    memory_hash = make_hash(ticker, summary)

    payload = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticker": ticker,
        "memory_type": memory_type,
        "source": source,
        "score": score,
        "summary": summary,
        "hash": memory_hash,
        "version": version,
        "entry_price": entry_price
    }

    requests.post(
        GOOGLE_MEMORY_URL,
        json=payload,
        timeout=10
    )

    return memory_hash

def load_memory():
    
    response = requests.get(
        GOOGLE_MEMORY_URL,
        timeout=10
    )

    response.raise_for_status()

    return response.json()

def update_validation(hash_value, current_price, return_pct, status):
    payload = {
        "action": "update_validation",
        "hash": hash_value,
        "current_price": current_price,
        "return_pct": return_pct,
        "validation_status": status,
        "validated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    response = requests.post(
        GOOGLE_MEMORY_URL,
        json=payload,
        timeout=10
    )

    response.raise_for_status()

    return response.json()