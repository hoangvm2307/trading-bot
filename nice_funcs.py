import ccxt, json
import pandas as pd
import numpy as np
import dontshare_config as ds
from datetime import date, datetime, timezone, tzinfo
import time, schedule

bingx = ccxt.bingx({
  'enableRateLimit': True,
  'apiKey': ds.bingx_KEY,
  'secret': ds.bingx_SECRET,
})

symbol = 'BTC/USDT'
index_pos = 0 # CHANGE BASED ON WHAT ASSET

# The time between trade
pause_time = 60

# for volume calc Vol_repeat * vol_time = TIME of volume collection
vol_repeat=11
vol_time=5

pos_size = 100 # 125, 75,
params = {'timeInForce': 'PostOnly',}
target = 35
max_loss = -55
vol_decimal = .4

# For df
timeframe = '4h'
limit=100
sma=20

# ask_bid()[0] = ask, [1] = bid
# ask_bid(symbol) if none given then default
def ask_bid(symbol=symbol):
  ob = bingx.fetch_order_book(symbol)
  
  bid = ob['bids'][0][0]
  ask = ob['asks'][0][0]
  print(f'this is the ask for {symbol} {ask}')
  
  return ask, bid

# returns: df with sma (can customize with below)
# call: daily_sma(symbol, timeframe, limit, sma) # if not passed, uses default
def df_sma(symbol=symbol, timeframe=timeframe, limit=limit, sma=sma):
  print('starting indis...')
  
  bars = bingx.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
  #print(bars)
  
  df_sma = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
  df_sma['timestamp'] = pd.to_datetime(df_sma['timestamp'], unit='ms')
  
  # DAILY SMA - 20 day
  df_sma[f'sma{sma}_{timeframe}'] = df_sma.close.rolling(sma).mean()

  # If bid < the 20 day sma then = BEARISH, if bid > 20 day sma = BULLISH
  bid = ask_bid(symbol)[1]
  
  # If sma > bid = SELL, if sma < bid = BUY
  df_sma.loc[df_sma[f'sma{sma}_{timeframe}'] > bid, 'sig'] = 'SELL'
  df_sma.loc[df_sma[f'sma{sma}_{timeframe}'] < bid, 'sig'] = 'BUY'
  
  df_sma['support'] = df_sma[:-2]['close'].min()
  df_sma['resis'] = df_sma[:-2]['close'].max()
  
  print(df_sma)
  
  return df_sma

# returns: open_positions() open_positions, openpos_bool, openpos_size, long, index_pos
# TODO - Figure out a way to sort through json (rando) and assign an index
# Make a function that loops through dictionary and does
def open_positions(symbol=symbol):
    symbol_index_map = {
        'BTC/USDT': 3,
        'APE/USDT': 1,
        'ETH/USDT': 2,
        'DOGE/USDT': 0
    }
    
    index_pos = symbol_index_map.get(symbol)
    if index_pos is None:
        print(f"Error: Unknown symbol {symbol}")
        return None, False, 0, None

    params = {'type': 'swap', 'code': 'USD'}
    try:
        balance = bingx.fetch_balance()
        print(f'Balance: {balance}')
        # open_positions = balance['info']['data']['positions']
        open_positions = bingx.fetch_positions()
        print(f'Open positions: {open_positions}')
        position = open_positions[index_pos]
        openpos_side = position['side']
        openpos_size = position['size']
        
        if openpos_side == 'Buy':
            openpos_bool, long = True, True
        elif openpos_side == 'Sell':
            openpos_bool, long = True, False
        else:
            openpos_bool, long = False, None
        
        print(f'Open positions: {open_positions} | '
              f'Open position: {openpos_bool} | '
              f'Position size: {openpos_size} | '
              f'Long: {long}')
        
        return open_positions, openpos_bool, openpos_size, long, index_pos
    
    except Exception as e:
        print(f"Error fetching position data: {e}")
        return None, False, 0, None


# Usage
# open_positions, openpos_bool, openpos_size, long = open_positions(symbol)


#NOTE - I marked out 2 orders below and the cancel, need to unmark before live
# returns: kill_switch() nothing
# kill_switch: pass in (symbol) if no symbol uses default
def kill_switch(symbol=symbol):
  print('starting the killing switch')
  open_pos = open_positions(symbol)[1] # true or false
  kill_size = open_positions(symbol)[2] # size thats open
  long = open_positions(symbol)[3] # true or false
  
  print(f'open_pos {open_pos} | long {long} | kill_size {kill_size}')
  
  while open_pos == True:
    print('starting kill switch loop til limit fil...')
    temp_df = pd.DataFrame()
    print('just made a temp df')

    # bingx.cancel_all_orders(symbol)
    open_pos = open_positions(symbol)[1]
    long = open_positions(symbol)[3] # true or false
    kill_size = open_positions(symbol)[2]
    kill_size= int(kill_size)
    
    ask = ask_bid(symbol)[0]
    bid = ask_bid(symbol)[1]

    if long == False:
      # bingx.create_limit_buy_order(symbol, kill_size, bid, params)
      print(f'just made a BUY to CLOSE order of {kill_size} {symbol} at ${bid}')
      print('sleeping for 30 seconds to see if it fills...')
      time.sleep(30)
    elif long == True:
      # bingx.create_limit_sell_order(symbol, kill_size, ask, params)
      print(f'just made a SELL to CLOSE order of {kill_size} {symbol} at ${ask}')
      print('sleeping for 30 seconds to see if it fills...')
      time.sleep(30)
    else:
      print('+++++ SOMETHING I DIDNT EXPECT IN KILL SWITCH FUNCTION')
    
    open_pos = open_positions(symbol)[1]

# returns nothing
# sleep_on_close(symbol=symbol, pause_time=pause_time) # pause in mins
def sleep_on_close(symbol=symbol, pause_time=pause_time):
  '''
  this func pulls close orders, then if last close was in last 59min
  then it sleeps for 1m
  sincelasttrade= minnutes since last trade
  '''

  closed_orders = bingx.fetch_closed_orders(symbol)
  print(f'closed orders: {closed_orders}')

  for ord in closed_orders[-1::-1]:
    sincelasttrade = pause_time - 1 # how long we pause
    
    filled = False
    
    status = ord['info']['status']
    txttime = ord['info']['time']
    txttime = int(txttime)
    txttime = round((txttime/1000000000))
    print(f'for {symbol} this is the status of the order {status} with epoch {txttime}')
    print('next iteration...')
    print('-----')

    if status == 'Filled':
      print('FOUND the order with last fill..')
      print(f'for {symbol} this is the time {txttime} this is the orderstatus {status}')
      orderbook = bingx.fetch_order_book(symbol)
      ex_timestamp = orderbook['timestamp'] # in ms
      ex_timestamp = int(ex_timestamp / 1000)
      print('---- below is the transaction time then exchange epoch time')
      print(txttime)
      print(ex_timestamp)
      
      time_spread = (ex_timestamp - txttime) / 60

      if time_spread < sincelasttrade:
        # print('time since last trade is less than time spread')
        # if in pos is true, put a close order here
        # if in_pos == True:
        
        sleepy = round(sincelasttrade - time_spread) * 60
        sleepy_min = sleepy / 60
        
        print(f'the time spread is less than {sincelasttrade} mins its between {time_spread}mins.. SO we sleep')
        time.sleep(60)
      else:
        print(f'its been {time_spread} mins since last fill so not sleeping ')
      break
    else:
      continue  
  
  print(f'done with the sleep on close function for {symbol}..')
sleep_on_close()
# returns vol_under_dec
def order_book(symbol=symbol, vol_repeat=vol_repeat, vol_time=vol_time):
    print(f'Fetching order book data for {symbol}...')
    
    df = pd.DataFrame()
    
    for _ in range(vol_repeat):
        ob = bingx.fetch_order_book(symbol)
        bids, asks = ob['bids'], ob['asks']
        
        bid_vol = sum(vol for _, vol in bids)
        ask_vol = sum(vol for _, vol in asks)
        
        temp_df = pd.DataFrame({'bid_vol': [bid_vol], 'ask_vol': [ask_vol]})
        df = pd.concat([df, temp_df], ignore_index=True)
        
        print(temp_df)
        print('\n------\n')
        
        time.sleep(vol_time)
    
    print('Done collecting volume data for bids and asks...')
    print('Calculating the sums...')
    
    total_bidvol = df['bid_vol'].sum()
    total_askvol = df['ask_vol'].sum()
    
    seconds = vol_time * vol_repeat
    mins = round(seconds / 60, 2)
    print(f'Last {mins}m for {symbol} total bid vol: {total_bidvol} | ask vol: {total_askvol}')
    
    if total_bidvol > total_askvol:
        control_dec = total_askvol / total_bidvol
        print(f'Bulls are in control: {control_dec:.4f}...')
        bullish = True
    else:
        control_dec = total_bidvol / total_askvol
        print(f'Bears are in control: {control_dec:.4f}...')
        bullish = False
    
    open_posi = open_positions(symbol)
    openpos_tf, long = open_posi[1], open_posi[3]
    print(f'openpos_tf: {openpos_tf} | long: {long}')
    
    vol_under_dec = None
    if openpos_tf:
        position_type = 'long' if long else 'short'
        print(f'We are in a {position_type} position...')
        if control_dec < vol_decimal:
            vol_under_dec = True
        else:
            print('Volume is not under dec so setting vol_under_dec to False')
            vol_under_dec = False
    else:
        print('We are not in a position...')
    
    print(f'vol_under_dec: {vol_under_dec}')
    return vol_under_dec

# pnl_close()[0] pnlclose [1]in_pos [2]size [3]long TF
def pnl_close(symbol=symbol):
    print(f'Checking exit conditions for {symbol}...')

    try:
        params = {'type': 'swap', 'code': 'USD'}
        positions = bingx.fetch_positions(params=params)
        
        _, _, _, _, index_pos = open_positions(symbol)
        position = positions[index_pos]
        
        side = position['side']
        size = position['contracts']
        entry_price = float(position['entryPrice'])
        leverage = float(position['leverage'])
        current_price = ask_bid(symbol)[1]
        
        print(f'Side: {side} | Entry Price: {entry_price} | Leverage: {leverage}')
        
        long = side == 'long'
        diff = current_price - entry_price if long else entry_price - current_price
        
        try:
            perc = round((diff / entry_price) * leverage * 100, 2)
        except ZeroDivisionError:
            perc = 0
        
        print(f'PNL percentage for {symbol}: {perc}%')
        
        in_pos = perc != 0
        pnlclose = False
        
        if perc > 0:
            print(f'Winning position for {symbol}')
            if perc > target:
                print(f'Hit target of {target}%. Checking volume before closing...')
                pnlclose = True
                if order_book(symbol):  # Assuming this returns True if volume is under threshold
                    print(f'Volume under threshold of {vol_decimal}. Waiting 30 seconds.')
                    time.sleep(30)
                else:
                    print('Starting kill switch due to hitting target.')
                    kill_switch()
            else:
                print('Target not yet reached.')
        elif perc < 0:
            if perc <= max_loss:
                print(f'Loss of {perc}% exceeds max loss. Starting kill switch...')
                kill_switch()
            else:
                print(f'Current loss: {perc}%. Holding as it\'s within max loss limit.')
        else:
            print('Not in position.')
        
        if in_pos:
            timeframe = '15m'
            df_f = df_sma(symbol, timeframe, 100, 20)
            last_sma15 = int(df_f.iloc[-1][f'sma{sma}_{timeframe}'])
            curr_bid = int(ask_bid(symbol)[1])
            sl_val = last_sma15 * 1.008
            
            print(f'Last SMA15: {last_sma15} | Current Bid: {curr_bid} | Stop Loss Value: {sl_val}')
            
            # Commented out as per your note
            # if curr_bid > sl_val:
            #     print('Current bid above stop loss value. Starting kill switch...')
            #     kill_switch(symbol)
            # else:
            #     print('Holding position...')
        else:
            print('Not in a position.')
        
        print(f'Finished checking PNL close for {symbol}.')
        return pnlclose, in_pos, size, long

    except Exception as e:
        print(f"Error in pnl_close for {symbol}: {e}")
        return False, False, 0, None