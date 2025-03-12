#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json, yfinance as yf


# In[ ]:


# from tqdm.notebook import tqdm


# In[ ]:


import numpy as np
import pandas as pd


# In[ ]:


from .feeds import LiveFeed,BackFeed,DataFeed,clean_feed,clean_feed_tickers


# In[ ]:


from .featfuncs import add_addl_features_feed,add_sym_feature_feed


# In[ ]:


import pickle
# from matplotlib import pyplot as plt


# In[ ]:


def compute_gaps(feed,topk=5):
    k,m=int(topk/2)+1,topk
    sg=compute_top_gaps(feed,topk)
    st=compute_top_trending(feed,topk)
    sv=compute_top_volatility(feed,topk)
    stocks=topk_of_each([sg,st,sv],feed,k,m)
    return stocks


# In[ ]:


def compute_top_gaps(feed,topk=5):
    dates=[]
    for t in feed.ndata:
        for d in feed.ndata[t]:
            dates+=[d]
    dates=list(set(dates))
    gaps={}
    stocks={}
    for d in dates:
        gaps[d]={}
        for t in feed.ndata:
            if d in feed.ndata[t]:
                df=feed.ndata[t][d]
                dts=df.Date.unique()
                if len(dts)>1:
                    endcl=df.loc[df['Date']==dts[0]]['Close_n'].values[-1]
                    startcl=df.loc[df['Date']==dts[1]]['Open_n'].values[0]
                    gaps[d][t]=abs(startcl-endcl)
        g=gaps[d]
        stocks[d]=pd.DataFrame([(t,g[t]) for t in g],columns=['ticker','gap']).sort_values('gap',ascending=False)
        stocks[d]=stocks[d].iloc[0:topk]
    return stocks


# In[ ]:


def compute_top_trending(feed,topk=5):
    dates=[]
    for t in feed.ndata:
        for d in feed.ndata[t]:
            dates+=[d]
    dates=list(set(dates))
    trends={}
    stocks={}
    for d in dates:
        trends[d]={}
        for t in feed.ndata:
            if d in feed.ndata[t]:
                df=feed.ndata[t][d]
                dts=df.Date.unique()
                if len(dts)>1:
                    endcl=df.loc[df['Date']==dts[0]]['Open_n'].values[0]
                    startcl=df.loc[df['Date']==dts[0]]['Close_n'].values[-1]
                    trends[d][t]=abs(startcl-endcl)
        g=trends[d]
        stocks[d]=pd.DataFrame([(t,g[t]) for t in g],columns=['ticker','trend']).sort_values('trend',ascending=False)
        stocks[d]=stocks[d].iloc[0:topk]
    return stocks


# In[ ]:


def compute_top_volatility(feed,topk=5):
    dates=[]
    for t in feed.ndata:
        for d in feed.ndata[t]:
            dates+=[d]
    dates=list(set(dates))
    vols={}
    stocks={}
    for d in dates:
        vols[d]={}
        for t in feed.ndata:
            if d in feed.ndata[t]:
                df=feed.ndata[t][d]
                dts=df.Date.unique()
                if len(dts)>1:        
                    vols[d][t]=df.loc[df['Date']==dts[0]]['Close_n'].std()
        g=vols[d]
        stocks[d]=pd.DataFrame([(t,g[t]) for t in g],columns=['ticker','vol']).sort_values('vol',ascending=False)
        stocks[d]=stocks[d].iloc[0:topk]
    return stocks


# In[ ]:


def topk_of_each(stockL,feed,k,m):
    stocks={}
    dates=[]
    for t in feed.ndata:
        for d in feed.ndata[t]:
            dates+=[d]
    ### Changed since dates have duplicates
    dates=list(set(dates))
    for d in dates: stocks[d]=pd.DataFrame(columns=['ticker'])
    for d in dates:
        # stocks[d]=pd.DataFrame(columns=['ticker'])
        for s in stockL:
            if not s[d].empty:
                if s[d].shape[0]<k: 
                    stocks[d]=pd.concat([stocks[d],s[d][['ticker']]])
                else: 
                    stocks[d]=pd.concat([stocks[d],s[d].iloc[0:k][['ticker']]])
    return {d:pd.DataFrame(data=stocks[d]['ticker'].unique()[0:m],columns=['ticker']) for d in dates}



# In[ ]:


def market_cap(t):
    try:
        bs=yf.Ticker(t).balance_sheet
        c=bs.loc[bs.index=='Common Stock'].values[-1][-1]
        p=yf.Ticker(t).history(period='1d',interval='1d').iloc[0]['Close']
        mc=(p*c/80)/1000000
    except: mc=0
    return mc


# In[ ]:


market_capD={}
def compute_market_caps(M,N):
    global market_capD,nsetickers
    for t in tqdm(list(nsetickers.keys())[M:N]):
        market_capD[t+'.NS']=market_cap(t+'.NS')
    caps=pd.DataFrame([(t,market_capD[t]) for t in market_capD],
                      columns=['ticker','cap']).sort_values('cap',ascending=False)
    return caps


# In[ ]:


def vol_est(t):
    try:
        df=yf.Ticker(t).history(period="1y",interval="1d")
        vol=np.mean((100*abs(df['Close']-df['Open'])/df['Close']).values)
        return vol
    except:
        return 0


# In[ ]:


volsD={}
def compute_vols(M,N):
    global volsD,nsetickers
    volsD={}
    for t in tqdm(list(nsetickers.keys())[M:N]):
        volsD[t+'.NS']=vol_est(t+'.NS')
    volsf=pd.DataFrame([(t,volsD[t]) for t in volsD],
                      columns=['ticker','vol']).sort_values('vol',ascending=False)
    return volsf


# Debugging

# In[ ]:


# import pickle
# from feeds import BackFeed,LiveFeed


# In[ ]:


# # with open('../../temp_data/feed_sim.pickle','rb') as f: feed_sim=pickle.load(f)
# with open('../temp_data/feed_live.pickle','rb') as f: feed_live=pickle.load(f)


# In[ ]:


# stocks=compute_gaps(feed_live,5)


# In[ ]:




