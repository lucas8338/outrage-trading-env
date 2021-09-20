# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['outrage_trading_env', 'outrage_trading_env.libs']

package_data = \
{'': ['*']}

install_requires = \
['gym>=0,<1', 'numpy>=1,<2', 'pandas>=1,<2', 'sklearn>=0,<1']

setup_kwargs = {
    'name': 'outrage-trading-env',
    'version': '2.0.0',
    'description': 'A gym-env to do trading (forex/stock/crypto) using reinforcement-learning',
    'long_description': None,
    'author': 'Lucas Monteiro',
    'author_email': 'lucas.ma8338@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3',
}


setup(**setup_kwargs)
