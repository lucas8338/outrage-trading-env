import gym
import gym.spaces
import pandas as pd
import numpy as np
import sklearn.preprocessing
from typing_extensions import Literal

class FreezableDict (dict):
    __frozen = False

    def freeze (self):
        self.__frozen = True

    def __setitem__ (self, key, value):
        if self.__frozen and key not in self:
            raise ValueError('Dictionary is frozen')
        super().__setitem__(key, value)


class outrage_trading_env(gym.Env):
    metadata = {'render.modes': ['human']}
    def __init__(self,df:pd.DataFrame,number_of_actions:'Literal[2,3]',reward_reduction_per_step:float=0.0001,df_price:str='Close',df_spread:'str|float|None'='Spread',bars_per_observation:int=64,columns_to_observe:"list[str]"='all',loss_sequence_to_done:int=4,pip_loss_to_done:float=0.035,pip_loss_position_equility_to_done:float=0.035):
        """
        Parameters
        ----------
        *df: pd.dataframe
            a pandas dataframe with the data
        *number_of_actions: 2 or 3
            the number of action in a action space discrete(number), whether 2 the env is buy/sell only whether 3 the is is buy/sell/nothing
        *reward_reduction_per_step:float
            the value the env will decrease from reward each step
        *df_price: string
            name of the column with the price
        *df_spread: string or float or None
            name of the column with the spread if float the spread will be a fixed value and None spread will be 0
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
        """
        
        if isinstance(df,pd.DataFrame):
            pass
        else:
            raise ValueError('df need to be a pandas.dataframe')
        self.data=df
        self.number_of_actions=number_of_actions
        self.reward_reduction_per_step=reward_reduction_per_step
        self.df_price=df_price
        self.df_spread=df_spread
        self.bars_per_observation=bars_per_observation
        self.columns_to_observe=list(self.data.columns) if isinstance(columns_to_observe,str) else columns_to_observe
        self.loss_sequence_to_done=loss_sequence_to_done
        self.pip_loss_to_done=pip_loss_to_done
        self.pip_loss_position_equility_to_done=pip_loss_position_equility_to_done
        self.last_reset_len=0 #storage the last reset lenght and will not be reseted
        self.action_space=gym.spaces.Discrete(2) if self.number_of_actions==2 else gym.spaces.Discrete(3) if self.number_of_actions==3 else None
        self.observation_space=gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.bars_per_observation*len(self.columns_to_observe),),
            dtype=np.float32)
            
    def reset(self):
        self.reward=0
        self.position=FreezableDict({'type':'','opened_price':None,'profit':0.00})
        self.position.freeze()
        self.spread=0.00
        self.sequence_loss=0
        self.number_of_trades=0
        self.total_profit=0.00
        self.total_drawdown=0.00 #total_drawdown contains the summatory of all negative modification to the balance
        self.hightest_total_profit=0.00 #keeps the hightest profit to calculate the equility drawdown
        self.niter=0 #the number of time step has been called
        self.visibledata=self.data.iloc[:self.bars_per_observation] #a dataframe cointaing only the bars_per_opservation
        obs = self.preprocess_obs(obs=self.visibledata[self.columns_to_observe].iloc[-abs(self.bars_per_observation):])
        return obs
    
    def calculate_profit(self):
        """calculate the profit of the actual position"""
        if self.position['opened_price'] is not None:
            if self.position['type']=='buy':
                self.position['profit']=self.visibledata[self.df_price].iloc[-1]-self.position['opened_price'] #the profit is the difference between opened and actual price plus self.spread
            elif self.position['type']=='sell':
                self.position['profit']=self.position['opened_price']-self.visibledata[self.df_price].iloc[-1] #the profit is the difference between opened and actual price plus self.spread

    def calculate_spread(self):
        """update self.sperad at actual nbar"""
        if isinstance(self.df_spread,str):
            self.spread=self.visibledata[self.df_spread].iloc[-1]
        elif isinstance(self.df_spread,(float,int)):
            self.spread=self.df_spread
        elif self.df_spread is None:
            self.spread=0

    def preprocess_obs(self,obs) -> np.array:
        return np.array(np.ravel(sklearn.preprocessing.StandardScaler().fit_transform(X=obs.to_numpy())))

    def step(self,action):
        self.niter += 1
        self.visibledata=self.data.iloc[:self.bars_per_observation+self.niter] #update visibledata
        self.calculate_profit()

        #if dont have any position open position
        if action==0 and self.position['type']=='':
            self.position['type']='buy'
            self.position['opened_price']=self.visibledata[self.df_price].iloc[-2]
            self.calculate_spread()
            self.number_of_trades+=1
        elif action==1 and self.position['type']=='':
            self.position['type']='sell'
            self.position['opened_price']=self.visibledata[self.df_price].iloc[-2]
            self.calculate_spread()
            self.number_of_trades+=1

        #if there a position and the action is different, so change the position
        if self.position['type']=='buy' and action==1: #close buy order and open sell
            self.position['profit']-=self.spread #add spread to the profit
            self.position['type']='sell'
            self.position['opened_price']=self.visibledata[self.df_price].iloc[-2] #write the new opened price
            self.total_drawdown=self.total_drawdown+self.position['profit'] if self.position['profit']<0 else self.total_drawdown
            self.sequence_loss=self.sequence_loss+1 if self.position['profit']<0 else 0 #sequence losses count
            self.total_profit+=self.position['profit']
            self.position['profit']=0.00 #reset the profit of the position
            self.calculate_spread()
            self.number_of_trades+=1
        elif self.position['type']=='sell' and action==0: #close sell order and open buy
            self.position['profit']-=self.spread #add spread to the profit
            self.position['type']='buy'
            self.position['opened_price']=self.visibledata[self.df_price].iloc[-2] #write the new opened price
            self.total_drawdown=self.total_drawdown+self.position['profit'] if self.position['profit']<0 else self.total_drawdown
            self.sequence_loss=self.sequence_loss+1 if self.position['profit']<0 else 0 #sequence losses count
            self.total_profit+=self.position['profit']
            self.position['profit']=0.00 #reset the profit of the position
            self.calculate_spread()
            self.number_of_trades+=1
        elif self.position['type']!='' and action==2: #close buy/sell orders and open nothing
            self.position['profit']-=self.spread #add spread to the profit
            self.position['type']=''
            self.position['opened_price']=None
            self.total_drawdown=self.total_drawdown+self.position['profit'] if self.position['profit']<0 else self.total_drawdown
            self.sequence_loss=self.sequence_loss+1 if self.position['profit']<0 else 0 #sequence losses count
            self.total_profit+=self.position['profit']
            self.position['profit']=0.00

        #update the self.hightest_total_profit keeps the hightest profit
        self.hightest_total_profit=self.total_profit if self.total_profit>self.hightest_total_profit else self.hightest_total_profit

        #calculate the equility
        equility=self.position['profit']+self.total_profit  #the reward is the sum of the profit of the actual position (starts negative due the self.spread) and the total_profit ("balance")

        #calculate reward
        self.reward-=abs(self.reward_reduction_per_step)
        self.reward=self.reward+(self.total_profit+self.position['profit'])

        #calculate the new obsservation
        obs = self.preprocess_obs(obs=self.visibledata[self.columns_to_observe].iloc[-abs(self.bars_per_observation):])

        #calculate info
        info={'action':action,'p_type':self.position['type'],'p_profit':self.position['profit'],'p_profit_with_spread':self.position['profit']-self.spread,'equility':equility,'reward':self.reward,'sequence_loss':self.sequence_loss,'number_of_trades':self.number_of_trades,'total_profit':self.total_profit,'hightest_total_profit':self.hightest_total_profit,'total_drawdown':self.total_drawdown,'position':self.position,'visibledata':self.visibledata}

        #calculate done                                                                                                                                                                                                          V done if the loss "equility total" in pips is lower than V                            V done if the loss "equility" (profit of the position) is lower than V
        if (self.visibledata.index.size >= self.data.index.size) or (self.reward<=-abs(self.pip_loss_to_done)) or (self.sequence_loss >= self.loss_sequence_to_done > 0) or (self.pip_loss_to_done != 0 and self.total_profit <= self.hightest_total_profit - abs(self.pip_loss_to_done)) or (self.pip_loss_position_equility_to_done != 0 and self.position['profit'] <= -abs(self.pip_loss_position_equility_to_done)):
            done=True
        else:
            done=False

        return obs,self.reward,done,info

    def render(self,mode='human'):
        raise NotImplementedError
    def seed(self,seed=None):
        pass
    def close(self):
        self.reset()



