#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import threading
import multiprocessing
from threading import Thread, current_thread, Event
from multiprocessing import Process, current_process, Pool
from multiprocessing.connection import Listener, Client
from IPython import display
import pandas as pd
from datetime import datetime as dt
from pandas.tseries.offsets import BDay, Day
from dataclasses import dataclass, fields, asdict, replace
import itertools
import datetime
import signal
# from matplotlib import pyplot as plt


# In[ ]:


import yfinance as yf
import pandas_ta as ta
import time, os, sys
import numpy as np
import pickle
from collections import deque
# from tqdm.notebook import tqdm


# In[ ]:


from .synfeed import Syn
# import plotly.graph_objects as go
# import plotly.express as px


# In[ ]:


from .featfuncs import feat_aug,add_addl_features_feed,add_ta_features_feed,add_sym_feature_feed
from .featfuncs import add_logical_features_feed,discretize_features_feed


# In[ ]:


from .india_calendar import IBDay


# In[ ]:


class BackFeed():
    def __init__(self,tickers=['WIPRO.NS','TCS.NS'],nw=1,nd=0,delay=0,interval='5m',
                verbose=False,synthetic=False,simple=True,sigma=0,mini_steps_per_step=1):
        self.mini_steps_per_step=mini_steps_per_step
        if synthetic: tickers=['SYN']
        self.verbose=verbose
        self.feedtype='back'
        self.interval=interval
        todayS=dt.today().strftime("%d-%b-%Y")
        todayD=pd.to_datetime(todayS)
        todayD=todayD-IBDay(1)+IBDay(1)
        todayS=todayD.strftime("%d-%b-%Y")
        self.tickers=tickers
        self.data={}
        self.counter=0
        self.mini_counter=0 # tracks mini_steps; num_mini_steps per main counter increment
        self.delay=delay
        self.dtD={}
        self.ncounter={t:0 for t in self.tickers}
        self.offsets={t:{} for t in self.tickers}
        self.eods={t:False for t in self.tickers}
        for t in self.tickers:
            if self.verbose:print('fetching ',t)
            dfL=[]
            try:
                for d in range(nw,0,-1):
                    if nd==0:
                        df=yf.Ticker(t).history(period='1d',interval=self.interval)
                        df['ticker']=t
                        df['datetime']=df.index
                        dfL=[df]
                        break
                    start=(todayD-IBDay(nd*d)).strftime("%Y-%m-%d")
                    end=(todayD-IBDay(nd*(d-1))).strftime("%Y-%m-%d")
                    if synthetic: 
                        df=Syn(simple=simple,sigma=sigma).history(start=start,end=end)
                    else: df=yf.Ticker(t).history(start=start,end=end,interval=self.interval)
                    limit=450
                    if self.interval=='5m': limit=40
                    if df.shape[0]>limit: 
                        # self.data[t]=df
                        df=df.fillna(0)
                        # self.dtD[t]=df.iloc[-1]['Date']
                        df['Date']=df.index.strftime('%d-%b-%Y')
                        df['ticker']=t
                        df['datetime']=df.index
                        dfL=dfL+[df]
                self.data[t]=pd.concat(dfL,axis=0)
                self.dtD[t]=self.data[t].iloc[0]['Date']
            except:
                pass
        self.tickers=[t for t in self.data]
        self.maxcount=max([self.data[t].shape[0] for t in self.tickers])
        self.df=pd.concat([self.data[t] for t in self.tickers])
        if self.df.loc[self.df['Date']==todayS].shape[0]>0:
            self.df.drop(self.df.loc[self.df['Date']==todayS].index,inplace=True)
        self.dates=self.df.Date.unique()[1:]
        # self.set_datesQ()
    def set_datesQ(self):
        dD={t:list(self.data[t].Date.unique()) for t in self.ndata}
        dD={t:dD[t] for t in dD if len(dD[t])>1}
        md=max([pd.to_datetime(dD[t][0]) for t in dD])
        for t in dD:
            if pd.to_datetime(dD[t][0])<pd.to_datetime(md): dD[t]=dD[t][1:]
        self.datesQ={t:deque(sorted(dD[t][1:],key=pd.to_datetime))for t in dD}
        self.tickers=[t for t in self.datesQ]
        self.ndata={t:self.ndata[t] for t in self.datesQ}
        self.data={t:self.data[t] for t in self.datesQ}
    def init_counters(self,date1=None,tickers=None):
        if tickers is None: t0=self.tickers[0]
        else: t0=tickers[0]
        if date1==None: date1=self.data[t0]['Date'].unique()[1]
        if tickers==None: tickers=self.tickers
        self.counter=self.offsets[t0][date1]
        for t in self.ndata:
            date1=self.data[t]['Date'].unique()[1]
            self.dtD[t]=self.datesQ[t].popleft()
            self.ncounter[t]=self.offsets[t][self.dtD[t]]
    def step(self):
        if self.mini_counter%self.mini_steps_per_step==0: 
            self.counter+=1
            for t in self.tickers:
                if self.ncounter[t]+1>=self.ndata[t][self.dtD[t]].shape[0]: self.eods[t]=True
                else: self.ncounter[t]+=1
        self.mini_counter+=1
        if not self.check_done(): self.check_eod_feed()
        time.sleep(self.delay)
    def check_eod_feed(self):
        retval=False
        if all([self.eods[t] for t in self.eods]):
            for t in self.eods: 
                if len(self.datesQ[t])>0:
                    self.dtD[t]=self.datesQ[t].popleft()
                    self.ncounter[t]=self.offsets[t][self.dtD[t]]
                    self.eods[t]=False
            retval=True
        return retval
    def get(self,t):
        if self.counter<self.data[t].shape[0]: idx=self.counter
        else: idx=-1
        return self.data[t].iloc[idx]
    def getData(self,t):
        if self.counter<self.data[t].shape[0]:
            return self.data[t].iloc[0:self.counter+1]
        else: return self.data[t]
    def getBasket(self,date=None,client=None):
        if date==None:
            getfL=[self.get(t) for t in self.tickers]
            dfL=[pd.DataFrame([getf.values],columns=getf.index) for getf in getfL]
            return pd.concat(dfL,axis=0)
        else:
            getfL=[self.getDataN(t,date).iloc[-1:] for t in self.tickers]
            dfL=[pd.DataFrame(getf.values,columns=getf.columns) for getf in getfL]
            return pd.concat(dfL,axis=0)
    def check_done(self):
        if self.counter>=self.maxcount: return True
        else: return False
    def getN(self,t,d):
        if self.ncounter[t]<self.ndata[t][d].shape[0]: idx=self.ncounter[t]
        else: idx=-1
        return self.ndata[t][d].iloc[idx]
    def getDataN(self,t,d):
        if t not in self.ndata: return pd.DataFrame()
        if not d in self.ndata[t]: return pd.DataFrame()
        if self.ncounter[t]<self.ndata[t][d].shape[0]:
            return self.ndata[t][d].iloc[0:self.ncounter[t]+1]
        else: return self.ndata[t][d]
    def update_tickers_feed(self,tickers):
        self.tickers=tickers
        self.dtD={t:self.dtD[t] for t in tickers}
        self.data={t:self.data[t] for t in tickers}
        self.ndata={t:self.ndata[t] for t in tickers}
        self.ncounter={t:self.ncounter[t] for t in tickers}
        self.eods={t:self.eods[t] for t in tickers}
        self.datesQ={t:self.datesQ[t] for t in tickers}
    def plot_ticker_date(self,ticker,date,show_prev=False):
        global fig
        feed=self
        dff=feed.ndata[ticker][date]
        df=dff.loc[dff['Date']==date]
        fig = go.Figure(data=
            [go.Candlestick(x = df.index,
                            open  = df["Open"],
                            high  = df["High"],
                            low   = df["Low"],
                            close = df["Close"])]
        )
        fig.update_layout(
            title=f'{ticker} on {date}',
            yaxis_title="Price"
        )
        if show_prev: 
            pdate=(pd.to_datetime(date)-IBDay(1)).strftime("%d-%b-%Y")
            df=dff.loc[dff['Date']==pdate]
            fig1 = go.Figure(data=
                [go.Candlestick(x = df.index,
                                open  = df["Open"],
                                high  = df["High"],
                                low   = df["Low"],
                                close = df["Close"])]
            )
            fig1.update_layout(
                title=f'previous day',
                yaxis_title="Price"
            )
        fig.show()
        if show_prev: fig1.show()
        return


# In[ ]:


class LiveFeed():
    def __init__(self,tickers=['WIPRO.NS','TCS.NS'],period='2d',interval='1m',
                 delay=1,discrete_features=False,DkD=None):
        self.discrete_features=discrete_features
        self.DkD=DkD
        self.feedtype='live'
        self.tickers=tickers
        self.data={}
        self.period=period
        self.interval=interval
        self.delay=delay
        self.counter=0
        self.dtD={}
        self.offsets={t:{} for t in self.tickers}
        todayS=dt.today().strftime("%d-%b-%Y")
        self.todayS=todayS
        todayD=pd.to_datetime(todayS)
        self.todayD=todayD-IBDay(1)+IBDay(1)
        self.step(init=True)
    def init_counters(self):
        t0=self.tickers[0]
        if len(self.data[t0]['Date'].unique())>1:
            date1=self.data[t0]['Date'].unique()[1]
            self.counter=self.offsets[t0][date1]
        else:
            self.counter=0
        self.dtD={t:self.get(t)['Date'] for t in self.tickers}
    def step(self,init=False):
        if init==False: time.sleep(self.delay)
        self.counter+=1
        for t in self.tickers:
            try:
                end=(self.todayD+IBDay(1)).strftime("%Y-%m-%d")
                start=(self.todayD-IBDay(1)).strftime("%Y-%m-%d")
                df=yf.Ticker(t).history(start=start, end=end,interval=self.interval)
                df['Date']=df.index.strftime('%d-%b-%Y')
                df['ticker']=t
                df['datetime']=df.index
                NDays=len(df['Date'].unique())
                if self.interval=='5m' and NDays>1: limit=20
                elif NDays>1: limit=225
                else: limit=0
                if df.shape[0]>limit:
                    df=df.fillna(0)
                    self.data[t]=df
                    self.dtD[t]=df.iloc[-1]['Date']
            except:
                pass
        if init==True: 
            self.tickers=[t for t in self.data]
            self.df=pd.concat([self.data[t] for t in self.tickers])
            self.dates=self.df.Date.unique()[1:]
        add_ta_features_feed(self)
        add_sym_feature_feed(self,tickers=self.tickers,live=True)
        add_logical_features_feed(self)
        if self.discrete_features: discretize_features_feed(self,self.DkD,'alllog')
        # if init==False: time.sleep(self.delay)
    def getData(self,t):
        return self.data[t]
    def get(self,t):
        return self.data[t].iloc[-1]
    def getBasket(self,date=None):
        if date==None:
            getfL=[self.get(t) for t in self.tickers]
            dfL=[pd.DataFrame([getf.values],columns=getf.index) for getf in getfL]
        else:
            getfL=[self.getDataN(t,date).iloc[-1:] for t in self.tickers]
            dfL=[pd.DataFrame(getf.values,columns=getf.columns) for getf in getfL]
        return pd.concat(dfL,axis=0)
    def getDataN(self,t,d):
        try:
            retval=self.ndata[t][d]
        except:
            return pd.DataFrame()
        return self.ndata[t][d]
    def getN(self,t,d):
        return self.ndata[t][d].iloc[-1]
    def check_done(self):
        return False
    def update_tickers_feed(self,tickers):
        self.tickers=tickers
        self.dtD={t:self.dtD[t] for t in tickers}
        self.data={t:self.data[t] for t in tickers}
        self.ndata={t:self.ndata[t] for t in tickers}


# In[ ]:


class DataFeed():
    def __init__(self,tickers=['WIPRO.NS','TCS.NS'],
                 datafile='./DataLocal/algo_fin_new/labeled_data_02-Mar-2022.csv',
                dfgiven=False,df=None,delay=0,verbose=False):
        self.verbose=verbose
        self.feedtype='data'
        self.tickers=tickers
        self.data={}
        self.counter=0
        self.delay=delay
        self.dtD={}
        self.ncounter={t:0 for t in self.tickers}
        self.offsets={t:{} for t in self.tickers}
        self.eods={t:False for t in self.tickers}
        if dfgiven==False: self.df=pd.read_csv(datafile)
        else: self.df=df
        self.df['datetime']=pd.to_datetime(self.df['Datetime'])
        self.dates=df.Date.unique()[1:]
        for t in self.tickers:
            if self.verbose:print('fetching ',t)
            self.data[t]=self.df.loc[self.df['ticker']==t]
            # self.data[t].index=pd.to_datetime(self.data[t].datetime)
            self.data[t].index=self.data[t].datetime
        self.maxcount=max([self.data[t].shape[0] for t in self.tickers])
        # self.datesQ={t:deque(sorted(list(self.data[t].Date.unique()[1:]),key=pd.to_datetime))
        #              for t in self.tickers}
        # self.set_datesQ()
    def set_datesQ(self):
        self.datesQ={t:deque(sorted(list(self.data[t].Date.unique()[1:]),key=pd.to_datetime))
                     for t in self.tickers}
    def init_counters(self,date1=None,tickers=None):
        if tickers is None: t0=self.tickers[0]
        else: t0=tickers[0]
        idx=1
        if date1==None:
            counter,idx=0,0
            while counter==0:
                idx+=1
                date1=self.data[t0]['Date'].unique()[idx]
                counter=self.offsets[t0][date1]
            self.counter=counter
        else: self.counter=self.offsets[t0][date1]
        for t in self.tickers:
            self.dtD[t]=self.datesQ[t].popleft()
            self.ncounter[t]=self.offsets[t][self.dtD[t]]
    def step(self):
        self.counter+=1
        for t in self.tickers:
            if self.ncounter[t]+1>=self.ndata[t][self.dtD[t]].shape[0]: self.eods[t]=True
            else: self.ncounter[t]+=1
        if not self.check_done(): self.check_eod_feed()
        time.sleep(self.delay)
    def check_eod_feed(self):
        retval=False
        if all([self.eods[t] for t in self.eods]):
            for t in self.eods: 
                if len(self.datesQ[t])>0: 
                    self.dtD[t]=self.datesQ[t].popleft()
                    self.ncounter[t]=self.offsets[t][self.dtD[t]]
                    self.eods[t]=False
            retval=True
        return retval
    def get(self,t):
        if self.counter<self.data[t].shape[0]: idx=self.counter
        else: idx=-1
        return self.data[t].iloc[idx]
    def getData(self,t):
        if self.counter<self.data[t].shape[0]:
            return self.data[t].iloc[0:self.counter+1]
        else: return self.data[t]
    def getBasket(self,date=None,client=None):
        if date==None:
            getfL=[self.get(t) for t in self.tickers]
            dfL=[pd.DataFrame([getf.values],columns=getf.index) for getf in getfL]
        else:
            getfL=[self.getDataN(t,date).iloc[-1:] for t in self.tickers]
            dfL=[pd.DataFrame(getf.values,columns=getf.columns) for getf in getfL]
        return pd.concat(dfL,axis=0)
    def check_done(self):
        if self.counter>=self.maxcount: return True
        else: return False
    def getN(self,t,d):
        if self.ncounter[t]<self.ndata[t][d].shape[0]: idx=self.ncounter[t]
        else: idx=-1
        return self.ndata[t][d].iloc[idx]
    def getDataN(self,t,d):
        if t not in self.ndata: return pd.DataFrame()
        if not d in self.ndata[t]: return pd.DataFrame()
        if self.ncounter[t]<self.ndata[t][d].shape[0]:
            return self.ndata[t][d].iloc[0:self.ncounter[t]+1]
        else: return self.ndata[t][d]
    def update_tickers_feed(self,tickers):
        self.tickers=tickers
        self.dtD={t:self.dtD[t] for t in tickers}
        self.data={t:self.data[t] for t in tickers}
        self.ndata={t:self.ndata[t] for t in tickers}
        self.ncounter={t:self.ncounter[t] for t in tickers}
        self.eods={t:self.eods[t] for t in tickers}
        self.datesQ={t:self.datesQ[t] for t in tickers}


# In[ ]:


def clean_feed(feed,ticker):
    #removes current date and last date if empty dataframe, for each ticker
    #to be called before add_addl_features; called from backtest; 
    feed_dates=feed.data[ticker].Date.unique()
    if feed.data[ticker].loc[feed.data[ticker]['Date']==feed_dates[-1]].shape[0]<10:
        feed.data[ticker]=feed.data[ticker].drop(
                feed.data[ticker].index[-1])
    todayS=pd.to_datetime(dt.today()).strftime('%d-%b-%Y')
    if feed.feedtype=='back':
        df=feed.data[ticker]
        feed.data[ticker]=feed.data[ticker].drop(df.loc[df['Date']==todayS].index)


# In[ ]:


def clean_feed_tickers(feed,limit=100):
    #removes tickers where size of data for a day+prev-day is less than limit
    #to be called before add_addl_feature; used in tradeserver
    if feed.interval=='5m': limit=20
    dropticks=[]
    for t in feed.tickers:
        dfa=feed.data[t]
        for d in dfa['Date'].unique():
            pdt=pd.to_datetime(d)
            pdtp=pdt-IBDay(1)
            df=dfa.loc[(pd.to_datetime(dfa['Date'])<=pdt)&
                       (pd.to_datetime(dfa['Date'])>=pdtp)]
            if len(df)<limit: dropticks+=[t]
    feed.tickers=[t for t in feed.tickers if t not in dropticks]
    return feed


# In[ ]:


def clean_feed_sim(feed,todayS=None):
    #removes current day or given day (for debugging cases) from feed 
    #to be called after add_addl_features; used in tradeserver
    #also resets datesQ (to remove what clean_feed_tickers may have dropped earlier)
    for ticker in feed.tickers:
        feed_dates=feed.data[ticker].Date.unique()
        if feed.data[ticker].loc[feed.data[ticker]['Date']==feed_dates[-1]].shape[0]<10:
            feed.data[ticker]=feed.data[ticker].drop(
                    feed.data[ticker].index[-1])
        if todayS==None: todayS=pd.to_datetime(dt.today()).strftime('%d-%b-%Y')
        if feed.feedtype=='back':
            df=feed.data[ticker]
            feed.data[ticker]=feed.data[ticker].drop(df.loc[df['Date']==todayS].index)
        for date in feed_dates:
            if date in feed.ndata[ticker]: 
                df=feed.ndata[ticker][date]
                feed.ndata[ticker][date]=feed.ndata[ticker][date].drop(
                    df.loc[df['Date']==todayS].index)
    feed.set_datesQ()


# In[ ]:


def clean_feed_nulls(feed):
    for t in feed.ndata:
        for d in feed.ndata[t]:
            if feed.ndata[t][d].isnull().values.any(): 
                feed.ndata[t][d]=feed.ndata[t][d].fillna(1)
                # print(t,d)
            if feed.ndata[t][d].isin([-np.inf,np.inf]).values.any():
                feed.ndata[t][d]=feed.ndata[t][d].replace([np.inf, -np.inf],1)
                # print(t,d)


# In[ ]:


def plot_ticker_date(feed,ticker,date,show_prev=False,ohlc=['Open','High','Low','Close']):
    global fig
    dff=feed.ndata[ticker][date]
    df=dff.loc[dff['Date']==date]
    fig = go.Figure(data=
        [go.Candlestick(x = df.index,
                        open  = df[ohlc[0]],
                        high  = df[ohlc[1]],
                        low   = df[ohlc[2]],
                        close = df[ohlc[3]])]
    )
    fig.update_layout(
        title=f'{ticker} on {date}',
        yaxis_title="Price"
    )
    if show_prev: 
        pdate=(pd.to_datetime(date)-IBDay(1)).strftime("%d-%b-%Y")
        df=dff.loc[dff['Date']==pdate]
        fig1 = go.Figure(data=
            [go.Candlestick(x = df.index,
                            open  = df[ohlc[0]],
                            high  = df[ohlc[1]],
                            low   = df[ohlc[2]],
                            close = df[ohlc[3]])]
        )
        fig1.update_layout(
            title=f'previous day',
            yaxis_title="Price"
        )
    fig.show()
    if show_prev: fig1.show()
    return


# Debugging

# In[ ]:


# tickers=['RELIANCE.NS',
#  'DMART.NS',
#  'NESTLEIND.NS',
#  'ULTRACEMCO.NS',
#  'KOTAKBANK.NS']


# In[ ]:


# tickers=['RELIANCE.NS',
#  'DMART.NS',
#  'NESTLEIND.NS',
#  'ULTRACEMCO.NS',
#  'KOTAKBANK.NS',
#  'TCS.NS',
#  'MARUTI.NS',
#  'NTPC.NS',
#  'SBILIFE.NS',
#  'ICICIBANK.NS',
#  'BAJAJ-AUTO.NS',
#  'HDFCLIFE.NS',
#  'POWERGRID.NS',
#  'COALINDIA.NS',
#  'BAJAJFINSV.NS',
#  'HDFCBANK.NS',
#  'HDFC.NS',
#  'BAJFINANCE.NS',
#  'ICICIPRULI.NS',
#  'HINDUNILVR.NS',
#  'IOC.NS',
#  'BPCL.NS',
#  'SBICARD.NS',
#  'SHREECEM.NS',
#  'LT.NS',
#  'ICICIGI.NS',
#  'ONGC.NS',
#  'WIPRO.NS',
#  'PGHH.NS',
#  'HAL.NS',
#  'SBIN.NS',
#  'BAJAJHLDNG.NS',
#  'MRF.NS',
#  'ACC.NS',
#  'PAGEIND.NS',
#  'GILLETTE.NS',
#  'ITC.NS',
#  'INDIGO.NS',
#  'DRREDDY.NS',
#  'PETRONET.NS',
#  'BOSCHLTD.NS',
#  'AXISBANK.NS',
#  'TECHM.NS',
#  'INDUSINDBK.NS',
#  'ASIANPAINT.NS',
#  'DCM.NS',
#  'OBCL.NS',
#  'MUTHOOTFIN.NS',
#  'PFC.NS',
#  'SUNPHARMA.NS',
#  'HONAUT.NS',
#  'SANOFI.NS',
#  'ABBOTINDIA.NS',
#  'NDTV.NS',
#  'COLPAL.NS',
#  'TV18BRDCST.NS',
#  'TRENT.NS',
#  'WOCKPHARMA.NS',
#  'SIEMENS.NS',
#  'BHARTIARTL.NS',
#  'AARTIIND.NS',
#  'TATACHEM.NS',
#  'VOLTAS.NS',
#  'PEL.NS',
#  'JUNIORBEES.NS',
#  'DABUR.NS',
#  'TATAMTRDVR.NS',
#  'BANKINDIA.NS',
#  'LICHSGFIN.NS',
#  'ZEEL.NS',
#  'TATAMOTORS.NS',
#  'JSWENERGY.NS',
#  'MCX.NS',
#  'KPRMILL.NS',
#  'PRAJIND.NS',
#  'NIITLTD.NS',
#  'NOCIL.NS',
#  'LUPIN.NS',
#  'ASHOKLEY.NS',
#  'VIPIND.NS',
#  'IRB.NS',
#  'HCC.NS',
#  'NHPC.NS']


# In[ ]:


# import warnings
# warnings.simplefilter("ignore")


# In[ ]:


# feed=LiveFeed(tickers=tickers,interval='5m',delay=1)


# In[ ]:


# feed.init_counters()


# In[ ]:


# feed.dtD


# In[ ]:


# min([pd.to_datetime(feed.dtD[t]) for t in feed.tickers]).strftime('%d-%b-%Y')


# In[ ]:




