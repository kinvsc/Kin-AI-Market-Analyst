import os
import feedparser
import yfinance as yf
import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="Kin AI Market Analyst",
    page_icon="🚀",
    layout="centered"
)

st.title("🚀 Kin AI Market Analyst")
st.caption("股票 / Crypto AI 分析工具")

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    api_key = st.text_input("輸入 OpenAI API Key", type="password")

client = OpenAI(api_key=api_key) if api_key else None

ticker = st.text_input(
    "輸入股票 / Crypto Ticker",
    placeholder="例如：NVDA, META, BTC-USD, ETH-USD"
).upper().strip()

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

    # =====================
    # 多來源新聞搜尋
    # =====================

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
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
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
        news_text = "\n".join(titles)

        if is_crypto:
                prompt = f"""
你是一名進取型加密貨幣市場研究員，專注短線至一星期內的市場機會。

請根據以下資料分析 {ticker}。

【市場資料】
市值: {market_cap}

【最新新聞】
以下新聞來自 Google News 搜尋結果，包含 Reuters、CNBC、MarketWatch、Yahoo Finance、財報、Investor Relations 等方向。

{news_text}

分析時請注意：
- Reuters、公司官方 Investor Relations、財報相關消息可信度最高
- CNBC、MarketWatch、Yahoo Finance 屬於一般市場新聞
- Motley Fool、個人評論類來源只作輔助參考
- 不要只根據單一標題下結論

請用廣東話回答，格式如下：

1. 市場現況
2. 利好因素
3. 利淡因素
4. 未來一星期方向
   請使用：
   ★★★★★ 非常看好
   ★★★★☆ 偏向看好
   ★★★☆☆ 中性
   ★★☆☆☆ 偏向看淡
   ★☆☆☆☆ 高風險

5. AI信心評級
   請使用五星制

6. 主要催化劑
7. 最大風險
8. 結論
   請使用五星制

要求：
- 不要用股票財報邏輯分析Crypto
- 重點分析市場情緒、ETF資金流、監管消息、鏈上採用、宏觀利率環境
- 不要保證價格一定上升或下跌
- 不要使用「必買」「必賣」「保證賺錢」
- 每項最多3點
- 總長度控制在300字內
"""
    else:
        prompt = f"""
你是一名進取型股票研究員，專注短線至一星期內的市場機會。

請根據以下資料分析 {ticker}。

【公司基本面】
市值: {market_cap}
Trailing PE: {trailing_pe}
Forward PE: {forward_pe}
Revenue Growth: {revenue_growth}
Earnings Growth: {earnings_growth}

【最新新聞】
{news_text}

請用廣東話回答，格式如下：

1. 公司現況
2. 利好因素
3. 利淡因素
4. 未來一星期方向
   請使用：
   ★★★★★ 非常看好
   ★★★★☆ 偏向看好
   ★★★☆☆ 中性
   ★★☆☆☆ 偏向看淡
   ★☆☆☆☆ 高風險

5. AI信心評級
   請使用五星制

6. 主要催化劑
7. 最大風險
8. 結論
   請使用五星制

要求：
- 分析可以進取，但必須講清楚原因
- 不要保證股價一定上升或下跌
- 不要使用「必買」「必賣」「保證賺錢」
- 每項最多3點
- 總長度控制在300字內
- 像專業股票研究員撰寫
"""

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt
    )

    return titles, response.output_text, response.usage

if st.button("🚀 開始分析"):
    if not api_key:
        st.error("請先輸入 API Key")
    elif ticker == "":
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