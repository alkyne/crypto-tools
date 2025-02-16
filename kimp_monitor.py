import asyncio
import json
from datetime import datetime
import websockets
import requests

THRESHOLD_USDT_DIFF = 3.5

# Shared dictionary to store latest prices.
price_data = {
    "btc_usdt": None,  # Binance BTC/USDT
    "eth_usdt": None,  # Binance ETH/USDT
    "trump_usdt": None,  # Binance trump/USDT
    "xrp_usdt": None,

    "btc_krw": None,   # Upbit BTC/KRW
    "eth_krw": None,   # Upbit ETH/KRW
    "trump_krw": None,   # Upbit trump/KRW
    "xrp_krw": None,

    "usdt_krw": None   # Upbit USDT/KRW
}

# ticker: "btc" or "eth"
def print_prices(ticker):
    """Print the latest prices and computed kimp ratios with a timestamp."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usdt_krw = float(price_data['usdt_krw'])

    # if ticker != "btc":
    #     return
    
    # Compute kimp ratios when both prices are available.
    if price_data[f'{ticker}_krw'] is not None and price_data[f'{ticker}_usdt'] is not None:
        calculated_kimp = float(price_data[f'{ticker}_krw']) / float(price_data[f'{ticker}_usdt'])
        diff = calculated_kimp - usdt_krw
        upbit_krw = price_data[f'{ticker}_krw']
        msg = f"[{now}] [{ticker.upper()}] diff: {diff:,.2f} ({ticker}_kimp: {calculated_kimp:,.2f}, USDT/KRW: {usdt_krw}, {ticker.upper()}/KRW: {upbit_krw:,})"
        print(msg)

        if abs(diff) >= THRESHOLD_USDT_DIFF:
            send_telegram_message(msg)

    # if diff is lower than THRESHOLD_USDT_DIFF, hedge
    # if diff is higher than THRESHOLD_USDT_DIFF, unhedge
    
    
    # print(f"[{now}] BTC/USDT: {price_data['btc_usdt']}, BTC/KRW: {price_data['btc_krw']}, BTC Kimp: {btc_kimp}, "
    #       f"ETH/USDT: {price_data['eth_usdt']}, ETH/KRW: {price_data['eth_krw']}, ETH Kimp: {eth_kimp}, "
    #       f"USDT/KRW: {price_data['usdt_krw']}")


async def binance_ws():
    """
    Connects to Binance's combined websocket stream for BTC/USDT and ETH/USDT.
    """
    # uri = "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker/glmusdt@ticker"
    uri = "wss://fstream.binance.com/stream?streams=btcusdt@ticker/ethusdt@ticker/trumpusdt@ticker/xrpusdt@ticker"
    async with websockets.connect(uri) as ws:
        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)
                stream = data.get("stream")
                ticker_data = data.get("data")
                if stream == "btcusdt@ticker":
                    price_data["btc_usdt"] = float(ticker_data.get("c"))
                    print_prices("btc")
                elif stream == "ethusdt@ticker":
                    price_data["eth_usdt"] = float(ticker_data.get("c"))
                    print_prices("eth")
                elif stream == "trumpusdt@ticker":
                    price_data["trump_usdt"] = float(ticker_data.get("c"))
                    print_prices("trump")
                elif stream == "xrpusdt@ticker":
                    price_data["xrp_usdt"] = float(ticker_data.get("c"))
                    print_prices("xrp")
                # print_prices()
            except Exception as e:
                print("Binance error:", e)
                # break

async def upbit_ws():
    """
    Connects to Upbit's websocket to subscribe to BTC/KRW, ETH/KRW, and USDT/KRW tickers.
    """
    uri = "wss://api.upbit.com/websocket/v1"
    async with websockets.connect(uri) as ws:
        # Subscribe to KRW-BTC, KRW-ETH, and KRW-USDT tickers.
        subscribe_msg = [
            {"ticket": "unique_ticket"},
            {"type": "ticker", "codes": ["KRW-BTC", "KRW-ETH", "KRW-TRUMP", "KRW-XRP", "KRW-USDT"]}
        ]
        await ws.send(json.dumps(subscribe_msg))
        while True:
            try:
                message = await ws.recv()
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                data = json.loads(message)
                code = data.get("code").lower() # "krw-btc"
                trade_price = float(data.get("trade_price"))
                dict_ticker = code.split("-")[1] + "_krw" # form of "btc_krw"
                # print(dict_ticker)
                price_data[dict_ticker] = trade_price
                if dict_ticker != "usdt_krw":
                    print_prices(code.split("-")[1]) # "btc"
                # if code == "KRW-BTC":
                #     price_data["btc_krw"] = trade_price
                #     print_prices("btc")
                # elif code == "KRW-ETH":
                #     price_data["eth_krw"] = trade_price
                #     print_prices("eth")
                # elif code == "KRW-GLM":
                #     price_data["glm_krw"] = trade_price
                #     print_prices("glm")
                # elif code == "KRW-USDT":
                #     price_data["usdt_krw"] = trade_price
                # print_prices()
            except Exception as e:
                print("Upbit error:", e)
                # break

def send_telegram_message(msg):
    BOT_TOKEN = "7985657708:AAGLhMYKDeizF5Jy7l46mUgqzzQojPElyG0"  # Replace with your actual token
    CHAT_ID = "@kimpmonitor"                  # Replace with your chat ID (as an integer)
    MESSAGE_TEXT = msg

    # Telegram API URL
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Parameters
    params = {
        "chat_id": CHAT_ID,
        "text": MESSAGE_TEXT
    }

    # Make a GET request
    response = requests.get(url, params=params)

    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message:", response.text)

async def main():
    # Run both websocket connections concurrently.
    await asyncio.gather(binance_ws(), upbit_ws())

if __name__ == "__main__":
    asyncio.run(main())