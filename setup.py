from setuptools import setup,find_packages

setup(name='outrage_trading_env',
      version='4.0.1',
      description='A gym-env to do trading (forex/stock/crypto) using reinforcement-learning',
      author='Lucas Monteiro',
      author_email='lucas.ma8338@gmail.com',
      url='https://github.com/lucas8338/outrage-trading-env',
      packages=find_packages(),
      requires=['gym','pandas','numpy','sklearn'],
     )