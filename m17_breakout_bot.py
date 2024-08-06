import ccxt, json
import pandas as pd
import numpy as np
import dontshare_config as ds
from datetime import date, datetime, timezone, tzinfo
import time,schedule
import nice_funcs as n
import datetime as dt
import nice_funcs as n

bingx = ccxt.bingx({
  'enableRateLimit': True,
  'apiKey': ds.bingx_KEY,
  'secret': ds.bingx_SECRET,
})

symbol = 'BTC/USDT'
pos_size = 1 # 125, 75,
target = 9 # % gain i want
max_loss = -8

index_pos = 3 # CHANGE BASED ON WHAT ASSET

# The time between trade
pause_time = 10

# for volume calc vol_repeat * vol_time == TIME of volume collection
vol_repeat = 11
vol_time = 5

 
params = {'timeInForce': 'PostOnly',}
 
vol_decimal = .4

# PULL IN ASK AND BID 
ask = n.ask_bid(symbol)[0]
bid = n.ask_bid(symbol)[1]
print(f'for {symbol}... ask: {ask} | bid: {bid}')


 
timeframe='15m'
limit=289
sma=20



# PULL IN THE DF_SMA - cause has all data we need
df_sma = n.df_sma(symbol, '15m', 289, 20) 

print('------Info----')
print(df_sma)
# PULL IN OPEN POSITIONS
open_pos = n.open_positions(symbol)

# CALCULATE SUPPORT & RESISTANCE BASE ON CLOSE
curr_support = df_sma['close'].min()
curr_resis = df_sma['close'].max()
print(f'support {curr_support} | resistance {curr_resis}')


# PULL IN PNL CLOSE
pnl_close = n.pnl_close(symbol)

# PULL iN THE KILL SWITCH
# kill_switch = n.kill_switch(symbol)

# FUNCTION SLEEP ON CLOSE
sleep_on_close = n.sleep_on_close(symbol, pause_time)

# RUN BOT
# CALC THE RETEST WHERE WE PUT ORDERS
# retest() buy_break_out, buy_break_down
def retest():
  print('creating retest number...') 
  
  '''
  if support breaks - SHORT, place asks right below (.1% == .001)
  if resis breaks - LONG, place bids right above (.1% == .001)
  '''
  
  buy_break_out = False
  sell_break_down = False
  breakoutprice = False
  breakdownprice = False
  
  # may want to do this on the bid..
  # if most current df resis <= df_without_last:
  if bid > df_sma['resis'].iloc[-1]:
    print(f'we are breaking out UP... buy at previous resis {curr_resis}')
    buy_break_out = True
    breakoutprice = int(df_sma['resis'].iloc[-1]) * 1.001
  elif bid < df_sma['support'].iloc[-1]:
    print(f'we are breaking out DOWN... sell at previous support {curr_support}')
    sell_break_down = True
    breakdownprice = int(df_sma['support'].iloc[-1]) * .999
  
  return buy_break_out, sell_break_down, breakoutprice, breakdownprice

def bot():
  n.pnl_close(symbol)

  askbid = n.ask_bid(symbol)
  ask = askbid[0]
  bid=  askbid[1]
  
  re_test = retest()
  break_out = re_test[0]
  break_down = re_test[1]
  breakoutprice = re_test[2]
  breakdownprice = re_test[3]
  print(f'breakout {break_out} {breakoutprice}| break down {break_down} {breakdownprice}')
  
  in_pos = open_pos[1]
  print(f'is in pos {in_pos}')
  curr_size = open_pos[2]
  curr_size = int(curr_size)
  
  curr_p = bid
  
  print(f'for {symbol} breakout {break_out} | break down {break_down} | inpos {in_pos} | size {curr_size} | price {curr_p}')

  if (in_pos == False) and (curr_size < pos_size):
    bingx.cancel_all_orders(symbol)
    askbid = n.ask_bid(symbol)
    ask = askbid[0]
    bid = askbid[1]
    
    # breakoutprice = re_test[2]
    # breakdownprice = re_test[3]
  
    if break_out == True:
      print('making an opening order as a BUY')
      print(f'{symbol} buy order of {pos_size} submitted @{breakoutprice}')
      bingx.create_limit_buy_order(symbol, pos_size, breakoutprice, params)
      print('order submitted so sleeping for 2mins...')
      time.sleep(120)
    elif break_down == True:
      print('making an opening order as a SELL')
      print(f'{symbol} sell order of {pos_size} submitted @{breakdownprice}')
      bingx.create_limit_sell_order(symbol, pos_size, breakdownprice, params)
      print('order submitted so sleeping for 2mins...')
      time.sleep(120)
    else:
      print('not submitting any orders... sleeping 1min')
      time.sleep(60)
  else:
    print('we are in position already so not making any orders...')

bot()
# scheduling the bot

schedule.every(28).seconds.do(bot)

while True:
  try:
    schedule.run_pending()
  except:
    print('+++++++++ MAYBE INTERNET PROBLEM +++++++++')
    time.sleep(30)
