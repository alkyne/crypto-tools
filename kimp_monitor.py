import asyncio
import json
from datetime import datetime
import websockets

# Shared dictionary to store latest prices.
price_data = {
    "btc_usdt": None,  # From Binance
    "btc_krw": None,   # From Upbit (BTC)
    "usdt_krw": None   # From Upbit (USDT)
}

def print_prices():
    """Print the latest prices with the current timestamp."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # print(f"[{now}] BTC/USDT: {price_data['btc_usdt']}, BTC/KRW: {price_data['btc_krw']}, USDT/KRW: {price_data['usdt_krw']}")
    usdt_krw = price_data['usdt_krw']
    if price_data['btc_krw'] is not None and price_data['btc_usdt'] is not None:
        btc_kimp = price_data['btc_krw'] / price_data['btc_usdt']
    else:
        return
    diff = btc_kimp - usdt_krw
    print(f"[{now}] diff: {diff:,.2f} (btc_kimp: {btc_kimp:,.2f}, usdt_krw: {usdt_krw})")

async def binance_ws():
    """
    Connects to Binance websocket for BTC/USDT ticker.
    Binance sends a JSON message with a 'c' field (current price).
    """
    uri = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
    async with websockets.connect(uri) as ws:
        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)
                # 'c' holds the current (last) price
                price_data["btc_usdt"] = float(data.get("c"))
                print_prices()
            except Exception as e:
                print("Binance error:", e)
                break

async def upbit_ws():
    """
    Connects to Upbit websocket for BTC/KRW and USDT/KRW tickers.
    We send a subscription message for the codes 'KRW-BTC' and 'KRW-USDT'.
    Each message contains a 'code' field (to identify the market)
    and 'trade_price' which is the latest price.
    """
    uri = "wss://api.upbit.com/websocket/v1"
    async with websockets.connect(uri) as ws:
        # Send subscription message to Upbit.
        subscribe_msg = [
            {"ticket": "unique_ticket"},
            {"type": "ticker", "codes": ["KRW-BTC", "KRW-USDT"]}
        ]
        await ws.send(json.dumps(subscribe_msg))
        while True:
            try:
                message = await ws.recv()
                # Upbit may send binary messages; decode if necessary.
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                data = json.loads(message)
                code = data.get("code")
                trade_price = data.get("trade_price")
                if code == "KRW-BTC":
                    price_data["btc_krw"] = float(trade_price)
                elif code == "KRW-USDT":
                    price_data["usdt_krw"] = float(trade_price)
                print_prices()
            except Exception as e:
                print("Upbit error:", e)
                break

async def main():
    # Run both websocket connections concurrently.
    await asyncio.gather(binance_ws(), upbit_ws())

if __name__ == "__main__":
    asyncio.run(main())