# OKX Triangular Arbitrage Simulator

This app simulates triangular arbitrage on OKX, accounting for trading fees and slippage, and includes daily performance tracking with Telegram notifications.

## Usage

1. Copy `.env.example` to `.env` and fill in your Telegram Bot credentials.
2. Deploy to Render as a Web Service.
3. The app will run:
   - Arbitrage simulation every 15 seconds.
   - Daily report at 09:00 via Telegram.

## Deployment

**Build command:**
```
pip install -r requirements.txt
```

**Start command:**
```
python app.py
```
