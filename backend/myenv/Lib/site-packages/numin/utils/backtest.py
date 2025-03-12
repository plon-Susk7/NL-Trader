#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import numpy as np
import anvil.server


# In[ ]:


# from tqdm.notebook import tqdm


# In[ ]:


tqdm=lambda x: x


# In[ ]:


from .feeds import BackFeed,LiveFeed,DataFeed,clean_feed
from .featfuncs import add_addl_features_feed,add_sym_feature_feed


# In[ ]:


from .feed_env import FeedEnv, Episode


# In[ ]:


from .scanner import compute_gaps


# In[ ]:


try:
    with open('/Users/a112956/MyCode/algo_fin_root/algo_fin_src/anvilcode.txt','r') as f: 
        CODE=f.read()
except:
    CODE=''


# In[ ]:


class Backtest():
    def __init__(self,feed,tickers=None,add_features=True,
                 target=.05,stop=.02,txcost=.001,remote=False,
                 data_cols=None,rpcname=None,loc_exit=True,rem_exit=False,
                 scan=True,topk=5,deploy=True,save_dfs=False,save_func=None,t_limit=None):
        if add_features:
            for t in tickers: clean_feed(feed,t)
            add_addl_features_feed(feed,tickers=tickers,drop_ta=False)
            add_sym_feature_feed(feed,tickers)
        self.t_limit=t_limit
        self.save_func=save_func
        self.save_dfs=save_dfs
        self.deploy=deploy
        self.feed=feed
        self.feed.set_datesQ()
        self.feed.init_counters()
        self.results={}
        self.returns={}
        self.total=0
        self.target=target
        self.stop=stop
        self.txcost=txcost
        self.remote=remote
        self.loc_exit=loc_exit
        self.rem_exit=rem_exit
        self.data_cols=data_cols
        if self.remote: 
            anvil.server.connect(CODE)
            self.model_type='rpc'
        else: self.model_type='none'
        self.rpcname=rpcname
        self.scan=scan
        self.topk=topk
        if self.scan: 
            self.tickersD=compute_gaps(self.feed,self.topk)
            self.gaptickers=[list(self.tickersD[d]['ticker'].values) for d in self.tickersD]
            self.gaptickers=list(set(sum(self.gaptickers,[])))
    def run_all(self,tickers=None,model=None,verbose=False):
        if self.scan:
            for t in self.gaptickers: 
                #clean_feed(self.feed,t)
                self.results[t]={}
                self.returns[t]=0
            for date in tqdm(self.tickersD):
                for ticker in tqdm(self.tickersD[date]['ticker'].values):
                    self.run(ticker,model=model,date=date,verbose=verbose)
        else:
            for ticker in tqdm(tickers):
                #clean_feed(self.feed,ticker)
                self.results[ticker]={}
                self.returns[ticker]=0
                self.run(ticker,model=model,verbose=verbose)
    def run(self,ticker,model=None,date=None,verbose=False):
        if 'agent' in model.__dict__: 
            model.scantickers=[ticker]
            # if 'model_type' in model.__dict__:
            #     if model.model_type=='RL':
            #         model.clear()
            #         model.time=0
        env=FeedEnv(self.feed,ticker=ticker,
                    target=self.target,stoploss=self.stop,
                    txcost=self.txcost,t_limit=self.t_limit)
        self.env=env
        env.set_state_type('dict')
        if self.remote==True:
            env.set_state_cols(self.data_cols)
            episode=Episode(env,model_type=self.model_type,remote=True,
                            rpcname=self.rpcname,rem_exit=self.rem_exit,deploy=self.deploy)
        else:
            env.set_state_cols(model.data_cols)
            episode=Episode(env,policy=model,loc_exit=self.loc_exit,
                            deploy=self.deploy,verbose=verbose,save_func=self.save_func)
        env.set_episode(episode)
        if self.scan: dates=[date]
        else: dates=tqdm(self.feed.data[ticker].Date.unique()[1:])
        for date in dates:
            env.set_date(date=date)
            self.feed.set_datesQ()
            self.feed.init_counters(date,tickers=[ticker])
            self.reset_agent(model)
            tot,rews,acts,dfs=episode.run_episode()
            self.results[ticker][date]={'tot':tot,'rew':rews,'acts':acts}
            if self.save_dfs:self.results[ticker][date]['dfs']=dfs
            self.returns[ticker]+=tot
            self.total+=tot
            env.reset()
    def reset_agent(self,model):
        if 'model_type' in model.__dict__:
            if model.model_type=='RL':
                model.clear()
                model.time=0


# # Experiments
