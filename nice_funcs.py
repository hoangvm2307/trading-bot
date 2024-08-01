import ccxt, json
import pandas as pd
import numpy as np
import dontshare_config as ds
from datetime import date, datetime, timezone, tzinfo
import time, schedule

phemex = ccxt.phemex({
  'enableRateLimit': True,
  'apiKey': ds.xP_hmv_KEY,
  'secret': ds.xP_hmv_SECRET,
})

symbol = 'BTCUSD'
pos_size = 100 # 125, 75,
params = {'timeInForce': 'PostOnly',}
target = 35
max_loss = -55
vol_decimal = .4

# For df
timeframe = '4h'
limit=100
sma=20

def ask_bid(symbol=symbol):
  ob = phemex.fetch_order_book(symbol)
  
  bid = ob['bids'][0][0]
  ask = ob['asks'][0][0]
  print(f'this is the ask for {symbol} {ask}')
  
  return ask, bid

# returns: df with sma
# call: daily_sma(symbol, timeframe, limit, sma) # if not passed, uses default
def daily_sma(symbol=symbol, timeframe=timeframe, limit=limit, sma=sma):
  """
  Calculate the daily simple moving average (SMA) of the closing price over a 20-day period.

  This function fetches the historical OHLCV data for a given symbol and timeframe using the `phemex.fetch_ohlcv` method. It then creates a pandas DataFrame with the fetched data and converts the timestamp column to datetime format.

  The function calculates the 20-day SMA of the closing prices using the `rolling` method of the DataFrame. It assigns the calculated SMA values to a new column named 'sma20_d'.

  The function determines the bid price using the `ask_bid` function and assigns it to the variable `bid`. It then assigns 'SELL' to the 'sig' column of the DataFrame if the SMA value is greater than the bid price, and 'BUY' if the SMA value is less than the bid price.

  The function prints the DataFrame and returns it.

  Parameters:
    None

  Returns:
    df_d (pandas.DataFrame): The DataFrame containing the OHLCV data with the calculated SMA and 'sig' columns.
  """
  print('starting indis...')
  
  bars = phemex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
  #print(bars)
  
  df_sma = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
  df_sma['timestamp'] = pd.to_datetime(df_sma['timestamp'], unit='ms')
  
  # DAILY SMA - 20 day
  df_sma[f'sma{sma}_d'] = df_sma.close.rolling(sma).mean()

  # If bid < the 20 day sma then = BEARISH, if bid > 20 day sma = BULLISH
  bid = ask_bid(symbol)[1]
  
  # If sma > bid = SELL, if sma < bid = BUY
  df_sma.loc[df_sma[f'sma{sma}_d'] > bid, 'sig'] = 'SELL'
  df_sma.loc[df_sma[f'sma{sma}_d'] < bid, 'sig'] = 'BUY'
  
  print(df_sma)
  
  return df_sma

daily_sma('ETH/BTC', '15m', 100,30)