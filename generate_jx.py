# -*- coding: utf-8 -*-
# @Time    : 2020/9/27 19:03
# @File    : generate_jx.py
"""
    
"""

import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import statsmodels.api as sm
from statsmodels.regression.rolling import RollingOLS
from tqdm import tqdm
import rqdatac

rqdatac.init('15221650016', '123456')


# import os
# os.chdir(os.path.dirname(__file__))


START = '2014-07-01'
END = '2019-08-01'

#fund_id

fund_info = rqdatac.fund.all_instruments(date=END)
fund_ids = fund_info.loc[fund_info.de_listed_date == '0000-00-00'].order_book_id
cat = rqdatac.fund.get_instrument_category(fund_ids).reset_index()
fund_ids = list(set(cat.order_book_id) - set(cat.loc[cat.category_type == 'bond_type'].order_book_id))





def three_fs(start_, end_date):
    '''
    计算Vol_ExRe_W，AlphaIR_Sharpe，Alpha_TM三因子的函数

    Parameters
    ----------
    start_ : str
    end_date : str

    Returns
    -------
    pd.DataFrame*3

    '''

    # benchmark
    benchmark_price = rqdatac.get_price('000902.XSHG', start_, end_date, frequency='1d', fields='close')

    # indics
    idx = ['000919.XSHG', '000918.XSHG', 'H30352.XSHG', 'H30351.XSHG']
    indics_price = rqdatac.get_price(idx, start_, end_date, frequency='1d', fields='close')

    # bond
    yield1 = rqdatac.get_yield_curve(start_, end_date)['1M']

    Vol_ExRe_W = []
    AlphaIR_Sharpe = []
    Alpha_TM = []
    fund_prices = rqdatac.fund.get_nav(ids, '2000-01-01', end_date, fields='unit_net_value')
    for fund_id in ids:
        fund = fund_info.loc[fund_info.order_book_id == fund_id].T
        if fund.shape[1] > 1:
            fund = fund.loc[:, fund.loc['transition_time'] == 1]
        fund_id_info = pd.Series(fund.values.flatten(), index=fund.index)
        listed_date = fund_id_info['listed_date']

        start = max(start_.strftime('%Y-%m-%d'), listed_date)
        # fund_price = rqdatac.fund.get_nav(fund_id, start_date, end_date=END,fields='unit_net_value')

        if fund_id not in fund_prices.columns:
            print('Cannot get fund_price!', fund_id)
            continue

        fund_price = fund_prices[fund_id][start:].dropna()

        # 1  Vol_ExRe_W
        def func(x):
            if len(x):
                y = x.iloc[-1] / x.iloc[0] - 1
                return y
            else:
                return 0

        fund_returns = fund_price.resample('W').apply(func).dropna()
        drop_list = ['2015-08-02', '2015-11-01', '2019-01-06']
        # sz50s = sz50s.drop(sz50s[(sz50s.symbol.isin(drop_list))].index)
        fund_returns = fund_returns.drop(fund_returns[(fund_returns.index.isin(drop_list))].index)
        # benchmark_returns_q = benchmark_price.resample('W').apply(func).dropna()
        # fund_returns.to_csv(r'H:\size3\fund_returns2.csv')
        # benchmark_returns_q.to_csv(r'H:\size3\benchmark_returns_q.csv')
        # print(fund_returns)
        # print(benchmark_returns_q)

        benchmark_returns = benchmark_price.resample('W').apply(func).dropna().loc[fund_returns.index]
        weeks = len(fund_returns)
        period = 26  # 52代表一年，26代表半年
        if weeks < period:
            print('data length is not enough!', fund_id)
            continue
        excess_returns = fund_returns - benchmark_returns
        vol_ExRe_W = excess_returns.rolling(period).std() * np.sqrt(period)
        vol_ExRe_W.name = fund_id
        Vol_ExRe_W.append(vol_ExRe_W)

        # 3 Alpha_TM
        yield_week = yield1.resample('W').mean().fillna(0).dropna().loc[fund_returns.index] / 52
        y = fund_returns - yield_week
        x = benchmark_returns - yield_week
        X = pd.concat([x, x ** 2], axis=1)
        alpha_TM = RollingOLS(y, sm.add_constant(X), period).fit().params['const']
        alpha_TM.name = fund_id
        Alpha_TM.append(alpha_TM)

        # 2 AlphaIR_Sharpe
        fund_returns = fund_price.resample('W').apply(func).dropna()
        fund_returns = fund_returns.drop(fund_returns[(fund_returns.index.isin(drop_list))].index)
        d = fund_returns.index[0]
        if not d.month % 3:
            d = d.replace(day=30) + timedelta(days=2)
            d = d.replace(day=1)
        fund_returns = fund_returns.loc[d:]
        indics_returns = indics_price.resample('W').apply(func).dropna().loc[fund_returns.index]
        # fund_returns.to_csv(r'H:\size3\fund_returns2.csv')
        # indics_returns.to_csv(r'H:\size3\indics_returns2.csv')
        # print(fund_returns)
        # print(indics_returns)

        fund_returns = fund_returns.drop(fund_returns[(fund_returns.index == fund_returns.index[-1])].index)
        alpha = fund_returns.resample('Q'). \
            apply(lambda y: sm.OLS(y, sm.add_constant(indics_returns.loc[y.index]), missing='drop').fit().params['const'])
        alphaIR_Sharpe = alpha.rolling(2).apply(lambda x: x.mean() / x.std())  # 4代表一年， 2代表半年
        alphaIR_Sharpe.name = fund_id
        AlphaIR_Sharpe.append(alphaIR_Sharpe)

    Vol_ExRe_W = pd.concat(Vol_ExRe_W, axis=1).resample('D').ffill()
    AlphaIR_Sharpe = pd.concat(AlphaIR_Sharpe, axis=1).resample('D').ffill()
    Alpha_TM = pd.concat(Alpha_TM, axis=1).resample('D').ffill()
    return Vol_ExRe_W, AlphaIR_Sharpe, Alpha_TM


#########################


# 获取自然日
nature_date = pd.date_range('1/1/2000', '8/1/2019')
nature_date_df = pd.DataFrame()
nature_date_df['datetime'] = nature_date

###################################################

# recurrent
dates = pd.date_range(START, END, freq='MS', closed='left')
print('dates:  ', dates)
edate = fund_info[['order_book_id', 'listed_date']].set_index('order_book_id')['listed_date']

periods = {}
for i in range(1, len(dates)):
    end_date = dates[i]
    print('end_date:  ', end_date)
    start_date = dates[i - 1]

    year = end_date.year
    e_2 = end_date.replace(year=year - 2)
    e_1 = start_date.replace(year=year - 1).strftime('%Y-%m-%d')

    fund_id = [i for i in fund_ids if edate[i] < e_1]
    ids, div = cal_div(fund_id, e_2, end_date)

    print(ids)
    print(len(ids))




    # Vol_ExRe_W, AlphaIR, AlphaTM
    Vol_ExRe_W, AlphaIR_Sharpe, Alpha_TM = three_fs(e_2, end_date)

    data['Vol_ExRe_W'] = Vol_ExRe_W.loc[start_date:end_date].stack()
    data['AlphaIR_Sharpe'] = AlphaIR_Sharpe.loc[start_date:end_date].stack()
    data['Alpha_TM'] = Alpha_TM.loc[start_date:end_date].stack()

 
    data = pd.merge(data, merge_all, on=['date', 'order_book_id'], how='inner')
    periods[end_date] = data
    # print(periods)

factors = pd.concat(periods.values())
# 需要将因子导出到任意路径
factors.to_csv(r'H:\size\factors.csv')

