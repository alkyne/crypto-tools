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
    "doge_usdt": None,

    "btc_krw": None,   # Upbit BTC/KRW
    "eth_krw": None,   # Upbit ETH/KRW
    "trump_krw": None,   # Upbit trump/KRW
    "xrp_krw": None,
    "doge_krw": None,

    "usdt_krw": None   # Upbit USDT/KRW
}

# ticker: "btc" or "eth"
async def print_prices(ticker):
    """Print the latest prices and computed kimp ratios with a timestamp."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usdt_krw = float(price_data['usdt_krw'])
    # print(usdt_krw)

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
            # await send_telegram_message(msg)
            await write_file_message(msg)

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
    uri = "wss://fstream.binance.com/stream?streams=btcusdt@ticker/ethusdt@ticker/trumpusdt@ticker/xrpusdt@ticker/dogeusdt@ticker"
    async with websockets.connect(uri) as ws:
        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)
                stream = data.get("stream")
                ticker_data = data.get("data")
                if ticker_data == None:
                    continue
                if stream == "btcusdt@ticker":
                    price_data["btc_usdt"] = float(ticker_data.get("c"))
                    await print_prices("btc")
                elif stream == "ethusdt@ticker":
                    price_data["eth_usdt"] = float(ticker_data.get("c"))
                    await print_prices("eth")
                elif stream == "trumpusdt@ticker":
                    price_data["trump_usdt"] = float(ticker_data.get("c"))
                    await print_prices("trump")
                elif stream == "xrpusdt@ticker":
                    price_data["xrp_usdt"] = float(ticker_data.get("c"))
                    await print_prices("xrp")
                elif stream == "dogeusdt@ticker":
                    price_data["doge_usdt"] = float(ticker_data.get("c"))
                    await print_prices("doge")
                # print_prices()
            except Exception as e:
                print("Binance error:", e)
                # break

async def upbit_ws():
    """
    Connects to Upbit's websocket to subscribe to BTC/KRW, ETH/KRW, and USDT/KRW tickers.
    """
    # Subscribe to KRW-BTC, KRW-ETH, and KRW-USDT tickers.
    uri = "wss://api.upbit.com/websocket/v1"
    subscribe_msg = [
        {"ticket": "unique_ticket"},
        {"type": "ticker", "codes": ["KRW-BTC", "KRW-ETH", "KRW-TRUMP", "KRW-XRP", "KRW-DOGE", "KRW-USDT"]}
    ]
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps(subscribe_msg))
        while True:
            try:
                message = await ws.recv()
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                data = json.loads(message)
                code = data.get("code").lower() # "krw-btc"
                trade_price = data.get("trade_price")
                if trade_price is None:
                    continue
                dict_ticker = code.split("-")[1] + "_krw" # form of "btc_krw"
                # print(dict_ticker)
                # print(trade_price)
                price_data[dict_ticker] = float(trade_price)
                if dict_ticker != "usdt_krw":
                    await print_prices(code.split("-")[1]) # "btc"
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

async def hyperliquid_ws():
    # Replace this URL with the official Hyperliquid websocket endpoint if different.
    url = "wss://api.hyperliquid.xyz/ws"

    async with websockets.connect(url) as ws:
        # Send the subscription message for all mid prices.
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "allMids"
            }
        }

        await ws.send(json.dumps(subscribe_msg))
        print("Subscribed")

        # Listen for messages indefinitely.
        while True:
            message = await ws.recv()
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print("Received non-JSON message:", message)
                continue

            channel = data.get("channel")
            # print (data)
            
            # Handle the subscription response message.
            if channel == "subscriptionResponse":
                print("Subscription response received:", data)
            
            # Look for mid price updates.
            elif channel == "allMids":
                # The data is expected in the format: { "data": { "mids": { "<symbol>": "<price>", ... } } }
                mids = data.get("data", {}).get("mids", {})
                # Depending on the API naming convention, the key might be "BTCUSDT", "BTC/USDT", etc.
                btc_price = mids.get("BTC")
                xrp_price = mids.get("XRP")
                trump_price = mids.get("TRUMP")
                # if btc_price is not None:
                    # print("BTC/USDT Perp Price:", btc_price)
                    # print("XRP/USDT Perp Price:", xrp_price)
                    # print("TRUMP/USDT Perp Price:", trump_price)
                # else:
                    # Optionally print if no BTC price is found.
                    # print("BTC/USDT price not found in mids:", mids)

                price_data["btc_usdt"] = float(btc_price)
                price_data["xrp_usdt"] = float(xrp_price)
                price_data["trump_usdt"] = float(trump_price)

                # await print_prices("btc")

async def send_telegram_message(msg):
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

async def write_file_message(msg):
    f.write(msg + "\n")

async def main():
    # Run both websocket connections concurrently.
    # await asyncio.gather(binance_ws(), upbit_ws())
    await asyncio.gather(hyperliquid_ws(), upbit_ws())

if __name__ == "__main__":
    f = open("kimp_alert.txt", "a+")
    asyncio.run(main())