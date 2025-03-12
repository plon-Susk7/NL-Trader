#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import anvil.server


# In[2]:


# import rpyc
import pickle


# In[3]:


class FeedEnv():
    def __init__(self,feed,ticker,target=.01,stoploss=.005,txcost=.001,
                 seq_len=50,verbose=True,t_limit=None):
        self.t_limit=t_limit
        self.feed=feed
        self.t=target
        self.stoploss=stoploss
        self.txcost=txcost
        self.ticker=ticker
        self.verbose=verbose
        self.state_type='dict'
        self.set_state_shape()
        self.set_state_type()
        self.seq_len=seq_len
        self.state_cols=self.feed.data[self.ticker].columns
        self.reset()
    
    def set_state_cols(self,cols):
        self.state_cols=cols
    
    def set_state_type(self,state_type='dict'):
        self.state_type=state_type
    
    def set_state_shape(self,state_shape='seq'):
        self.state_shape=state_shape
    
    def set_date(self,date):
        self.date=date
        # self.state_cols=self.feed.getDataN(self.ticker,self.date).columns
        df=self.feed.ndata[self.ticker][date]
        # self.mv=df.iloc[self.feed.offsets[self.ticker][date]]['Open_n']
        self.r=df['Close_n'].values[self.feed.offsets[self.ticker][date]:]
        self.end=df.shape[0]-self.feed.offsets[self.ticker][self.date]
        self.time=0
        # env.done=False
        
    def set_episode(self,episode):
        self.episode=episode
        
    def thresh(self,x,pos):
        # x=current_price,pos=position_taken(+-)
        if pos>0:
            if x>pos+self.t*pos or x<pos-self.l*pos: return True
            else: return False
        elif pos<0:
            if x<abs(pos)-self.t*abs(pos) or x>abs(pos)+self.l*abs(pos): return True
            else: return False
    
    def partial_thresh(self,x,pos):
        #x=current_price,pos=position_taken(+-)
        if pos>0:
            if x>pos+self.t*pos/2: return 1
            else: return 0
        elif pos<0:
            if x<abs(pos)-self.t*abs(pos)/2: return 1
            else: return 0
    
    def get_state(self):
        if self.state_type=='dict':
            if self.state_shape=='seq':
                return {self.ticker:self.feed.getDataN(self.ticker,self.date)[self.state_cols]}
            elif self.state_shape=='flat':
                return {self.ticker:self.feed.getDataN(self.ticker,self.date).iloc[-1][self.state_cols]}
        elif self.state_type=='frame':
            if self.state_shape=='seq':
                return (self.feed.getDataN(self.ticker,self.date)
                        [self.state_cols]).to_numpy()[-self.seq_len:,:]
            elif self.state_shape=='flat':
                return (self.feed.getDataN(self.ticker,self.date)[self.state_cols]).to_numpy()[-1,:]
    
    def reset(self):
        self.l=self.stoploss
        self.sl=self.stoploss
        self.time=0
        self.tot=0
        self.done=False

    def step(self,action):
        if action==0: 
            ret=0.0
            if self.time+1==self.end: self.done=True
            else: 
                self.feed.step()
                self.time+=1
            if self.verbose: return self.get_state(),ret,self.done,'no action'
            else:  return self.get_state(),ret,self.done
        else: 
            r=self.r
            pos=action*r[self.time]
            exit_type=self.episode.exit_episode(self,pos,t_limit=self.t_limit)
            if pos>0: ret=100*(r[self.time]-pos-r[self.time]*self.txcost)/pos
            elif pos<0: ret=100*(abs(pos)-r[self.time]-r[self.time]*self.txcost)/abs(pos)
            # ret=ret*100/self.mv
            self.l=self.sl
            if self.time+1==self.end: self.done=True
            else:
                self.time+=1
                self.feed.step()
            if self.verbose: return self.get_state(),ret,self.done,exit_type
            else:  return self.get_state(),ret,self.done


# In[1]:


class Episode():
    def __init__(self,env,policy=None,model_type='none',remote=False,rpcname=None,
                 loc_exit=True,rem_exit=False,deploy=True,verbose=False,save_func=None):
        self.save_func=save_func
        self.verbose=verbose
        self.deploy=deploy
        self.state={}
        self.env=env
        self.policy=policy
        if model_type=='none':self.rl_type=policy.model_type
        else: self.rl_type=model_type
        self.remote=remote
        self.rpcname=rpcname
        self.loc_exit=loc_exit
        self.rem_exit=rem_exit
        self.debug=[]
    def run_episode(self):
        self.env.time=0
        env=self.env
        if self.rl_type=='meta_rl' and env.state_type=='dict':
            t=self.env.ticker
            state={t:self.policy.get_meta_state(self.env.get_state()[t],t,0,0,self.env.done)}
        elif env.state_type=='dict':
            state=self.env.get_state()
        elif env.state_type=='frame':
            state={env.ticker:self.env.get_state()}
        self.actionL=[]  
        self.rewardL=[]
        self.dfL=[]
        if self.rl_type=='meta_rl': self.policy.reset_hidden()
        tot=0.0
        done=False
        while done==False:
            if self.remote==True: 
                action=self.remote_check_entry_batch(state,self.rpcname)[0][self.env.ticker]
            else: 
                retval=self.policy.check_entry_batch(state)
                action=retval[0][self.env.ticker]
                stop=retval[1][self.env.ticker]
                target=retval[2][self.env.ticker]
                if stop>0: self.env.l=stop/100
                if target>0: self.env.t=target/100
                # action=self.policy.check_entry_batch(state)[0][self.env.ticker]
            #track state passed to entry function for saving later
            saved_state=state
            action_time=self.env.time
            df=env.feed.ndata[env.ticker][env.date]
            if action!=0: 
                self.actionL+=[(action,stop,target,self.env.time)]
            if self.deploy==False and action!=0:
                #save env state including feed
                self.save_episode_state(self.env.feed,self.env.ticker)
            # state,rew,done,exit_type=self.env.step(action)
            state,rew,done,exit_type=self.env_step(action)
            if rew!=0.0: self.rewardL+=[(action_time,rew,self.env.time)]
            if self.save_func==None: self.dfL+=[(action_time,action,rew,self.env.time,saved_state)]
            else: self.dfL+=[(action_time,action,rew,self.env.time,self.save_func(saved_state))]
            finish_time=env.time
            if self.deploy==False and action!=0:
                #restore env state including feed, increment envtime and take feed step
                self.restore_and_inc_episode_state(self.env.feed)
                done=env.done
            if self.verbose: print(env.ticker,env.date,action_time,finish_time,action,rew,env.time)
            if env.state_type=='frame':state={env.ticker:self.env.get_state()}
            elif self.rl_type=='meta_rl' and env.state_type=='dict':
                t=self.env.ticker
                state={t:self.policy.get_meta_state(self.env.get_state()[t],t,action,rew,self.env.done)}
            if action!=0:
                tot+=rew
                # print(rew)
        return tot,self.rewardL,self.actionL,self.dfL
    
    def env_step(self,action):
        return self.env.step(action)
    
    def exit_episode(self,env,pos,t_limit=None):
        exit_type='none'
        env=self.env
        start_time=env.time
        while True:
            thresh_met=env.thresh(env.r[env.time],pos)
            if self.remote: 
                if self.rem_exit==False: exit_met=False
                else:
                    exit_met=self.remote_exit_predicate({'quant':pos,'ticker':env.ticker},
                                                        env.get_state()[env.ticker],
                                                        self.rpcname)
                    # print(exit_met,env.time,env.ticker,pos)
            elif self.loc_exit==False: 
                exit_met=False
            else:
                if env.state_type=='dict':
                    exit_met=self.policy.exit_predicate({'quant':pos,'ticker':env.ticker},
                                                        env.get_state()[env.ticker])
                elif env.state_type=='frame': 
                    exit_met=self.policy.exit_predicate({'quant':pos},env.get_state())
            if thresh_met: 
                exit_type='thresh'
                break
            if exit_met:
                exit_type='policy'
                break
            if env.time+1==env.end:
                env.done=True
                break
            if t_limit is not None:
                if env.time+1>start_time+t_limit:
                    exit_type='timeout'
                    break
            env.feed.step()
            env.time+=1
            if env.time==env.end: env.done=True
            # if env.partial_thresh(env.r[env.time],pos): env.l=-env.t/2
        return exit_type

    def remote_check_entry_batch(self,dfD,rpcname):
        # c = rpyc.connect("localhost", 18861)
        dfR={}
        for t in dfD.keys():
            dfR[t]=dfD[t].to_dict('records')
        return anvil.server.call('check_entry_batch_'+rpcname,dfR)
        # return c.root.check_entry(pickle.dumps(dfR),rpcname)
        
    def remote_exit_predicate(self,posR,df,rpcname):
        # c = rpyc.connect("localhost", 18861)
        # posR=posf.fillna(0).to_dict('records')
        dR=df.to_dict('records')
        exit_met=anvil.server.call('exit_predicate_'+rpcname,posR,dR)
        return exit_met
        # return c.root.check_entry(pickle.dumps(dfR),stratname)
        
    def save_episode_state(self,feed,ticker):
        self.state['ticker']=ticker
        self.state['counter']=feed.counter
        self.state['ncounter']=feed.ncounter[ticker]
        self.state['ndata']=feed.ndata[ticker]
        self.state['time']=self.env.time
        self.state['done']=self.env.done
    def restore_and_inc_episode_state(self,feed):
        ticker=self.state['ticker']
        feed.counter=self.state['counter']
        feed.ncounter[ticker]=self.state['ncounter']
        feed.ndata[ticker]=self.state['ndata']
        self.env.done=self.state['done']
        self.env.time=self.state['time']
        if self.env.time+1==self.env.end: self.env.done=True
        else: 
            self.env.time+=1
            feed.step()


# Develop
