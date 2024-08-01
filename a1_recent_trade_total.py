import ccxt, json
import pandas as pd
import numpy as np
import dontshare_config as ds
from datetime import date, datetime, timezone, tzinfo
import time,schedule
import nice_funcs as n
import datetime as dt

phemex = ccxt.phemex({
  'enableRateLimit': True,
  'apiKey': ds.xP_hmv_KEY,
  'secret': ds.xP_hmv_SECRET,
})

symbol = 'BTCUSD'
def bot():
  
  print('starting recent trades bot...')
  
  #pull in recent orders
  tape_reader_df = pd.DataFrame()
  
  params = {'type':'swap','code':'USD'}
  phe_bal = phemex.fetch_balance(params = params)

  n
  
  #total recent order
  