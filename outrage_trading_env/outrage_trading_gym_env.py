import gym
import gym.spaces
import pandas as pd
import numpy as np
import sklearn.preprocessing as sklpp
from typing_extensions import Literal

class outrage_trading_env(gym.Env):
    metadata = {'render.modes': ['human']}
    def __init__(self,df:pd.DataFrame,number_of_actions:'Literal[2,3]',df_price:str='Close',df_spread:'str|None'='Spread',alternative_spread:int=10,contrate_value:int=100000,bars_per_observation:int=64,columns_to_observe:"list[str]"='all',loss_sequence_to_done:int=4,pip_loss_to_done:float=0.035,pip_loss_position_equility_to_done:float=0.035,len_reduce_prevent:bool=False):
        """
        Parameters
        ----------
        *df: pd.dataframe
            a pandas dataframe with the data
        *number_of_actions: 2 or 3
            the number of action in a action space discrete(number), whether 2 the env is buy/sell only whether 3 the is is buy/sell/nothing
        *df_price: string
            name of the column with the price
        *df_spread: string or None
            name of the column with the spread if the table dont have spread column set it to None
        *alternative_spread: int
            will be used if spread is set to None this value will be the fixed spread value
        *contrate_value: int
            the number of the contrate size, how much monetary value cost exactly 1 in the trading currency, actualy applied only to spread, for example 1 spread in 'default' forex is 0.1 pip that is 0.00001 (1/100000=0.00001) for crypto is commonly contrate_value=1
        *bars_per_observation: int
            the number of bars the observation will take from number of bars each step
        *columns_to_observe: list[str] or 'all'
            columns to return in the observation
        *loss_sequence_to_done: int or 0
            number of sequential losses to reset the env, 0 is disabled
        *pip_loss_to_done: float or 0
            will return done if the total profit (balance) is lower than. 0 is disabled
        *pip_loss_position_equility_to_done: float or 0
            will return done if the profit of the position (equility (position was not closed)) is lower than. 0 is disabled
        *len_reduce_prevent: bool
            test option, if true this will prevent the lenght of the episode be lesser previous episode lenght this way the episode lenght only increase not decrease
        """
        
        if isinstance(df,pd.DataFrame):
            pass
        else:
            raise ValueError('df need to be a pandas.dataframe')
        self.data=df
        self.number_of_actions=number_of_actions
        self.df_price=df_price
        self.df_spread=df_spread
        self.alternative_spread=alternative_spread
        self.bars_per_observation=bars_per_observation
        self.columns_to_observe=list(self.data.columns) if isinstance(columns_to_observe,str) else columns_to_observe
        self.contrate_value=contrate_value
        self.loss_sequence_to_done=loss_sequence_to_done
        self.pip_loss_to_done=pip_loss_to_done
        self.pip_loss_position_equility_to_done=pip_loss_position_equility_to_done
        self.len_reduce_prevent=len_reduce_prevent
        self.last_reset_len=0 #storage the last reset lenght and will not be reseted
        self.action_space=gym.spaces.Discrete(2) if self.number_of_actions==2 else gym.spaces.Discrete(3) if self.number_of_actions==3 else None
        self.observation_space=gym.spaces.Box(
            low=1,
            high=100,
            shape=(self.bars_per_observation*len(self.columns_to_observe),),
            dtype=np.float32)
            
    def reset(self):
        self.done=False
        self.reward=0
        self.position={'type':'','opened_price':None,'profit':0.00}
        self.sequence_loss=0
        self.number_of_trades=0
        self.total_profit=0.00
        self.hightest_total_profit=0.00 #keeps the hightest profit to calculate the equility drawdown
        self.niter=0 #the number of time step has been called
        self.nbar=1+self.bars_per_observation #will be always the number of the current bar
        newobs=self.preprocess_obs(self.data[self.columns_to_observe].iloc[:self.bars_per_observation])
        return newobs
    
    def calculate_profit(self):
        #calc profit
        if self.position['type']=='buy':
            self.position['profit']=self.data[self.df_price].iloc[self.nbar]-self.position['opened_price']+self.spread #the profit is the difference between opened and actual price plus self.spread
        elif self.position['type']=='sell':
            self.position['profit']=self.position['opened_price']-self.data[self.df_price].iloc[self.nbar]+self.spread #the profit is the difference between opened and actual price plus self.spread

    def preprocess_obs(self,obs) -> np.array:
        return np.array(np.ravel(sklpp.minmax_scale(obs.to_numpy(),feature_range=(1,100))))

    def step(self,action):
        #calculate self.spread
        self.spread=-self.data[self.df_spread].iloc[self.nbar]/self.contrate_value if self.df_spread!=None else self.alternative_self.spread

        self.calculate_profit()

        #if dont have any position open position
        if action==0 and self.position['type']=='':
            self.position['type']='buy'
            self.position['opened_price']=self.data[self.df_price].iloc[self.nbar-1]
            self.position['profit']=self.spread #reset the profit, set the self.spread
        elif action==1 and self.position['type']=='':
            self.position['type']='sell'
            self.position['opened_price']=self.data[self.df_price].iloc[self.nbar-1]
            self.position['profit']=self.spread #reset the profit, set the self.spread
        

        #if there a position and the value predicted is difference, so change the position
        if self.position['type']=='buy' and action==1: #close buy order and open sell
            self.position['type']='sell'
            self.position['opened_price']=self.data[self.df_price].iloc[self.nbar-1] #write the new opened price
            self.sequence_loss=self.sequence_loss+1 if self.position['profit']<0 else 0 #sequence losses count
            self.total_profit+=self.position['profit']
            self.position['profit']=self.spread #reset the profit of the position
            self.number_of_trades+=1
        elif self.position['type']=='sell' and action==0: #close sell order and open buy
            self.position['type']='buy'
            self.position['opened_price']=self.data[self.df_price].iloc[self.nbar-1] #write the new opened price
            self.sequence_loss=self.sequence_loss+1 if self.position['profit']<0 else 0 #sequence losses count
            self.total_profit+=self.position['profit']
            self.position['profit']=self.spread #reset the profit of the position
            self.number_of_trades+=1
        elif self.position['type']!='' and action==2: #close buy/sell orders and open nothing
            self.position['type']=''
            self.position['opened_price']=None
            self.sequence_loss=self.sequence_loss+1 if self.position['profit']<0 else 0 #sequence losses count
            self.total_profit+=self.position['profit']
            self.position['profit']=0.0

        self.calculate_profit()

        self.hightest_total_profit=self.total_profit if self.total_profit>self.hightest_total_profit else self.hightest_total_profit
        #^ update the self.hightest_total_profit keeps the hightest profit

        info={'p_type':self.position['type'],'p_profit':self.position['profit'],'reward':self.reward,'sequence_loss':self.sequence_loss,'number_of_trades':self.number_of_trades,'total_profit':self.total_profit}

        
        self.niter+=1
        self.nbar+=1

        #!                                                                                                                                                                                                          V done if the loss "equility total" in pips is lower than V                            V done if the loss "equility" (profit of the position) is lower than V
        if self.nbar>=self.data.index.size or (self.sequence_loss>=self.loss_sequence_to_done and self.loss_sequence_to_done>0 and self.niter>=self.last_reset_len) or (self.pip_loss_to_done!=0 and self.total_profit<=self.hightest_total_profit-abs(self.pip_loss_to_done)) or (self.pip_loss_position_equility_to_done!=0 and self.position['profit']<=-abs(self.pip_loss_position_equility_to_done)):
            self.done=True
            self.last_reset_len=self.niter if (self.nbar<self.data.index.size and self.len_reduce_prevent==True) else 0 #will set always 0 if the len_reduce_prevent==False

        self.reward=self.position['profit']+self.total_profit  #the reward is the sum of the profit of the actual position (starts negative due the self.spread) and the total_profit ("balance")
        newobs=self.preprocess_obs(self.data[self.columns_to_observe].iloc[self.niter:self.nbar-1])
        
        #                                       V test is because i think the agent cant read very low values to reward so multipling it to contrate_value will be all rewards changes can be readen
        return newobs,self.reward*self.contrate_value*self.number_of_trades,self.done,info
    def render(self,mode='human'):
        pass
    def seed(self,seed=None):
        pass
    def close(self):
        self.reset()
        pass


