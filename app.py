import os
from urllib.parse import quote_plus

import feedparser
import yfinance as yf
import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="Kin AI",
    page_icon="🚀",
    layout="centered"
)

st.title("🚀 Kin AI")
st.caption("AI Market Analyst v3.1 - Watchlist")

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

# =====================
# Watchlist session state
# =====================

if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["NVDA", "META", "TSM", "BTC-USD"]

# =====================
# Functions
# =====================

def get_news(ticker):
    news_queries = [
        f"{ticker} Reuters stock news",
        f"{ticker} CNBC stock news",
        f"{ticker} MarketWatch stock news",
        f"{ticker} Yahoo Finance stock news",
        f"{ticker} earnings guidance",
        f"{ticker} investor relations earnings",
        f"{ticker} market news",
    ]

    titles = []
    seen_titles = set()

    for query in news_queries:
        safe_query = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={safe_query}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        for article in feed.entries[:2]:
            title = article.title

            if title not in seen_titles:
                titles.append(title)
                seen_titles.add(title)

            if len(titles) >= 10:
                break

        if len(titles) >= 10:
            break

    return titles


def analyze(ticker):
    is_crypto = "-USD" in ticker

    asset = yf.Ticker(ticker)

    try:
        info = asset.info
    except Exception:
        info = {}

    market_cap = info.get("marketCap", "N/A")
    trailing_pe = info.get("trailingPE", "N/A")
    forward_pe = info.get("forwardPE", "N/A")
    revenue_growth = info.get("revenueGrowth", "N/A")
    earnings_growth = info.get("earningsGrowth", "N/A")

    titles = get_news(ticker)
    news_text = "\n".join(titles)

    if is_crypto:
        prompt = f"""
你是一名進取型加密貨幣市場研究員，專注短線至下一交易日/未來一星期的市場機會。

請根據以下資料分析 {ticker}。

【市場資料】
市值: {market_cap}

【最新新聞】
以下新聞來自 Google News 搜尋結果，包含 Reuters、CNBC、MarketWatch、Yahoo Finance、官方消息等方向。

{news_text}

分析時請注意：
- Reuters、官方消息、財報相關消息可信度最高
- CNBC、MarketWatch、Yahoo Finance 屬於一般市場新聞
- 不要只根據單一標題下結論

請用廣東話回答，格式如下：

1. 市場現況
2. 利好因素
3. 利淡因素
4. 未來一星期方向
請使用五星制：
★★★★★ 非常看好
★★★★☆ 偏向看好
★★★☆☆ 中性
★★☆☆☆ 偏向看淡
★☆☆☆☆ 高風險

5. AI信心評級
6. 主要催化劑
7. 最大風險

8. 下一交易日升跌機率估算
- 上升機率：__%
- 下跌機率：__%
- 震盪機率：__%

9. 預估升跌幅範圍
- 上升情境：+__% 至 +__%
- 下跌情境：-__% 至 -__%
- 最可能區間：__% 至 __%

10. 機率判斷理由
最多3點

11. 結論
請使用五星制

要求：
- 不要用股票財報邏輯分析 Crypto
- 不要保證價格一定上升或下跌
- 不要使用「必買」「必賣」「保證賺錢」
- 所有機率都只是根據目前公開資訊的主觀估算
- 每項最多3點
- 總長度控制在450字內
"""
    else:
        prompt = f"""
你是一名進取型股票研究員，專注短線至下一交易日/未來一星期的市場機會。

請根據以下資料分析 {ticker}。

【公司基本面】
市值: {market_cap}
Trailing PE: {trailing_pe}
Forward PE: {forward_pe}
Revenue Growth: {revenue_growth}
Earnings Growth: {earnings_growth}

【最新新聞】
以下新聞來自 Google News 搜尋結果，包含 Reuters、CNBC、MarketWatch、Yahoo Finance、財報、Investor Relations 等方向。

{news_text}

分析時請注意：
- Reuters、公司官方 Investor Relations、財報相關消息可信度最高
- CNBC、MarketWatch、Yahoo Finance 屬於一般市場新聞
- 不要只根據單一標題下結論

請用廣東話回答，格式如下：

1. 公司現況
2. 利好因素
3. 利淡因素
4. 未來一星期方向
請使用五星制：
★★★★★ 非常看好
★★★★☆ 偏向看好
★★★☆☆ 中性
★★☆☆☆ 偏向看淡
★☆☆☆☆ 高風險

5. AI信心評級
6. 主要催化劑
7. 最大風險

8. 下一交易日升跌機率估算
- 上升機率：__%
- 下跌機率：__%
- 震盪機率：__%

9. 預估升跌幅範圍
- 上升情境：+__% 至 +__%
- 下跌情境：-__% 至 -__%
- 最可能區間：__% 至 __%

10. 機率判斷理由
最多3點

11. 結論
請使用五星制

要求：
- 分析可以進取，但必須講清楚原因
- 不要保證股價一定上升或下跌
- 不要使用「必買」「必賣」「保證賺錢」
- 所有機率都只是根據目前公開資訊的主觀估算
- 每項最多3點
- 總長度控制在450字內
- 像專業股票研究員撰寫
"""

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt
    )

    return titles, response.output_text, response.usage


# =====================
# Watchlist UI
# =====================

st.subheader("⭐ 我的 Watchlist")

new_ticker = st.text_input(
    "新增 Ticker",
    placeholder="例如：NVDA 或 BTC-USD"
).upper().strip()

col1, col2 = st.columns(2)

with col1:
    if st.button("➕ 加入 Watchlist"):
        if new_ticker and new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
            st.success(f"已加入 {new_ticker}")

with col2:
    if st.button("🧹 清空 Watchlist"):
        st.session_state.watchlist = []
        st.warning("Watchlist 已清空")

if st.session_state.watchlist:
    remove_ticker = st.selectbox(
        "刪除 Ticker",
        st.session_state.watchlist
    )

    if st.button("❌ 刪除選中 Ticker"):
        st.session_state.watchlist.remove(remove_ticker)
        st.success(f"已刪除 {remove_ticker}")

    st.write("目前 Watchlist：")
    st.write(", ".join(st.session_state.watchlist))
else:
    st.info("Watchlist 目前是空的。")

st.divider()

# =====================
# Single Analysis
# =====================

st.subheader("🔍 單隻分析")

ticker = st.text_input(
    "輸入股票 / Crypto Ticker",
    placeholder="例如：NVDA, META, BTC-USD, ETH-USD",
    key="single_ticker"
).upper().strip()

if st.button("🚀 分析單隻"):
    if ticker == "":
        st.warning("請輸入 ticker，例如 NVDA 或 BTC-USD")
    else:
        with st.spinner(f"AI 正在分析 {ticker}..."):
            titles, result, usage = analyze(ticker)

        st.subheader(f"📌 {ticker} 最新新聞")
        for title in titles:
            st.write("•", title)

        st.divider()

        st.subheader("🤖 AI 分析報告")
        st.markdown(result)

        st.divider()

        st.caption(
            f"Token Usage — Input: {usage.input_tokens} | "
            f"Output: {usage.output_tokens} | Total: {usage.total_tokens}"
        )

st.divider()

# =====================
# Watchlist Analysis
# =====================

st.subheader("📊 一鍵分析 Watchlist")

if st.button("🚀 分析整個 Watchlist"):
    if not st.session_state.watchlist:
        st.warning("Watchlist 是空的，請先加入 ticker。")
    else:
        for ticker in st.session_state.watchlist:
            with st.spinner(f"AI 正在分析 {ticker}..."):
                titles, result, usage = analyze(ticker)

            st.markdown(f"## 📌 {ticker}")
            st.markdown(result)

            with st.expander(f"{ticker} 最新新聞"):
                for title in titles:
                    st.write("•", title)

            st.caption(
                f"Token Usage — Input: {usage.input_tokens} | "
                f"Output: {usage.output_tokens} | Total: {usage.total_tokens}"
            )

            st.divider()