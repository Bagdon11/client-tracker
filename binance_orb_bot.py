from binance.client import Client
import pandas as pd
import time
from ta.momentum import RSIIndicator

# Initialize Binance client
api_key = "your_api_key"  # Replace with your API key
api_secret = "your_secret_key"
client = Client(api_key, api_secret)

# Settings
symbol = "BTCUSDT"
timeframe = "1h"          # Opening range duration
orb_period = 1            # 1-hour ORB (adjust as needed)
rsi_window = 14           # RSI period
rsi_overbought = 70       # RSI sell threshold
rsi_oversold = 30         # RSI buy threshold

def get_historical_data(symbol, interval, limit=100):
    """Fetch historical klines and convert to DataFrame."""
    klines = client.get_klines(
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    return df

def calculate_rsi(df, window=14):
    """Calculate RSI using TA library."""
    return RSIIndicator(df['close'], window=window).rsi()

def get_opening_range(symbol, interval, orb_period):
    """Fetch opening range high/low."""
    df = get_historical_data(symbol, interval, orb_period)
    opening_range = df.iloc[:orb_period]
    return opening_range['high'].max(), opening_range['low'].min()

def monitor_orb_breakout(symbol, orb_high, orb_low):
    """Monitor live price and RSI for breakouts."""
    while True:
        # Get live price
        live_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        
        # Get latest RSI (using last 100 candles)
        df = get_historical_data(symbol, Client.KLINE_INTERVAL_1HOUR, 100)
        rsi = calculate_rsi(df, rsi_window).iloc[-1]  # Latest RSI value
        
        # Trading logic
        if live_price > orb_high and rsi < rsi_overbought:
            print(f"BUY SIGNAL: {symbol} broke ORB high ({orb_high}) | RSI: {rsi:.2f}")
            # Add buy order logic here
        elif live_price < orb_low and rsi > rsi_oversold:
            print(f"SELL SIGNAL: {symbol} broke ORB low ({orb_low}) | RSI: {rsi:.2f}")
            # Add sell order logic here
        else:
            print(f"Waiting... Price: {live_price} | RSI: {rsi:.2f}")
        
        time.sleep(5)  # Check every 5 seconds

# Main execution
if __name__ == "__main__":
    # Get Opening Range
    orb_high, orb_low = get_opening_range(symbol, Client.KLINE_INTERVAL_1HOUR, orb_period)
    print(f"ORB High: {orb_high}, ORB Low: {orb_low}")
    
    # Start monitoring
    monitor_orb_breakout(symbol, orb_high, orb_low)