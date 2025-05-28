import ccxt
import time
import requests
import os
import threading
import schedule
from flask import Flask
from dotenv import load_dotenv

# === 環境變數 ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === 初始化 OKX ===
okx = ccxt.okx()
okx.load_markets()

# === 模擬參數設定 ===
TWD_CAPITAL = 150000
TWD_USDT_RATE = 32.0
BASE_USDT = TWD_CAPITAL / TWD_USDT_RATE
FEE_RATE = 0.001
SLIPPAGE = 0.0015
MIN_PROFIT_RATE = 0.001

# === 模擬資金狀態 ===
sim_wallet = {
    "usdt": BASE_USDT,
    "history": []
}

app = Flask(__name__)

@app.route("/")
def home():
    return f"🟢 OKX Arbitrage Running - USDT Balance: {sim_wallet['usdt']:.2f}"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram 發送失敗：", e)

def check_arbitrage():
    try:
        tickers = {
            "BTC/USDT": okx.fetch_ticker("BTC/USDT"),
            "ETH/BTC": okx.fetch_ticker("ETH/BTC"),
            "ETH/USDT": okx.fetch_ticker("ETH/USDT")
        }

        # 正向套利 USDT -> BTC -> ETH -> USDT
        btc_ask = tickers["BTC/USDT"]["ask"] * (1 + SLIPPAGE)
        eth_ask = tickers["ETH/BTC"]["ask"] * (1 + SLIPPAGE)
        eth_bid = tickers["ETH/USDT"]["bid"] * (1 - SLIPPAGE)

        usdt = sim_wallet["usdt"]
        btc_amt = usdt / btc_ask * (1 - FEE_RATE)
        eth_amt = btc_amt / eth_ask * (1 - FEE_RATE)
        usdt_final = eth_amt * eth_bid * (1 - FEE_RATE)

        profit = usdt_final - usdt
        profit_rate = profit / usdt

        if profit_rate > MIN_PROFIT_RATE:
            msg = (
                f"🟢 正向套利：USDT→BTC→ETH→USDT\n"
                f"利潤率：{profit_rate*100:.2f}%\n"
                f"淨利：{profit:.2f} USDT"
            )
            send_telegram(msg)
            sim_wallet["usdt"] = usdt_final
            sim_wallet["history"].append({"type": "forward", "profit": profit, "timestamp": time.time()})

        # 反向套利 USDT -> ETH -> BTC -> USDT
        eth_ask_rev = tickers["ETH/USDT"]["ask"] * (1 + SLIPPAGE)
        btc_bid_rev = tickers["BTC/USDT"]["bid"] * (1 - SLIPPAGE)
        eth_btc_bid = tickers["ETH/BTC"]["bid"] * (1 - SLIPPAGE)

        eth_amt_rev = usdt / eth_ask_rev * (1 - FEE_RATE)
        btc_amt_rev = eth_amt_rev * eth_btc_bid * (1 - FEE_RATE)
        usdt_final_rev = btc_amt_rev * btc_bid_rev * (1 - FEE_RATE)

        profit_rev = usdt_final_rev - usdt
        profit_rate_rev = profit_rev / usdt

        if profit_rate_rev > MIN_PROFIT_RATE:
            msg = (
                f"🟡 反向套利：USDT→ETH→BTC→USDT\n"
                f"利潤率：{profit_rate_rev*100:.2f}%\n"
                f"淨利：{profit_rev:.2f} USDT"
            )
            send_telegram(msg)
            sim_wallet["usdt"] = usdt_final_rev
            sim_wallet["history"].append({"type": "reverse", "profit": profit_rev, "timestamp": time.time()})

    except Exception as e:
        print("套利檢查錯誤：", e)

def loop_arbitrage():
    while True:
        check_arbitrage()
        time.sleep(1)

def send_daily_report():
    usdt = sim_wallet["usdt"]
    twd_equivalent = usdt * TWD_USDT_RATE
    total_profit = sum(h["profit"] for h in sim_wallet["history"])
    msg = (
        f"📊 每日模擬資金報告\n"
        f"🕘 時間：{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"💵 現有 USDT：{usdt:.2f}\n"
        f"💰 折合 TWD：約 {twd_equivalent:.2f} 元\n"
        f"📈 累積套利淨利：{total_profit:.2f} USDT\n"
        f"📄 套利次數：{len(sim_wallet['history'])}"
    )
    send_telegram(msg)

def schedule_daily_report():
    schedule.every().day.at("09:00").do(send_daily_report)
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    send_telegram(f"🚀 OKX 套利模擬器啟動（含反向套利，每秒掃描）\n初始資金：{sim_wallet['usdt']:.2f} USDT")
    threading.Thread(target=loop_arbitrage, daemon=True).start()
    threading.Thread(target=schedule_daily_report, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
