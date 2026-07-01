from memory import load_memory, update_validation
import yfinance as yf


def judge(action, ret):
    action = str(action).upper()

    if action == "BUY":
        return "SUCCESS" if ret > 0 else "FAILED"

    if action == "AVOID":
        return "SUCCESS" if ret < 0 else "FAILED"

    if action == "HOLD":
        if abs(ret) <= 3:
            return "SUCCESS"
        elif ret > 3:
            return "MISSED UP"
        else:
            return "MISSED DOWN"

    return "UNKNOWN"


def get_action_from_summary(summary):
    try:
        return summary.split("|")[0].replace("Action:", "").strip()
    except Exception:
        return "UNKNOWN"


memories = load_memory()
pending = []

for m in memories:
    entry_price = m.get("Entry Price")
    current_price = m.get("Current Price")

    if entry_price and not current_price:
        pending.append(m)

print(f"Need Validation: {len(pending)}")

for p in pending:
    ticker = p["Ticker"]
    entry_price = float(p["Entry Price"])
    action = get_action_from_summary(p.get("Summary", ""))

    stock = yf.Ticker(ticker)
    hist = stock.history(period="1d")

    if hist.empty:
        print(f"{ticker}: no price data")
        continue

    current_price = round(float(hist["Close"].iloc[-1]), 2)

    ret = round((current_price - entry_price) / entry_price * 100, 2)
    status = judge(action, ret)

    result = update_validation(
        hash_value=p["Hash"],
        current_price=current_price,
        return_pct=ret,
        status=status
    )

    print(
        ticker,
        "Action:", action,
        "Entry:", entry_price,
        "Current:", current_price,
        "Return:", ret,
        "Status:", status,
        "Update:", result
    )