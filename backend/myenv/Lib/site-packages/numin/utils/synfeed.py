#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd
# import plotly.express as px
import os
from datetime import datetime,timedelta
import pytz


# In[ ]:

from .india_calendar import IBDay


# In[ ]:


class OUProcess():
    def __init__(self,mu=0,alpha=1,sigma=1,dt=1.0):
        self.mu,self.alpha,self.sigma=mu,alpha,sigma
        self.dt=1
    def fetch(self,s,n):
        # generate n steps of the process starting from s
        S=np.zeros(n)
        S[0]=s
        N=np.random.randn(n)
        # print(N)
        sdev=self.sigma*np.sqrt(self.dt)
        for i in range(0, n-1):
            S[i+1] = S[i] + self.alpha*(self.mu-S[i])*self.dt + sdev*N[i]
        return S


# Generation process:
# 
# Generate two day at a time; at start of each two day interval target delta is drawn from normal with mean 0 and std avg_delta (=.3) Target mu is set at s+delta and OU process initated from s=1. Target delta is divided equally in two and generation proceeds in  two stages: yesterday from 1-delta/2 with mean of 1 and today with mean 1+delta/2 starting from 1.
# 
# Choose alpha prop to 1/delta, i.e., if delta small then alpha large; say .0005/(1+abs(delta))
# OU process uses sigma=.005 and dt=.01 by default.
# TBD: learn the above parameters via a GAN procedure from real data.
# 
# Finally prices are compressed to 5min interval OHLC form as a dataframe

# In[ ]:


def gen2days(avg_delta=.3,alpha0=.0005,sigma=.005,dt=.01):
    #generate yesterday
    delta=avg_delta*np.random.randn()
    delta0,delta1=-delta/2,delta/2
    oup=OUProcess(1,alpha0/abs(delta0),sigma,dt)
    data0=oup.fetch(1+delta0,375)
    #generate today
    # delta1=avg_delta*np.random.randn()
    oup=OUProcess(1+delta1,alpha0/(1+abs(delta1)),sigma,dt)
    data1=oup.fetch(1,375)
    data=np.concatenate((data0,data1))
    # px.line(data).show()
    # print(delta0,delta1)
    return data


# In[ ]:


def compress_prices_df(prices,f=5,ret='ohlc'):
    # uniform volume of 1 is returned
    n=len(prices)
    opens=[prices[i:i+f][0] for i in range(0,n,f)]
    lows=[min(prices[i:i+f]) for i in range(0,n,f)]
    highs=[max(prices[i:i+f]) for i in range(0,n,f)]
    closes=[prices[i:i+f][-1] for i in range(0,n,f)]
    volumes=[1 for i in range(0,n,f)]
    data=np.array([[o,h,l,c,v] for o,h,l,c,v in zip(opens,lows,highs,closes,volumes)])
    df=pd.DataFrame(data,columns=['Open','High','Low','Close','Volume'])
    df['ticker']='SYN'
    return df


# In[ ]:


class Syn():
    def __init__(self,avg_delta=.3,alpha0=.0005,sigma=.005,dt=.01,simple=False):
        self.avg_delta=avg_delta
        self.alpha0=alpha0
        self.sigma=sigma
        self.dt=dt
        self.simple=simple
    def gen2days(self,plotting=False):
        #generate yesterday
        delta=np.abs(self.avg_delta*np.random.randn())
        delta0,delta1=-delta/3,2*delta/3
        oup=OUProcess(1,self.alpha0/abs(delta0),self.sigma/(1+abs(delta)),self.dt)
        data0=oup.fetch(1+delta0,375)
        #generate today and tomorrow
        # delta1=avg_delta*np.random.randn()
        oup=OUProcess(1+delta1,self.alpha0/abs(delta1),self.sigma/(1+abs(delta)),self.dt)
        data1=oup.fetch(data0[-1],750)
        data=np.concatenate((data0,data1[0:375]))
        if plotting: 
            px.line(data).show()
            print(delta0,delta1)
        return data
    def simple2days(self,plotting=False,regime=None):
        # toss coin to decide on mean-reverting or trending
        if regime is None: regime=np.random.randint(2)
        if regime==0: #trending
            delta=self.avg_delta*np.random.randn()
            sigma=self.sigma/50
            alpha=self.alpha0/5
            oup=OUProcess(1+delta,alpha=alpha,sigma=sigma,dt=self.dt)
            data=oup.fetch(1,750)
            if plotting: px.line(data).show()
        elif regime==1: #mean-reverting
            delta=self.avg_delta*np.random.randn()
            sigma=self.sigma
            f=np.random.randint(low=1,high=5)
            data=[]
            peaks=[delta*abs(r) for r in np.random.uniform(low=.25,high=1,size=f)]
            sinedata=[np.sin(2*np.pi*f*x/750) for x in np.arange(750)]
            # px.line(sinedata).show()
            for i in range(f):
                data+=[1+peaks[i]*sinedata[int(x)]+sigma*np.random.randn() for x in np.array([j for j in range(int(i*750/f),int((i+1)*750/f))])]
            if plotting: px.line(data).show()
        return data
    def sinewave(self,f=3,plotting=False,sigma=None):
            delta=self.avg_delta
            if sigma is None: sigma=self.sigma
            data=[]
            if f==0 or f<0: 
                if f<0: delta=-delta
                data=[1+x*delta/750+sigma[0]*np.random.randn() for x in np.arange(750)]
                return data
            peaks=[delta+abs(sigma[1]*np.random.randn()) for r in np.ones(f)]
            shift=np.random.randint(2)
            sinedata=[np.sin(2*np.pi*f*x/750+shift*np.pi) for x in np.arange(750)]
            for i in range(f):
                data+=[1+peaks[i]*sinedata[int(x)]+sigma[0]*np.random.randn() for x in np.array([j for j in range(int(i*750/f),int((i+1)*750/f))])]
            if plotting: px.line(data).show()
            return data
    def compress_prices_df(self,prices,f=5,ret='ohlc'):
        # uniform volume of 1 is returned
        n=len(prices)
        opens=[prices[i:i+f][0] for i in range(0,n,f)]
        lows=[min(prices[i:i+f]) for i in range(0,n,f)]
        highs=[max(prices[i:i+f]) for i in range(0,n,f)]
        closes=[prices[i:i+f][-1] for i in range(0,n,f)]
        volumes=[1 for i in range(0,n,f)]
        data=np.array([[o,h,l,c,v] for o,h,l,c,v in zip(opens,lows,highs,closes,volumes)])
        df=pd.DataFrame(data,columns=['Open','High','Low','Close','Volume'])
        df['ticker']='SYN'
        return df
    def history(self,start,end=None):
        #fill datetimes
        def stringify(x):
            return x.strftime('%d-%b-%Y')
        date=pd.to_datetime(start)
        if end is not None:enddate=pd.to_datetime(end)
        else: enddate=date+IBDay(1)
        dfL=[]
        while date<=enddate:
            if (self.simple!='sinewave') and ('sinewave' in self.simple):
                freq=int(self.simple.split('sinewave')[-1].split('_')[0])
                self.avg_delta=float(self.simple.split('sinewave')[-1].split('_')[1])
                self.simple='sinewave'
            if self.simple==True: df=self.compress_prices_df(self.simple2days())
            elif self.simple=='sinewave': df=self.compress_prices_df(self.sinewave(f=freq))
            else: df=self.compress_prices_df(self.gen2days())
            # cn=df.iloc[75]['Close']
            # df[['Open','High','Low','Close']]=df[['Open','High','Low','Close']]/cn
            dt=datetime(year=date.year,day=date.day,month=date.month,hour=9,minute=15,second=0)
            dt.replace(tzinfo=pytz.timezone('Asia/Kolkata'))
            dtcol=[]
            for i in range(75):
                dtcol+=[dt]
                dt=dt+timedelta(minutes=5)
            date=date+IBDay(1)
            dt=datetime(year=date.year,day=date.day,month=date.month,hour=9,minute=15,second=0)
            dt.replace(tzinfo=pytz.timezone('Asia/Kolkata'))
            for i in range(75):
                dtcol+=[dt]
                dt=dt+timedelta(minutes=5)
            date=date+IBDay(1)
            df['datetime']=dtcol
            df['Date']=df['datetime'].apply(stringify)
            df.index=dtcol
            dfL+=[df]
        dfret=pd.concat(dfL)
        return dfret[['datetime','Date','ticker','Open','High','Low','Close','Volume']]


# In[ ]:




