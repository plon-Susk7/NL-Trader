#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd
# from tqdm.notebook import tqdm
# from matplotlib import pyplot as plt
from pandas.tseries.offsets import BDay
import pickle
import pandas_ta as ta
import yfinance as yf
import pandas_ta as ta
from pandas.tseries.offsets import BDay


# In[ ]:


from sklearn.preprocessing import KBinsDiscretizer
from datetime import datetime


# In[ ]:


from .india_calendar import IBDay


# In[ ]:


OHLC_COLS=['Open_n','High_n','Low_n','Close_n']
OHLC_ORIG=['Open','High','Low','Close']
OHLC_TEMP=['Open_t','High_t','Low_t','Close_t']
TA_COLS_OLD=['SMA_10', 'SMA_20', 
       'VOL_SMA_20','RSI_14','BBL_5_2.0','BBM_5_2.0','BBU_5_2.0',
       'BBB_5_2.0', 'BBP_5_2.0','MACD_12_26_9','MACDh_12_26_9','MACDs_12_26_9']
TA_COLS=['SMA_10', 'SMA_20','VOL_SMA_20','RSI_14','BBL_5_2.0','BBM_5_2.0','BBU_5_2.0',
       'BBB_5_2.0', 'BBP_5_2.0','MACD_12_26_9','MACDh_12_26_9','MACDs_12_26_9','VWAP_D',
        'MOM_30', 'CMO_14']
TA_COLS_TO_NORM=['SMA_10', 'SMA_20','BBL_5_2.0','BBM_5_2.0','BBU_5_2.0']


# In[ ]:


OHLCV_COLS=['Open_n','High_n','Low_n','Close_n','Volume_n']
TA_COLS_MIN=['SMA_10', 'SMA_20','CMO_14']
LOGICAL_FEATURES=['High_n-Low_n',
 'Open_n-Close_n',
 'SMA_20-SMA_10',
 'Close_n_slope_3',
 'Close_n_slope_5',
 'Close_n_slope_10',
 'Open_n_changelen',
 'High_n_changelen',
 'Low_n_changelen',
 'Close_n_changelen',
 'High_n-Low_n_changelen',
 'Open_n-Close_n_changelen',
 'SMA_20-SMA_10_changelen',
 'Close_n_slope_3_changelen',
 'Close_n_slope_5_changelen',
 'Close_n_slope_10_changelen']
GDIM=3
MINCOLS=['row_num']+OHLCV_COLS+TA_COLS_MIN
ALLCOLS=['row_num']+OHLCV_COLS+TA_COLS
MINLOG=['row_num']+OHLCV_COLS+TA_COLS_MIN+LOGICAL_FEATURES
ALLLOG=['row_num']+OHLCV_COLS+TA_COLS_MIN+LOGICAL_FEATURES
LOGCOLS=['row_num']+OHLCV_COLS+LOGICAL_FEATURES
USE_COLS_DICT_ORIG={'allcols':ALLCOLS,'mincols':MINCOLS,'minlog':MINLOG,
           'alllog':ALLLOG,'logcols':LOGCOLS}


# In[ ]:


def update_use_cols_dict(USE_COLS_DICT):
    NEWDICT={}
    for uc in USE_COLS_DICT:
        dc=[]
        for c in USE_COLS_DICT[uc]:
            if c is not 'row_num': dc+=[c+'_val']
            elif c is 'row_num': dc+=[c]
        NEWDICT[uc+'D']=dc
    for nc in NEWDICT:
        USE_COLS_DICT[nc]=NEWDICT[nc]
    return USE_COLS_DICT


# In[ ]:


def add_ta(df):
    df[TA_COLS]=1.0
    df['error']=np.nan
    if df.shape[0]>20:
        df['error']=0
        sma=df.ta.sma()
        sma20=df.ta.sma(length=20)
        vsma20=df.ta.sma(close=df['Volume'],length=20)
        df['SMA_10']=sma
        df['SMA_20']=sma20
        df['VOL_SMA_20']=vsma20
        df.ta.rsi(append=True)
        df.ta.bbands(append=True)
        df.ta.macd(append=True)
        df.ta.vwap(append=True)
        df.ta.mom(length=30,append=True)
        df.ta.cmo(append=True)
    return df


# In[ ]:


def norm_add_ta(df,drop_ta=False):
    dft=df.copy()
    if drop_ta: dft=dft.drop(columns=TA_COLS_OLD)
    dft[OHLC_TEMP]=dft[OHLC_ORIG]
    dft[OHLC_ORIG]=dft[OHLC_COLS]
    dft=add_ta(dft)
    dft[OHLC_ORIG]=dft[OHLC_TEMP]
    dft=dft.drop(columns=OHLC_TEMP)
    return dft


# In[ ]:


def adjust_split(df,ticker,date,split):
    df1=df.loc[(df['ticker']==ticker)&(pd.to_datetime(df['Date'])<pd.to_datetime(date))]
    for c in ['Open','High','Low','Close']: df1[c]=df1[c]/split
    return df1


# In[ ]:


def hurst(df,lags=[2,20],field='Close'):
    input_ts=df[field].values
    lagvec=[]
    tau=[]
    cL=[]
    for lag in range(lags[0],lags[1]):
        pp=np.subtract(input_ts[lag:],input_ts[:-lag])
        lagvec.append(lag)
        tau.append(np.std(pp))
        #c=np.corrcoef(input_ts[lag:],input_ts[:-lag])
        #cL.append(c[0,1])
    m=np.polyfit(np.log10(lagvec),np.log10(tau),1)
    #alpha=np.polyfit(np.log10(lagvec),np.log10(cL),1)
    #plt.plot(np.log10(lagvec),np.log10(cL))
    #plt.plot(lagvec,tau)
    #H1=1-abs(alpha[0])/2
    H=m[0]
    return H#,H1


# In[ ]:


def compute_hurst(dft,lags=[2,20],field='Close'):
    dates=dft['Date'].unique()
    tickers=dft['ticker'].unique()
    hL=[]
    for t in tqdm(tickers):
        for d in tqdm(dates):
            H,H1=1,1
            df=dft.loc[(dft['Date']==d)&(dft['ticker']==t)]
            #print(d,t,df)
            if df.shape[0]>=lags[1]: H=hurst(df,lags=lags,field=field)
            #print(t,d,H)
            ymd=pd.to_datetime(d).strftime('%Y-%m-%d')
            hL+=[{'ticker':t,'Prev Date':pd.to_datetime(ymd),'hurst':H}]
    hf=pd.DataFrame(hL)
    return dft.merge(hf,how='left',on=['ticker','Prev Date'])


# Load prev-days data for month from yf

# In[ ]:


def aug_prev_day(dft_all,daysfD):
    tickers=dft_all['ticker'].unique()
    dft_all['Prev Date']=(pd.to_datetime(dft_all['Date'])-BDay(1))
    dftL=[]
    for t in tqdm(tickers):
        dft=dft_all.loc[dft_all['ticker']==t]
        daysfD[t]['Prev Date']=daysfD[t].index
        dftL+=[pd.merge(dft,daysfD[t],on='Prev Date',suffixes=('','_prev'))]
    dft_aug=pd.concat(dftL,axis=0)
    return dft_aug


# load data for prev month

# In[ ]:


def get_prev_day_data(dateList,tickers):
    std=(pd.to_datetime(dateList[0])-BDay(1)).strftime("%Y-%m-%d")
    edt=pd.to_datetime(dateList[-1]).strftime("%Y-%m-%d")
    dfD={}
    for t in tqdm(tickers):
        df=yf.Ticker(t).history(start=std,end=edt,interval='1d')
        dfD[t]=df
    return dfD


# technical indictoars and normalizatin (earlier was in mlstrats)

# In[ ]:


def add_vol_n(df,sdx): 
    av=df.loc[(df['row_num']<sdx)&(df['row_num']>=sdx-350)]['Volume'].mean()
    df['Volume_n']=df['Volume']/av
    return df
def feat_aug(df,sdx,tickers,caller=None):
    # caller.feat_argsL+=[(df,sdx)]
    # r=df['Close'].values[sdx]
    r=df.loc[df['row_num']==sdx]['Close'].values[0]
    df[OHLC_COLS]=df[OHLC_ORIG]/r
    df=add_vol_n(df,sdx)
    df=add_addl_features_online(df,tickers)
    df=df.fillna(1)
    #df[OHLC_COLS+TA_COLS]=df[OHLC_COLS+TA_COLS]-1
    df[OHLC_COLS+TA_COLS]=df[OHLC_COLS+TA_COLS]
    return df
def add_addl_features_online(df,tickers):
    def tick_index(t):
        if t in tickers: return tickers.index(t)
        else: return None
    df=norm_add_ta(df,drop_ta=False)
    df['sym']=df['ticker'].apply(tick_index)
    return df
def add_addl_features_feed(feed,tickers,drop_ta=False):
    add_ta_features_feed(feed,drop_ta=drop_ta)
    # add_sym_feature_feed(feed,tickers)
def add_ta_features_feed(feed,drop_ta=False):
    dfaL=[]
    feed.ndata={}
    for t in feed.tickers:
        dfa=feed.data[t]
        dfL=[]
        feed.ndata[t]={}
        for d in dfa['Date'].unique():
            try:
                pdt=pd.to_datetime(d,format='%d-%b-%Y')
                pdtp=pdt-IBDay(1)
                df=dfa.loc[(pd.to_datetime(dfa['Date'],format='%d-%b-%Y')<=pdt)&
                            (pd.to_datetime(dfa['Date'],format='%d-%b-%Y')>=pdtp)]
                df['row_num'] = np.arange(len(df))
                df=df[~df.index.duplicated(keep='first')]
                df=df.sort_index()
                sdx=df.loc[df['Date']==d]['row_num'].values[0]
                r=df['Close'].values[sdx]
                df[OHLC_COLS]=df[OHLC_ORIG]/r
                if r==0:
                    l=len(df['Close'].values)
                    while r==0 and sdx+j<l: 
                        j+=1
                        r=df['Close'].values[sdx+j]
                if r!=0: df[OHLC_COLS]=df[OHLC_ORIG]/r
                else: df[OHLC_COLS]=1 
                df=add_vol_n(df,sdx)
                df=norm_add_ta(df,drop_ta=drop_ta)
                df['error']=df.isnull().apply(lambda x: -1 if any(x) else 0,axis=1)
                df=df.fillna(1)
                # df[OHLC_COLS+TA_COLS]=df[OHLC_COLS+TA_COLS]-1
                dfc=df.loc[df['Date']==d]
                feed.offsets[t][d]=df.shape[0]-dfc.shape[0]
                dfL+=[dfc]
                # dfL+=[df]
                feed.ndata[t][d]=df
            except:
                pass
        try:
            feed.data[t]=pd.concat(dfL,axis=0)
            dfaL+=[feed.data[t]]
        except:
            pass
    feed.df=pd.concat(dfaL,axis=0)
    feed.df.sort_index(inplace=True)
def add_sym_feature_feed(feed,tickers,live=False):
    def tick_index(t):
        if t in tickers: return tickers.index(t)
        else: return None
    for t in tickers:
        sym=tickers.index(t)
        feed.data[t]['sym']=sym
        for d in feed.ndata[t]: feed.ndata[t][d]['sym']=sym
    if live==False: feed.df['sym']=feed.df['ticker'].apply(tick_index)


# In[ ]:


def get_global_indices(day=None,global_tickers=None):
    dfL=[]
    if global_tickers==None: global_tickers=['^NSEI','^NYA','LSEG.L','^IXIC']
    for t in global_tickers:
        try:
            if day==None: df=yf.Ticker(t).history(period='1d',interval='1d')
            else: 
                end=pd.to_datetime(day).strftime('%Y-%m-%d')
                start=(pd.to_datetime(day)-IBDay(1)).strftime('%Y-%m-%d')
                df=yf.Ticker(t).history(start=start,end=end)
            df[['Open_'+t,'High_'+t,'Low_'+t,'Close_'+t]]=df[['Open','High','Low','Close']]/df.Open.values[0]
            mv=yf.Ticker(t).history(period='1y',interval='1d')['Volume'].mean()
            df['Volume_'+t]=df['Volume']/mv
            dfL+=[df[['Open_'+t,'High_'+t,'Low_'+t,'Close_'+t,'Volume_'+t]]]
        except:
            pass
    gf=pd.concat(dfL,axis=1)
    return gf.iloc[-1:].to_dict('records')


# In[ ]:


def add_global_indices_feed(feed,global_tickers=None):
    feed.gdata={}
    for d in feed.dates:
        feed.gdata[d]=get_global_indices(day=d,global_tickers=global_tickers)


# In[ ]:


def add_logical_features_feed(feed):

    ### LOCAL FUNCTIONS
    
    def check_numeric(df, col):
        return df[col].dtype in ['float64', 'int64']

    def difference_cols(df, a, b):
        df[f'{a}-{b}'] = df[a] - df[b]
        return df, f'{a}-{b}'

    def get_ma_base_string(s):
        idx = s.find('_ma_')
        if idx == -1:
            return None
        return s[:idx]

    def moving_avg(df, col, window_size=3, center=False):
        col_name = f'{col}_ma_{window_size}'
        df[col_name] = df[col].rolling(window_size, min_periods=1, center=center).mean()
        return df, col_name

    def slope(df, col, window):
        col_name = f'{col}_slope_{window}'
        df[col_name] = df[col].diff(periods=window).fillna(df[col])/window
        return df, col_name

    def max_change_helper(seq):
        ans = []
        tracker = {i:0 for i in range(seq[-1]+1)}
        for i in seq:
            tracker[i] += 1
            ans.append(tracker[i])
        return ans

    def max_change(df, col):
        inc_tracker = df[col].diff().lt(0).cumsum().values
        dec_tracker = df[col].diff().gt(0).cumsum().values

        inc_values = max_change_helper(inc_tracker)
        dec_values = max_change_helper(dec_tracker)

        combined = [inc_values[i]-1 if inc_values[i] >= dec_values[i] \
                    else -dec_values[i]+1 for i in range(len(inc_values))]

        col_name = f'{col}_changelen'
        df[col_name] = combined
        return df, col_name

    def discretize(df, col):
        stats = df[col].describe()
        low_thresh, high_thresh = stats['25%'], stats['75%']
        df[f'{col}_val'] = df[col].apply(lambda x: 0 if x<=low_thresh else 2 if x>=high_thresh else 1)
        df[f'{col}_polarity'] = df[col].apply(lambda x: 1 if x>0 else -1)
        # df[f'{col}_discrete'] = df[f'{col}_val'] + df[f'{col}_polarity']
        return df, [f'{col}_val', f'{col}_polarity'] #, f'{col}_discrete']
    
    ####
    
    def add_features_df(df):
        
        nonlocal subtract_cols,slope_cols,change_cols
                
        columns_to_use = ['Open_n', 'High_n', 'Low_n', 'Close_n']
        slope_cols_to_use = ['Close_n']

        subtract_col_names = [('High_n', 'Low_n'),('Open_n', 'Close_n'),('SMA_20', 'SMA_10')]
        subtract_cols = []

        for cols in subtract_col_names:
            df, added_col = difference_cols(df, cols[0], cols[1])
            subtract_cols.append(added_col)

        pre_slope_cols = slope_cols_to_use

        window_sizes = [3,5,10]
        slope_cols = []

        for window in window_sizes:
            for col in pre_slope_cols:
                df, added_col = slope(df, col, window=window)
                slope_cols.append(added_col)

        pre_change_cols = columns_to_use + subtract_cols + slope_cols

        change_cols = []

        for col in pre_change_cols:
            df, added_col = max_change(df, col)
            change_cols.append(added_col)

    # MAIN FUNCTION
    subtract_cols,slope_cols,change_cols=[],[],[]
    _=[add_features_df(feed.ndata[t][d]) for t in feed.ndata for d in feed.ndata[t]]
        
    return subtract_cols+slope_cols+change_cols


# In[ ]:


# Discretize dataframe columns with option to keep values within epsilon of 0 as middle bin
# use zeromean=True to do above for target column; else use zeromean=False
class DiscretizeK:
    def __init__(self,epsilon=.001):
        self.epsilon=epsilon
    def discretizeK(self,df,col,k=5,fit=False,zeromean=True):
        epsilon=self.epsilon
        def zdisc(x):
            estpos,estneg=self.estpos,self.estneg
            if x>epsilon: y=estpos.transform(np.array(x).reshape(1,-1))+k2+1
            elif x<-epsilon: y=estneg.transform(np.array(x).reshape(1,-1))
            else: return k2/4
            return y[0][0]/4
        if not zeromean:
            if fit:
                est=KBinsDiscretizer(n_bins=k,encode='ordinal',strategy='quantile')
                est.fit(df[col].values.reshape(-1,1))
                self.est=est
            df[f'{col}_val']=self.est.transform(df[col].values.reshape(-1,1))/4
        elif zeromean:
            k2=int((k-1)/2)
            if fit:
                epsilon=self.epsilon
                estpos = KBinsDiscretizer(n_bins=k2,encode='ordinal',strategy='quantile')
                estpos.fit(df.loc[df[col]>epsilon][col].values.reshape(-1,1))
                estneg = KBinsDiscretizer(n_bins=k2,encode='ordinal',strategy='quantile')
                estneg.fit(df.loc[df[col]<-epsilon][col].values.reshape(-1,1))
                self.estpos,self.estneg=estpos,estneg
            df[f'{col}_val']=df[col].apply(zdisc)


# In[ ]:


def discretize_features_feed(feed,DkD,use_cols):
    USE_COLS_DICT=update_use_cols_dict(USE_COLS_DICT_ORIG)
    cols=USE_COLS_DICT[use_cols]
    for t in feed.ndata:
        for d in feed.ndata[t]:
            df=feed.ndata[t][d]
            _=[DkD[c].discretizeK(df,col=c,zeromean=False) for c in cols if c is not 'row_num']


# # Experiments/Debugging

# In[ ]:


# with open('./saved_models/discretizers.pickle','rb') as f: discretizers=pickle.load(f)


# In[ ]:


# DK0,DK1=discretizers[0],discretizers[1]


# In[ ]:


# DKO=discretizers[2]['Open_n']


# In[ ]:


# DKO.est.transform(np.array([[1.008],[.993]]))


# In[ ]:


# DK1.estpos.transform(np.array([[.0034],[-.0026]]))


# In[ ]:


# DK1.estneg.transform(np.array([[.0026],[-.0033]]))


# In[ ]:




