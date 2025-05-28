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
    "eth": 0,
    "btc": 0,
    "history": []
}

app = Flask(__name__)

@app.route("/")
def home():
    return f"🟢 OKX Triangular Arbitrage Simulator Running with {sim_wallet['usdt']:.2f} USDT"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram 發送失敗：", e)

def simulate_okx_triangle():
    try:
        btc_ask = okx.fetch_ticker('BTC/USDT')['ask'] * (1 + SLIPPAGE)
        eth_ask = okx.fetch_ticker('ETH/BTC')['ask'] * (1 + SLIPPAGE)
        eth_bid = okx.fetch_ticker('ETH/USDT')['bid'] * (1 - SLIPPAGE)

        btc_amt = sim_wallet['usdt'] / btc_ask
        btc_amt *= (1 - FEE_RATE)

        eth_amt = btc_amt / eth_ask
        eth_amt *= (1 - FEE_RATE)

        final_usdt = eth_amt * eth_bid
        final_usdt *= (1 - FEE_RATE)

        profit = final_usdt - sim_wallet['usdt']
        profit_rate = profit / sim_wallet['usdt']

        print(f"[OKX套利] 利潤率: {profit_rate:.4f}, 淨利: {profit:.2f} USDT")

        if profit_rate > MIN_PROFIT_RATE:
            msg = (
                f"🔁 OKX 三角套利機會！\n"
                f"1️⃣ USDT → BTC @ {btc_ask:.2f}（含滑價+費）\n"
                f"2️⃣ BTC → ETH @ {eth_ask:.6f}（含滑價+費）\n"
                f"3️⃣ ETH → USDT @ {eth_bid:.2f}（含滑價+費）\n"
                f"📈 利潤率：{profit_rate*100:.2f}%\n"
                f"💰 模擬淨利：{profit:.2f} USDT"
            )
            send_telegram(msg)

            sim_wallet['history'].append({
                "profit": profit,
                "rate": profit_rate,
                "usdt_before": sim_wallet['usdt'],
                "usdt_after": final_usdt,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            sim_wallet['usdt'] = final_usdt

    except Exception as e:
        print("❌ 模擬錯誤：", e)

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

def loop_arbitrage():
    while True:
        simulate_okx_triangle()
        time.sleep(15)

if __name__ == "__main__":
    send_telegram(f"🚀 模擬器啟動，初始資金 {sim_wallet['usdt']:.2f} USDT (≈{TWD_CAPITAL} TWD)")
    threading.Thread(target=loop_arbitrage, daemon=True).start()
    threading.Thread(target=schedule_daily_report, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
