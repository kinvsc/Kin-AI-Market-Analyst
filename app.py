import os, re, json
from datetime import datetime
from urllib.parse import quote_plus
import feedparser
import yfinance as yf
import streamlit as st
from openai import OpenAI
from memory import save_memory


LOG_FILE = "security_log.txt"

def write_security_log(event):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now} - {event}\n")


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Password", type="password")

        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            write_security_log("Login Success")
            st.rerun()

        elif password:
            write_security_log("Wrong Password")
            st.error("Wrong password")
            st.stop()

        else:
            st.stop()


st.set_page_config(page_title="Kin AI", page_icon="🚀", layout="centered")

check_password()

st.title("🚀 Kin AI")
st.caption("Decision Engine v4.4 Memory")

if st.button("🧠 Test Memory"):
    save_memory(
        ticker="TEST",
        memory_type="System",
        source="Kin AI",
        score=100,
        summary="Google Sheet memory test successful",
        version="v4.4"
    )
    st.success("Memory saved!")

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

SOURCE_WEIGHTS = {
    "Reuters": 10,
    "SEC": 10,
    "Investor Relations": 10,
    "NVIDIA Newsroom": 10,
    "CNBC": 9,
    "MarketWatch": 8,
    "Barron's": 8,
    "Benzinga": 7,
    "TipRanks": 7,
    "Zacks": 6,
    "Yahoo Finance": 5,
    "Investing.com": 5,
    "Motley Fool": 3,
}

def clean_tickers(text):
    text = text.replace("\n", ",").replace(" ", ",")
    result = []
    for x in text.split(","):
        t = x.upper().strip()
        if t and t not in result:
            result.append(t)
    return result

def detect_source(title):
    for source in SOURCE_WEIGHTS:
        if source.lower() in title.lower():
            return source
    if " - " in title:
        return title.split(" - ")[-1].strip()
    return "Unknown"

def source_weight(source):
    return SOURCE_WEIGHTS.get(source, 4)

def get_news(ticker, mode):
    if mode == "⚡ Quick Mode":
        queries = [
            f"{ticker} Reuters market news",
            f"{ticker} CNBC market news",
            f"{ticker} MarketWatch market news",
            f"{ticker} earnings guidance",
            f"{ticker} stock market news",
        ]
        max_articles = 5
        per_query = 1
    else:
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
        max_articles = 10
        per_query = 3

    articles = []
    seen = set()

    for query in queries:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)

        for article in feed.entries[:per_query]:
            title = article.title.strip()
            if title in seen:
                continue

            seen.add(title)
            source = detect_source(title)

            articles.append({
                "title": title,
                "source": source,
                "weight": source_weight(source),
            })

        if len(articles) >= max_articles:
            break

    articles = sorted(articles, key=lambda x: x["weight"], reverse=True)
    return articles[:max_articles]

def get_basic_data(ticker):
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        info = {}

    return {
        "market_cap": info.get("marketCap", "N/A"),
        "trailing_pe": info.get("trailingPE", "N/A"),
        "forward_pe": info.get("forwardPE", "N/A"),
        "revenue_growth": info.get("revenueGrowth", "N/A"),
        "earnings_growth": info.get("earningsGrowth", "N/A"),
    }

def build_summary(ticker, mode):
    is_crypto = "-USD" in ticker
    data = get_basic_data(ticker)
    articles = get_news(ticker, mode)

    news_text = ""
    for a in articles:
        news_text += f"- [{a['source']} | Weight {a['weight']}/10] {a['title']}\n"

    evidence_score = 0
    if articles:
        evidence_score = round(sum(a["weight"] for a in articles) / len(articles), 1)

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

def ai_decision(tickers, mode):
    summaries = []
    all_news = {}
    evidence_scores = {}

    for ticker in tickers:
        summary, articles, evidence_score = build_summary(ticker, mode)
        summaries.append(summary)
        all_news[ticker] = articles
        evidence_scores[ticker] = evidence_score

    combined_data = "\n\n====================\n\n".join(summaries)

    if mode == "⚡ Quick Mode":
        prompt = f"""
你是一名進取型基金經理。你的任務是用最少文字，快速作出投資決策。

資料來源有權重：
SEC / 公司官方 / Reuters 權重最高。
CNBC / MarketWatch 次高。
Yahoo / Investing 只作輔助。
低質 Opinion 不可主導決策。

請根據以下資料，判斷未來1至5個交易日：

{combined_data}

只輸出 JSON，不要輸出其他文字。

格式：

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
      "reason": "一句原因，30字內"
    }}
  ],
  "cash_warning": "N/A 或 今日不適合出手原因"
}}

規則：
- action 只能 BUY / HOLD / AVOID
- 不要保證升跌
- 如果高質證據不足，不要給太高 confidence
- 如果沒有明顯機會，top_pick 寫 NONE，market_decision 寫 STAY CASH
"""
    else:
        prompt = f"""
你是一名管理超過100億美元資產的進取型基金經理。

你的工作不是寫文章，而是作出投資決策。
必須優先使用高質量來源，而不是新聞數量。

原則：
1. Quality over Quantity
2. Events over Headlines
3. Decision over Description
4. Evidence over Opinion

請根據以下資料，判斷未來1至5個交易日：

{combined_data}

只輸出 JSON，不要輸出其他文字。

格式：

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
  "cash_warning": "N/A 或 今日不適合出手原因"
}}

規則：
- action 只能 BUY / HOLD / AVOID
- 如果只有低質來源支持，不要給 BUY
- 如果沒有明顯機會，top_pick 寫 NONE，market_decision 寫 STAY CASH
- 不要保證升跌
- 機率只是主觀估算
"""

    response = client.responses.create(
        model="gpt-5.5",
        input=prompt
    )

    parsed = extract_json(response.output_text)
    return parsed, response.output_text, response.usage, all_news, evidence_scores

def action_icon(action):
    if action == "BUY":
        return "🟢"
    if action == "HOLD":
        return "🟡"
    if action == "AVOID":
        return "🔴"
    return "⚪"

def display_item(item, mode, rank=None):
    ticker = item.get("ticker", "N/A")
    action = item.get("action", "N/A")

    if rank == 1:
        title = f"🥇 {ticker}"
    elif rank == 2:
        title = f"🥈 {ticker}"
    elif rank == 3:
        title = f"🥉 {ticker}"
    else:
        title = ticker

    st.markdown(f"## {title}")
    st.markdown(f"### {action_icon(action)} {action}")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("AI Score", f"{item.get('ai_score', 'N/A')}/100")
        st.metric("上升機率", f"{item.get('success_probability', 'N/A')}%")
        st.metric("預估波動", item.get("expected_move", "N/A"))

    with col2:
        st.metric("風險機率", f"{item.get('risk_probability', 'N/A')}%")
        st.metric("信心指數", f"{item.get('confidence', 'N/A')}%")
        st.metric("Evidence Quality", f"{item.get('evidence_quality', 'N/A')}/10")

    st.info(item.get("reason", "N/A"))

    if mode == "🧠 Fund Manager Mode":
        with st.expander("📌 高質證據"):
            for x in item.get("key_evidence", []):
                st.write("•", x)

        with st.expander("📄 詳細分析"):
            st.write("買入區：", item.get("buy_zone", "N/A"))
            st.write("第一目標價：", item.get("target_1", "N/A"))
            st.write("第二目標價：", item.get("target_2", "N/A"))
            st.write("止蝕位：", item.get("stop_loss", "N/A"))

            details = item.get("details", {})
            for section, title in [
                ("bullish", "利好因素"),
                ("bearish", "利淡因素"),
                ("catalysts", "催化劑"),
                ("risks", "最大風險"),
            ]:
                st.markdown(f"#### {title}")
                for x in details.get(section, []):
                    st.write("•", x)

st.subheader("🎯 Fund Manager Input")

analysis_mode = st.radio(
    "分析模式",
    ["⚡ Quick Mode", "🧠 Fund Manager Mode"],
    horizontal=True
)

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

if st.button("🚀 開始決策"):
    if not tickers:
        st.warning("請輸入至少一隻 ticker。")
    else:
        with st.spinner(f"Kin AI 正在用 {analysis_mode} 分析..."):
            parsed, raw_text, usage, all_news, evidence_scores = ai_decision(tickers, analysis_mode)

        if parsed is None:
            st.error("AI 回覆格式解析失敗，以下是原始回覆：")
            st.write(raw_text)
        else:
            st.subheader("🚀 今日決策")

            md = parsed.get("market_decision", "N/A")
            top_pick = parsed.get("top_pick", "N/A")
            summary = parsed.get("summary", "N/A")
            cash_warning = parsed.get("cash_warning", "N/A")

            if md == "BUY":
                st.success(f"🟢 Market Decision: {md}")
            elif md == "HOLD":
                st.warning(f"🟡 Market Decision: {md}")
            elif md == "AVOID":
                st.error(f"🔴 Market Decision: {md}")
            elif md == "STAY CASH":
                st.error("⚪ Market Decision: STAY CASH")
            else:
                st.info(f"Market Decision: {md}")

            st.markdown(f"### 🏆 Top Pick: {top_pick}")
            st.info(summary)

            if cash_warning and cash_warning != "N/A":
                st.warning(cash_warning)

            st.divider()

            items = parsed.get("items", [])
            for item in items:
                ticker_symbol = item.get("ticker", "N/A")

                entry_price = None
                try:
                    stock = yf.Ticker(ticker_symbol)
                    hist = stock.history(period="1d")
                    if not hist.empty:
                        entry_price = round(float(hist["Close"].iloc[-1]), 2)
                except Exception:
                    entry_price = None
                    
                save_memory(
                    memory_type="Stock Analysis",
                    source="Kin AI Decision Engine",
                    score=item.get("ai_score", 0),
                    summary=(
                        f"Action: {item.get('action', 'N/A')} | "
                        f"Success: {item.get('success_probability', 'N/A')}% | "
                        f"Risk: {item.get('risk_probability', 'N/A')}% | "
                        f"Expected Move: {item.get('expected_move', 'N/A')} | "
                        f"Confidence: {item.get('confidence', 'N/A')} | "
                        f"Reason: {item.get('reason', 'N/A')}"
                    ),
                    version="v4.5",
                    entry_price=entry_price
                )

            try:
                items = sorted(items, key=lambda x: int(x.get("ai_score", 0)), reverse=True)
            except Exception:
                pass

            st.subheader("📊 Ranking")

            for i, item in enumerate(items, start=1):
                display_item(item, analysis_mode, rank=i)
                st.divider()

            with st.expander("📰 Evidence Feed"):
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