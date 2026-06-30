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
st.caption("Fund Manager Mode v4")

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

tickers_input = st.text_area(
    "輸入 Watchlist / Tickers",
    value="NVDA, META, TSM, AMD, PLTR, BTC-USD, ETH-USD",
    height=100,
    placeholder="例如：NVDA, META, TSM, BTC-USD"
)


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


def build_stock_summary(ticker):
    is_crypto = "-USD" in ticker
    data = get_basic_data(ticker)
    news = get_news(ticker)

    summary = f"""
Ticker: {ticker}
Asset Type: {"Crypto" if is_crypto else "Stock"}

Market Cap: {data["market_cap"]}
Trailing PE: {data["trailing_pe"]}
Forward PE: {data["forward_pe"]}
Revenue Growth: {data["revenue_growth"]}
Earnings Growth: {data["earnings_growth"]}

News:
{chr(10).join(news)}
"""
    return summary, news


def fund_manager_analysis(tickers):
    summaries = []
    all_news = {}

    for ticker in tickers:
        summary, news = build_stock_summary(ticker)
        summaries.append(summary)
        all_news[ticker] = news

    combined_data = "\n\n====================\n\n".join(summaries)

    prompt = f"""
你是一名進取型基金經理，專注短線至未來一星期的市場機會。

你每天只能挑選少數最值得研究或部署的標的。
請根據以下多隻股票 / Crypto 的新聞、基本面、市場情緒，直接做投資決策。

【資料】
{combined_data}

請用廣東話輸出。

格式必須如下：

# 🚀 今日基金經理決策

## 🥇 Top Pick
Ticker:
Action: BUY / HOLD / AVOID
AI Score: __/100
上升機率: __%
下跌機率: __%
預估升幅: +__% 至 +__%
預估跌幅: -__% 至 -__%
信心評級: ★★★★★ / ★★★★☆ / ★★★☆☆ / ★★☆☆☆ / ★☆☆☆☆
一句原因:

## 📊 排名
請用表格：

| 排名 | Ticker | Action | AI Score | 上升機率 | 預估波動 | 一句原因 |

## 🟢 BUY List
列出最值得研究的標的，最多3隻。

## 🟡 HOLD List
列出中性或可觀察標的。

## 🔴 AVOID List
列出暫時不建議參與標的。

## ⚠️ 最大市場風險
最多3點。

要求：
- 可以果斷，但必須有理由
- 不要保證升跌
- 不要使用「必賺」「一定升」「必買」
- 如果沒有明顯機會，可以說「今日沒有強烈買入機會」
- 所有機率都是根據目前公開資訊的主觀估算
- 回答要簡潔，方便手機快速閱讀
"""

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt
    )

    return response.output_text, response.usage, all_news


tickers = clean_tickers(tickers_input)

st.write("目前分析名單：")
st.write(", ".join(tickers))

if st.button("🚀 基金經理分析"):
    if not tickers:
        st.warning("請輸入至少一隻 ticker。")
    else:
        with st.spinner("Kin AI 基金經理正在分析..."):
            result, usage, all_news = fund_manager_analysis(tickers)

        st.subheader("🤖 Fund Manager Decision")
        st.markdown(result)

        st.divider()

        with st.expander("📰 查看新聞來源"):
            for ticker, news in all_news.items():
                st.markdown(f"### {ticker}")
                for title in news:
                    st.write("•", title)

        st.caption(
            f"Token Usage — Input: {usage.input_tokens} | "
            f"Output: {usage.output_tokens} | Total: {usage.total_tokens}"
        )