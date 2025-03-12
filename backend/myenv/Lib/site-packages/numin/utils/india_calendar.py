#!/usr/bin/env python
# coding: utf-8

# In[6]:


import pandas as pd
from pandas.tseries.holiday import *
from pandas.tseries.holiday import AbstractHolidayCalendar,Holiday
from pandas.tseries.offsets import CustomBusinessDay
from functools import partial


# In[7]:


class IndiaBusinessCalendar(AbstractHolidayCalendar):
   rules = [
     Holiday('Republic Day', month=1, day=26),
     Holiday('Mahashivratri', month=3, day=8),
     Holiday('Holi', month=3, day=25),
     Holiday('Good Friday', month=3, day=29),
     Holiday('Id-ul Fitr', month=4, day=11),  
     Holiday('Ram Navmi', month=4, day=17), 
     Holiday('Maharashtra Day', month=5, day=1),
     Holiday('Elections', month=5, day=20),
     Holiday('Bakr Id', month=6, day=17),
     Holiday('Moharram', month=7, day=17),
     Holiday('Independence Day', month=8, day=15),
     Holiday('Gandhi Jayanti', month=10, day=2),
     Holiday('Diwali', month=11, day=1),
     Holiday('Gurunanak Jayanti', month=11, day=15),    
     Holiday('Christmas', month=12, day=25)
   ]


# In[ ]:


# class IndiaBusinessCalendar(AbstractHolidayCalendar):
#    rules = [
#      Holiday('Republic Day', month=1, day=26),
#      Holiday('Holi', month=3, day=7),
#      Holiday('Ram Navmi', month=3, day=30),
#      Holiday('Mahavir Jayanti', month=4, day=4),
#      Holiday('Good Friday', month=4, day=7),
#      Holiday('Ambedkar Jayanti', month=4, day=14),   
#      Holiday('Maharashtra Day', month=5, day=1),
#      Holiday('Bakr Id', month=6, day=29),
#      Holiday('Independence Day', month=8, day=15),
#      Holiday('Ganesh Chaturthi', month=9, day=19),
#      Holiday('Gandhi Jayanti', month=10, day=2),
#      Holiday('Dussehra', month=10, day=24),
#      Holiday('Diwali', month=11, day=14),
#      Holiday('Gurunanak Jayanti', month=11, day=27),    
#      Holiday('Christmas', month=12, day=25)
#    ]


# In[40]:


IBDay=partial(CustomBusinessDay,calendar=IndiaBusinessCalendar())

