from datetime import datetime
import hashlib
import requests
import streamlit as st


def make_hash(ticker, summary):
    raw = f"{ticker}-{summary}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def save_memory(ticker, memory_type, source, score, summary, version="v4.4"):

    memory_hash = make_hash(ticker, summary)

    payload = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticker": ticker,
        "memory_type": memory_type,
        "source": source,
        "score": score,
        "summary": summary,
        "hash": memory_hash,
        "version": version
    }

    requests.post(
        st.secrets["GOOGLE_MEMORY_URL"],
        json=payload,
        timeout=10
    )

    return memory_hash