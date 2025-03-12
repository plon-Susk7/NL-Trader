import pandas as pd
import numpy as np
# from .utils import Backtest, DataFeed, discretize_features_feed, add_addl_features_feed, add_logical_features_feed
# import anvil.server

# Base Strategy -------------

def do_nothing(dfD):
    empty={t:0 for t in dfD}
    return empty,empty,empty

def always_buy(dfD):
    buy={t:1 for t in dfD}
    empty={t:0 for t in dfD}
    return buy,empty,empty

def always_sell(dfD):
    sell={t:-1 for t in dfD}
    empty={t:0 for t in dfD}
    return sell,empty,empty

class BaseStrat():
    def __init__(self):
        self.logL=[]
    def check_entry_batch(self,dfD):
        return do_nothing(dfD)
    
# Base Strategy -------------

# Features -------------

OHLC_COLS=['Open_n','High_n','Low_n','Close_n']
TA_COLS=['SMA_10', 'SMA_20','VOL_SMA_20','RSI_14','BBL_5_2.0','BBM_5_2.0','BBU_5_2.0',
       'BBB_5_2.0', 'BBP_5_2.0','MACD_12_26_9','MACDh_12_26_9','MACDs_12_26_9','VWAP_D',
        'MOM_30', 'CMO_14']

VALCOLS=['Open_n_val',
 'High_n_val',
 'Low_n_val',
 'Close_n_val',
 'Volume_n_val',
 'SMA_10_val',
 'SMA_20_val',
 'CMO_14_val',
 'High_n-Low_n_val',
 'Open_n-Close_n_val',
 'SMA_20-SMA_10_val',
 'Close_n_slope_3_val',
 'Close_n_slope_5_val',
 'Close_n_slope_10_val',
 'Open_n_changelen_val',
 'High_n_changelen_val',
 'Low_n_changelen_val',
 'Close_n_changelen_val',
 'High_n-Low_n_changelen_val',
 'Open_n-Close_n_changelen_val',
 'SMA_20-SMA_10_changelen_val',
 'Close_n_slope_3_changelen_val',
 'Close_n_slope_5_changelen_val',
 'Close_n_slope_10_changelen_val']


COLS=['High_n-Low_n',
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
 'Close_n_slope_10_changelen',
 'row_num'] + VALCOLS + OHLC_COLS + TA_COLS

# User Backtesting Wrapper Class -------------
class UserBacktestStrategy(BaseStrat):
    def __init__(self, user_strategy_function):
        super(UserBacktestStrategy,self).__init__()
        self.model_type='rule_based'
        self.data_cols=COLS
        self.user_strategy_function=user_strategy_function
        
        #track the number of times check_entry_batch is called
        self.round_count = 0

    def check_entry_batch(self,dfD):
        """
        dfD: dict of {ticker -> Pd.DataFrame_of_features_for_that_ticker}
             with columns like ['ticker', 'Open', 'High', 'Low', ...].
        
        This method:
          - Combine them into one big DataFrame
          - Call user_strategy_function, expecting it to return [id, predictions, round_no]
          - Map predictions to (quantD, stops, targets) 
        """
        
        # Intialize
        stops={t:2 for t in dfD}
        targets={t:1 for t in dfD}
        quantD={t:0 for t in dfD}
        
        # 2. Combine dfD into a single DataFrame (to handle all the tickers)
        combined_list = []
        for t, dframe in dfD.items(): # (id, DataFrame) pairs
            if dframe.empty:
                continue
           
            # Copy to avoid mutating the original
            temp_df = dframe.copy()
            
            # If you want the user function to see the column named 'id':
            # rename 'ticker' -> 'id' (or just create 'id' if not present).
            if 'ticker' in temp_df.columns:
                temp_df = temp_df.rename(columns={'ticker': 'id'})
            else:
                # If there's no 'ticker' column, create 'id' from the dictionary key
                temp_df['id'] = t
            
            combined_list.append(temp_df)
        
        if not combined_list:
            # If nothing is there, return 0 actions
            return quantD, stops, targets
        
        combined_df = pd.concat(combined_list, ignore_index=True)
        
        # Call user's strategy function
        self.round_count += 1
        preds_df = self.user_strategy_function(combined_df, current_round=self.round_count)
        
        # Must return columns: [id, predictions, round_no]
        if not {"id", "predictions", "round_no"}.issubset(preds_df.columns):
            raise ValueError(
                "User strategy must return a dataframe with columns "
                "['id', 'predictions', 'round_no']"
            )
        
        # 4. Map predictions back to each ticker
        for t, dframe in dfD.items():
            if dframe.empty:
                quantD[t] = 0
                continue
        
        row_match = preds_df[preds_df["id"] == t]
        if row_match.empty:
            # If no prediction for that ticker, remain 0
            quantD[t] = 0
        else:
            # If multiple rows, we might just take the first for that ticker
            # or handle it differently if your user function is more advanced
            pred_val = row_match.iloc[0]["predictions"]
            
            # Translate user prediction to long/short:
            # 0 => short (-1), 4 => long (+1)
            if pred_val == 0:
                quantD[t] = -1
            elif pred_val == 4:
                quantD[t] = 1
            else:
                quantD[t] = 0
        
        return quantD,stops,targets