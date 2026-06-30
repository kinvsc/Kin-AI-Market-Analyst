import os
import re
import json
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
st.caption("Fund Manager Decision Engine v4.1 - Intelligence Engine")


try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


SOURCE_WEIGHTS = {
    "Reuters": 10,
    "NVIDIA Newsroom": 10,
    "Investor Relations": 10,
    "SEC": 10,
    "CNBC": 9,
    "MarketWatch": 8,
    "Barron's": 8,
    "The Wall Street Journal": 8,
    "Benzinga": 7,
    "TipRanks": 7,
    "Zacks": 6,
    "Yahoo Finance": 5,
    "Investing.com": 5,
    "Motley Fool": 3,
}


def clean_tickers(text):
    text = text.replace("\n", ",").replace(" ", ",")
    tickers = []

    for item in text.split(","):
        ticker = item.upper().strip()
        if ticker and ticker not in tickers:
            tickers.append(ticker)

    return tickers


def detect_source(title):
    for source in SOURCE_WEIGHTS:
        if source.lower() in title.lower():
            return source

    if " - " in title:
        return title.split(" - ")[-1].strip()

    return "Unknown"


def source_weight(source):
    return SOURCE_WEIGHTS.get(source, 4)


def get_high_quality_news(ticker):
    queries = [
        f"{ticker} Reuters market news",
        f"{ticker} CNBC market news",
        f"{ticker} MarketWatch market news",
        f"{ticker} Barrons stock news",
        f"{ticker} Benzinga stock news",
        f"{ticker} TipRanks analyst rating",
        f"{ticker} earnings guidance",
        f"{ticker} investor relations earnings",
        f"{ticker} SEC filing 8-K 10-Q",
        f"{ticker} Yahoo Finance news",
    ]

    articles = []
    seen_titles = set()

    for query in queries:
        safe_query = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={safe_query}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        for article in feed.entries[:3]:
            title = article.title.strip()

            if title in seen_titles:
                continue

            seen_titles.add(title)

            source = detect_source(title)
            weight = source_weight(source)

            articles.append({
                "title": title,
                "source": source,
                "weight": weight
            })

    articles = sorted(
        articles,
        key=lambda x: x["weight"],
        reverse=True
    )

    return articles[:10]


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
    articles = get_high_quality_news(ticker)

    news_text = ""

    for article in articles:
        news_text += (
            f"- [{article['source']} | Weight {article['weight']}/10] "
            f"{article['title']}\n"
        )

    evidence_score = 0

    if articles:
        evidence_score = round(
            sum(article["weight"] for article in articles) / len(articles),
            1
        )

    summary = f"""
Ticker: {ticker}
Asset Type: {"Crypto" if is_crypto else "Stock"}

Market Cap: {data["market_cap"]}
Trailing PE: {data["trailing_pe"]}
Forward PE: {data["forward_pe"]}
Revenue Growth: {data["revenue_growth"]}
Earnings Growth: {data["earnings_growth"]}

Evidence Quality Score: {evidence_score}/10

Weighted News:
{news_text}
"""

    return summary, articles, evidence_score


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
    evidence_scores = {}

    for ticker in tickers:
        summary, articles, evidence_score = build_summary(ticker)
        summaries.append(summary)
        all_news[ticker] = articles
        evidence_scores[ticker] = evidence_score

    combined_data = "\n\n====================\n\n".join(summaries)

    prompt = f"""
你是一名管理超過100億美元資產的進取型基金經理。

你的工作不是寫分析文章，而是作出投資決策。

你必須優先使用高質量資料來源，而不是新聞數量。

資料來源權重規則：
- SEC、公司官方 Investor Relations、官方財報、Reuters：最高權重
- CNBC、MarketWatch、Barron's：高權重
- Benzinga、TipRanks、Zacks：中高權重
- Yahoo Finance、Investing.com：中等權重
- Motley Fool、Blog、Opinion 類來源：低權重

重要原則：
1. Quality over Quantity：高質資料比大量普通新聞重要
2. Events over Headlines：分析事件，不要只數新聞標題
3. Decision over Description：先給決策，再給原因
4. Evidence over Opinion：BUY / HOLD / AVOID 必須由高質證據支持

請根據以下候選標的資料，判斷未來1至5個交易日的機會。

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
      "evidence_quality": 0,
      "reason": "一句原因，30字內",
      "buy_zone": "價格或N/A",
      "target_1": "價格或N/A",
      "target_2": "價格或N/A",
      "stop_loss": "價格或N/A",
      "key_evidence": [
        "最重要高質證據1",
        "最重要高質證據2",
        "最重要高質證據3"
      ],
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
- evidence_quality 用 0-10
- 如果高質來源不足，不要給太高 confidence
- 如果只有低質來源支持，不要給 BUY
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

    return parsed, response.output_text, response.usage, all_news, evidence_scores


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
    evidence_quality = item.get("evidence_quality", "N/A")
    reason = item.get("reason", "N/A")

    title = ticker

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
        st.metric("Evidence Quality", f"{evidence_quality}/10")

    st.info(reason)

    with st.expander("📌 高質證據"):
        for x in item.get("key_evidence", []):
            st.write("•", x)

    with st.expander("📄 詳細分析"):
        st.write("買入區：", item.get("buy_zone", "N/A"))
        st.write("第一目標價：", item.get("target_1", "N/A"))
        st.write("第二目標價：", item.get("target_2", "N/A"))
        st.write("止蝕位：", item.get("stop_loss", "N/A"))

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
        with st.spinner("Kin AI 正在搜尋高質資料並作出決策..."):
            parsed, raw_text, usage, all_news, evidence_scores = fund_manager_decision(tickers)

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

            with st.expander("📰 高質新聞來源 / Evidence Feed"):
                for ticker, articles in all_news.items():
                    st.markdown(f"### {ticker}")
                    st.write(f"平均證據質素：{evidence_scores.get(ticker, 'N/A')}/10")

                    for article in articles:
                        st.write(
                            f"• [{article['source']} | Weight {article['weight']}/10] "
                            f"{article['title']}"
                        )

            st.caption(
                f"Token Usage — Input: {usage.input_tokens} | "
                f"Output: {usage.output_tokens} | Total: {usage.total_tokens}"
            )