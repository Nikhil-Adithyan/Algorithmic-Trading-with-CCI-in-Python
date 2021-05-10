import pandas as pd
import requests
import pandas_datareader as web
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
from math import floor
from termcolor import colored as cl

plt.rcParams['figure.figsize'] = (20, 10)
plt.style.use('fivethirtyeight')

def get_historical_data(symbol, start_date = None):
    api_key = open(r'api_key.txt')
    api_url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&apikey={api_key}&outputsize=full'
    raw_df = requests.get(api_url).json()
    df = pd.DataFrame(raw_df[f'Time Series (Daily)']).T
    df = df.rename(columns = {'1. open': 'open', '2. high': 'high', '3. low': 'low', '4. close': 'close', '5. adjusted close': 'adj close', '6. volume': 'volume'})
    for i in df.columns:
        df[i] = df[i].astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.iloc[::-1].drop(['7. dividend amount', '8. split coefficient'], axis = 1)
    if start_date:
        df = df[df.index >= start_date]
    return df

fb = get_historical_data('FB', '2020-01-01')
print(fb)

def get_cci(symbol, n, start_date):
    api_key = open(r'api_key.txt')
    url = f'https://www.alphavantage.co/query?function=CCI&symbol={symbol}&interval=daily&time_period={n}&apikey={api_key}'
    raw = requests.get(url).json()
    df = pd.DataFrame(raw['Technical Analysis: CCI']).T.iloc[::-1]
    df = df[df.index >= start_date]
    df.index = pd.to_datetime(df.index)
    df = df.astype(float)
    return df

fb['cci'] = get_cci('FB', 20, '2020-01-01')
fb = fb.dropna()
print(fb.tail())

ax1 = plt.subplot2grid((10,1), (0,0), rowspan = 5, colspan = 1)
ax2 = plt.subplot2grid((10,1), (6,0), rowspan = 4, colspan = 1)
ax1.plot(fb['close'])
ax1.set_title('FACEBOOK SHARE PRICE')
ax2.plot(fb['cci'], color = 'orange')
ax2.set_title('FACEBOOK CCI 20')
ax2.axhline(150, linestyle = '--', linewidth = 1, color = 'black')
ax2.axhline(-150, linestyle = '--', linewidth = 1, color = 'black')
plt.show()

def implement_cci_strategy(prices, cci):
    buy_price = []
    sell_price = []
    cci_signal = []
    signal = 0
    
    lower_band = (-150)
    upper_band = 150
    
    for i in range(len(prices)):
        if cci[i-1] > lower_band and cci[i] < lower_band:
            if signal != 1:
                buy_price.append(prices[i])
                sell_price.append(np.nan)
                signal = 1
                cci_signal.append(signal)
            else:
                buy_price.append(np.nan)
                sell_price.append(np.nan)
                cci_signal.append(0)
                
        elif cci[i-1] < upper_band and cci[i] > upper_band:
            if signal != -1:
                buy_price.append(np.nan)
                sell_price.append(prices[i])
                signal = -1
                cci_signal.append(signal)
            else:
                buy_price.append(np.nan)
                sell_price.append(np.nan)
                cci_signal.append(0)
                
        else:
            buy_price.append(np.nan)
            sell_price.append(np.nan)
            cci_signal.append(0)
            
    return buy_price, sell_price, cci_signal

buy_price, sell_price, cci_signal = implement_cci_strategy(fb['close'], fb['cci'])

ax1 = plt.subplot2grid((10,1), (0,0), rowspan = 5, colspan = 1)
ax2 = plt.subplot2grid((10,1), (6,0), rowspan = 4, colspan = 1)
ax1.plot(fb['close'], color = 'skyblue', label = 'FB')
ax1.plot(fb.index, buy_price, marker = '^', markersize = 12, linewidth = 0, label = 'BUY SIGNAL', color = 'green')
ax1.plot(fb.index, sell_price, marker = 'v', markersize = 12, linewidth = 0, label = 'SELL SIGNAL', color = 'r')
ax1.set_title('FACEBOOK SHARE PRICE')
ax1.legend()
ax2.plot(fb['cci'], color = 'orange')
ax2.set_title('FACEBOOK CCI 20')
ax2.axhline(150, linestyle = '--', linewidth = 1, color = 'black')
ax2.axhline(-150, linestyle = '--', linewidth = 1, color = 'black')
plt.show()

position = []
for i in range(len(cci_signal)):
    if cci_signal[i] > 1:
        position.append(0)
    else:
        position.append(1)
        
for i in range(len(fb['close'])):
    if cci_signal[i] == 1:
        position[i] = 1
    elif cci_signal[i] == -1:
        position[i] = 0
    else:
        position[i] = position[i-1]
        
cci = fb['cci']
close_price = fb['close']
cci_signal = pd.DataFrame(cci_signal).rename(columns = {0:'cci_signal'}).set_index(fb.index)
position = pd.DataFrame(position).rename(columns = {0:'cci_position'}).set_index(fb.index)

frames = [close_price, cci, cci_signal, position]
strategy = pd.concat(frames, join = 'inner', axis = 1)

print(strategy.head())

fb_ret = pd.DataFrame(np.diff(fb['close'])).rename(columns = {0:'returns'})
cci_strategy_ret = []

for i in range(len(fb_ret)):
    returns = fb_ret['returns'][i]*strategy['cci_position'][i]
    cci_strategy_ret.append(returns)
    
cci_strategy_ret_df = pd.DataFrame(cci_strategy_ret).rename(columns = {0:'cci_returns'})
investment_value = 100000
number_of_stocks = floor(investment_value/fb['close'][-1])

cci_investment_ret = []

for i in range(len(cci_strategy_ret_df['cci_returns'])):
    returns = number_of_stocks*cci_strategy_ret_df['cci_returns'][i]
    cci_investment_ret.append(returns)

cci_investment_ret_df = pd.DataFrame(cci_investment_ret).rename(columns = {0:'investment_returns'})
total_investment_ret = round(sum(cci_investment_ret_df['investment_returns']), 2)
profit_percentage = round((total_investment_ret/investment_value)*100, 2)

print(cl('Profit gained from the CCI strategy by investing $100k in FB : {}'.format(total_investment_ret), attrs = ['bold']))
print(cl('Profit percentage of the CCI strategy : {}%'.format(profit_percentage), attrs = ['bold']))