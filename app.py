import os
import re
import json
from urllib.parse import quote_plus

import feedparser
import yfinance as yf
import streamlit as st
from openai import OpenAI


# =====================
# Page setup
# =====================

st.set_page_config(
    page_title="Kin AI",
    page_icon="🚀",
    layout="centered"
)

st.title("🚀 Kin AI")
st.caption("Fund Manager Decision Engine v4")


# =====================
# API Key
# =====================

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


# =====================
# Helper functions
# =====================

def clean_tickers(text):
    text = text.replace("\n", ",").replace(" ", ",")
    tickers = []

    for item in text.split(","):
        ticker = item.upper().strip()
        if ticker and ticker not in tickers:
            tickers.append(ticker)

    return tickers


def get_news(ticker):
    queries = [
        f"{ticker} Reuters market news",
        f"{ticker} CNBC market news",
        f"{ticker} MarketWatch market news",
        f"{ticker} Yahoo Finance news",
        f"{ticker} earnings guidance",
        f"{ticker} investor relations earnings",
        f"{ticker} stock market news",
    ]

    titles = []
    seen = set()

    for query in queries:
        safe_query = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={safe_query}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        for article in feed.entries[:2]:
            title = article.title

            if title not in seen:
                titles.append(title)
                seen.add(title)

            if len(titles) >= 8:
                break

        if len(titles) >= 8:
            break

    return titles


def get_basic_data(ticker):
    asset = yf.Ticker(ticker)

    try:
        info = asset.info
    except Exception:
        info = {}

    return {
        "market_cap": info.get("marketCap", "N/A"),
        "trailing_pe": info.get("trailingPE", "N/A"),
        "forward_pe": info.get("forwardPE", "N/A"),
        "revenue_growth": info.get("revenueGrowth", "N/A"),
        "earnings_growth": info.get("earningsGrowth", "N/A"),
    }


def build_summary(ticker):
    is_crypto = "-USD" in ticker
    data = get_basic_data(ticker)
    news = get_news(ticker)

    news_text = "\n".join(news)

    summary = f"""
Ticker: {ticker}
Asset Type: {"Crypto" if is_crypto else "Stock"}

Market Cap: {data["market_cap"]}
Trailing PE: {data["trailing_pe"]}
Forward PE: {data["forward_pe"]}
Revenue Growth: {data["revenue_growth"]}
Earnings Growth: {data["earnings_growth"]}

News:
{news_text}
"""

    return summary, news


def extract_json(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        return None

    return None


def fund_manager_decision(tickers):
    summaries = []
    all_news = {}

    for ticker in tickers:
        summary, news = build_summary(ticker)
        summaries.append(summary)
        all_news[ticker] = news

    combined_data = "\n\n====================\n\n".join(summaries)

    prompt = f"""
你是一名管理超過100億美元資產的進取型基金經理。

你的工作不是寫分析文章，而是作出投資決策。

你需要根據：
- 最新新聞
- 財報及基本面
- 估值
- 市場情緒
- 催化劑
- 風險

判斷未來1至5個交易日的機會。

以下是候選標的資料：

{combined_data}

請直接輸出 JSON，不要輸出任何 JSON 以外文字。

JSON 格式必須如下：

{{
  "top_pick": "NVDA",
  "market_decision": "BUY / HOLD / AVOID / STAY CASH",
  "summary": "一句總結，30字內",
  "items": [
    {{
      "ticker": "NVDA",
      "action": "BUY / HOLD / AVOID",
      "ai_score": 0,
      "success_probability": 0,
      "risk_probability": 0,
      "expected_move": "+0% ~ +0%",
      "confidence": 0,
      "reason": "一句原因，30字內",
      "buy_zone": "價格或N/A",
      "target_1": "價格或N/A",
      "target_2": "價格或N/A",
      "stop_loss": "價格或N/A",
      "details": {{
        "bullish": ["最多3點"],
        "bearish": ["最多3點"],
        "catalysts": ["最多3點"],
        "risks": ["最多3點"]
      }}
    }}
  ],
  "avoid_list": ["ticker"],
  "cash_warning": "如果今日不適合出手，寫原因；否則寫N/A"
}}

規則：
- action 只能是 BUY / HOLD / AVOID
- ai_score 用 0-100
- success_probability 用 0-100
- risk_probability 用 0-100
- confidence 用 0-100
- 如果沒有明顯機會，可以 top_pick 寫 "NONE"，market_decision 寫 "STAY CASH"
- 不要保證升跌
- 不要使用「必賺」「一定升」「穩賺」
- 機率只是根據目前公開資訊的主觀估算
- 回答要果斷
- 短線優先，重點是未來1至5個交易日
"""

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt
    )

    parsed = extract_json(response.output_text)

    return parsed, response.output_text, response.usage, all_news


def action_color(action):
    if action == "BUY":
        return "🟢"
    if action == "HOLD":
        return "🟡"
    if action == "AVOID":
        return "🔴"
    return "⚪"


def display_item(item, rank=None):
    ticker = item.get("ticker", "N/A")
    action = item.get("action", "N/A")
    score = item.get("ai_score", "N/A")
    success = item.get("success_probability", "N/A")
    risk = item.get("risk_probability", "N/A")
    move = item.get("expected_move", "N/A")
    confidence = item.get("confidence", "N/A")
    reason = item.get("reason", "N/A")

    title = f"{ticker}"

    if rank == 1:
        title = f"🥇 {ticker}"
    elif rank == 2:
        title = f"🥈 {ticker}"
    elif rank == 3:
        title = f"🥉 {ticker}"

    st.markdown(f"## {title}")
    st.markdown(f"### {action_color(action)} {action}")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("AI Score", f"{score}/100")
        st.metric("上升機率", f"{success}%")
        st.metric("預估波動", move)

    with col2:
        st.metric("風險機率", f"{risk}%")
        st.metric("信心指數", f"{confidence}%")
        st.metric("止蝕位", item.get("stop_loss", "N/A"))

    st.info(reason)

    with st.expander("📄 詳細分析"):
        st.write("買入區：", item.get("buy_zone", "N/A"))
        st.write("第一目標價：", item.get("target_1", "N/A"))
        st.write("第二目標價：", item.get("target_2", "N/A"))

        details = item.get("details", {})

        st.markdown("#### 利好因素")
        for x in details.get("bullish", []):
            st.write("•", x)

        st.markdown("#### 利淡因素")
        for x in details.get("bearish", []):
            st.write("•", x)

        st.markdown("#### 催化劑")
        for x in details.get("catalysts", []):
            st.write("•", x)

        st.markdown("#### 最大風險")
        for x in details.get("risks", []):
            st.write("•", x)


# =====================
# UI
# =====================

st.subheader("🎯 Fund Manager Input")

tickers_input = st.text_area(
    "輸入一隻或多隻 Ticker",
    value="",
    height=120,
    placeholder="例如：NVDA, META, TSM, BTC-USD"
)

tickers = clean_tickers(tickers_input)

if tickers:
    st.write("目前分析名單：")
    st.write(", ".join(tickers))

st.divider()

if st.button("🚀 開始基金經理決策"):
    if not tickers:
        st.warning("請輸入至少一隻 ticker。")
    else:
        with st.spinner("Kin AI 基金經理正在決策..."):
            parsed, raw_text, usage, all_news = fund_manager_decision(tickers)

        if parsed is None:
            st.error("AI 回覆格式解析失敗，以下是原始回覆：")
            st.write(raw_text)
        else:
            st.subheader("🚀 今日決策")

            market_decision = parsed.get("market_decision", "N/A")
            top_pick = parsed.get("top_pick", "N/A")
            summary = parsed.get("summary", "N/A")
            cash_warning = parsed.get("cash_warning", "N/A")

            if market_decision == "BUY":
                st.success(f"🟢 Market Decision: {market_decision}")
            elif market_decision == "HOLD":
                st.warning(f"🟡 Market Decision: {market_decision}")
            elif market_decision == "AVOID":
                st.error(f"🔴 Market Decision: {market_decision}")
            elif market_decision == "STAY CASH":
                st.error("⚪ Market Decision: STAY CASH")
            else:
                st.info(f"Market Decision: {market_decision}")

            st.markdown(f"### 🏆 Top Pick: {top_pick}")
            st.info(summary)

            if cash_warning and cash_warning != "N/A":
                st.warning(cash_warning)

            st.divider()

            items = parsed.get("items", [])

            try:
                items = sorted(
                    items,
                    key=lambda x: int(x.get("ai_score", 0)),
                    reverse=True
                )
            except Exception:
                pass

            st.subheader("📊 Ranking")

            for i, item in enumerate(items, start=1):
                display_item(item, rank=i)
                st.divider()

            with st.expander("📰 新聞來源"):
                for ticker, news in all_news.items():
                    st.markdown(f"### {ticker}")
                    for title in news:
                        st.write("•", title)

            st.caption(
                f"Token Usage — Input: {usage.input_tokens} | "
                f"Output: {usage.output_tokens} | Total: {usage.total_tokens}"
            )