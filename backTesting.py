#用于回测
#已求得股票池，计算历史表现
#stock.csv:date,tag,percent,factor,code,share,longOrShort,value(这里value值暂时用不到)

import pandas as pd
import numpy as np
from rqdatac import init,get_price_change_rate,all_instruments
from datetime import datetime
init()

#读取股票池数据
stockPool = pd.read_csv(r'stockPool.csv')

#主键有点多,遍历这些主键咯
stockPool = stockPool.set_index(['date','tag','percent','factor','longOrShort'])

timeSeries = stockPool.index.levels[0]
tags = stockPool.index.levels[1]
percents = stockPool.index.levels[2]
factors = stockPool.index.levels[3]

#datetime数据写入csv以后成了字符串，读出来也是字符串，直接拿到的日期数据又是numpy的时间，需要转换

#不是很了解这个pd解析csv中值类型的机制，明明是'xxxx/xx/xx'读出来是'xxxx-xx-xx'
try:
    timeSeries = [datetime.strptime(time, '%Y/%m/%d') for time in timeSeries]
    timeSeries.sort()
except:
    timeSeries = [datetime.strptime(time, '%Y-%m-%d') for time in timeSeries]
    timeSeries.sort()
#所有股票信息
stockList = all_instruments(type='CS')

#一次性多拿一点数据,否则在取得股票池后再取数据一方面会有大量数据重复取用,一方面api的响应速度真的很慢
#价格变动率
priceChangeData = get_price_change_rate(stockList['order_book_id'],timeSeries[0],timeSeries[-1])
#存放收益率的df
backTest = pd.DataFrame(columns=('tag','percent','factor','returnRatio','date'))
#不要最后一个时刻的回测，没得必要，比如2020.6.30调仓后就是七月份的收益咯，暂时不关心
for time in timeSeries[:-1]:
    print(time)
    #loc到调仓日
    try:
        transferDayStockPool = stockPool.loc[str(time.year)+'/'+str(time.month)+'/'+str(time.day)]
    except:
        transferDayStockPool = stockPool.loc[str(time.year) + '-' +'0'*(-len(str(time.month))+2)+ str(time.month) + '-' + str(time.day)]
    #下一个调仓日
    nextTransferDay = timeSeries[timeSeries.index(time)+1]
    #他的index是datetime64[ns]类型的数据,numpy的模块转字符串到dt64对字符串要求为xxxx-xx-xx,太死板了,借用一下datetime
    periodReturnRate = priceChangeData.loc[np.datetime64(time,'ns'):
                                           np.datetime64(nextTransferDay,'ns')]
    periodReturnRate = periodReturnRate.iloc[:-1]
    # 交易日的index
    timeIndex = periodReturnRate.index
    for tag in tags:
        try:
            #中证500发布较晚,较早的数据没有500的池子
            transferDayStockPoolClassifiedByTag = transferDayStockPool.loc[tag]
        except:
            continue
        #for percent in percents:
        #改变了需求咯，暂时不要30%的配额咯
        for percent in ['20.0%', ]:
            transferDayStockPoolClassifiedByTagAndPercent = transferDayStockPoolClassifiedByTag.loc[percent]
            for factor in factors:
                try:
                    #有时候因子数据全部缺失,导致池子为空
                    transferDayStockPoolClassifiedByTagAndPercentAndFactor = transferDayStockPoolClassifiedByTagAndPercent.loc[factor]
                except:
                    continue
                totalReturnRatio = []
                #后面用的totalReturnRatio的第一个减第二个哦，第一个是多头收益，第二个是空头，注意对应
                for longFlag in ['long','short']:
                    stocksData = transferDayStockPoolClassifiedByTagAndPercentAndFactor.loc[longFlag]
                    stocks = list(stocksData['code'])
                    #权重取流通市值
                    power = stocksData['share']
                    #总的权
                    totalPower = sum(power)
                    #转为矩阵，方便收益计算
                    power = np.mat(power)
                    returnRate = periodReturnRate[stocks]
                    returnRate = np.mat(returnRate)

                    #每日收益
                    dailyReturnRate = power*returnRate.T/totalPower
                    #临时保存在这个list里面
                    totalReturnRatio.append(pd.DataFrame(dailyReturnRate.T))
                    #属于池（属于沪深300，写300，属于中证500，写500，全部A股就写A），
                    # 比例（30%或20%），因子（比如A股流通市值），多空组合每日收益，日期（从2005年6月30日到2020年6月30日）
                temp = pd.DataFrame(columns=('tag','percent','factor','returnRatio','date'))
                temp['date'] = timeIndex
                temp['tag'] = tag
                temp['percent'] = percent
                temp['factor'] = factor
                #做多收益减去做空收益
                temp['returnRatio'] = totalReturnRatio[0]-totalReturnRatio[1]
                backTest = backTest.append(temp)
backTest.to_csv('backTesting.csv',index=False)