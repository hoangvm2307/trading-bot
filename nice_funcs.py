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

def ask_bid(symbol=symbol):
  ob = phemex.fetch_order_book(symbol)
  
  bid = ob['bids'][0][0]
  ask = ob['asks'][0][0]
  print(f'this is the ask for {symbol} {ask}')
  
  return ask, bid

ask_bid()

# def daily_sma();