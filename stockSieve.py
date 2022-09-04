#根据因子选股票

import pandas as pd
import dataPretreatment
from rqdatac import init,get_trading_dates,all_instruments
from datetime import datetime

init()
#获取一段时间内的交易日
marketTime = get_trading_dates(20040101, 20201001)

#所有股票信息
stockList = all_instruments(type='CS')


#factorList的结构:因子名字;(True/false)的标志位,True表示数值小的做多,False表示数值小的做空;第三个位置是换仓周期
'''factorSettingList = [['valueFactor',True,1],['momentum',False,1],['waveRatio365',True,1],
              ['waveRatio250',True,1],['turnover30',True,1],['turnover90',True,1],
                  ['shareCirculation',True,1],['shareTotal',True,1],['interest',False,1]]'''
#我们暂时只关心其中一部分因子咯
#事实上我们先把所有东西都算完了的哦这里只是注释掉了，包括后面的percent的循环，这里把30%的省略啦
#这是事后为了后面的计算方便这么写的
factorSettingList = [['valueFactor',True,1],['momentum',False,1],
              ['waveRatio250',True,1],['turnover30',True,1],
                  ['shareTotal',True,1],['shareCirculation',True,1],['interest',False,1]]

#因子数据
#date,code,tag,factordata（这个地方是valueFactor,momentum,waveRatio365,waveRatio250,turnover30,turnover90,shareCirculation,shareTotal,interest）,listedDate
data = pd.read_csv(r'data_valuefactor_waveratio_momentum_turnover_share_interst_listdate.csv')
data = data.set_index(['date','code'])
dp = dataPretreatment.dataPretreatment()

index = data.index.levels[0]
#为了保证dateList按顺序在走，不能直接字符串排序，数字在'/'的前面
#不是很了解这个pd解析csv中值类型的机制，明明是'xxxx/xx/xx'读出来是'xxxx-xx-xx'
try:
    dateList = [datetime.strptime(time,'%Y/%m/%d') for time in index]
    dateList.sort()
    dateList = [str(time.year) + '/' + str(time.month) + '/' + str(time.day) for time in dateList]
    marketTime = [str(date.year) + '/' + str(date.month) + '/' + str(date.day) for date in marketTime]
except:
    dateList = [datetime.strptime(time, '%Y-%m-%d') for time in index]
    dateList.sort()
    dateList = [str(time.year) + '-' +'0'*(-len(str(time.month))+2)+ str(time.month) + '-' + str(time.day) for time in dateList]
    marketTime = [str(date.year) + '-' +'0'*(-len(str(date.month))+2)+  str(date.month) + '-' +'0'*(-len(str(date.day))+2)+ str(date.day) for date in marketTime]

#计算日期，属于池（属于沪深300，写300，属于中证500，写500，全部A股就写A），
# 比例（30%或20%），因子（比如A股流通市值）,股票代码，
# 对应股票当时的A股流通市值，做多还是做空（long/short）；
stockPool = pd.DataFrame(columns=('date','tag','percent','factor','code','share','longOrShort','value'))

#根据因子，百分比,选股
def sieve(factorData,percent,shortFlag,tag):
    #总的股票数量
    quantity = len(factorData)
    #多\空头的量
    quantity = int(quantity * percent)
    if shortFlag:
        #做空池就选因子数据偏后的股票（注意什么做空什么做多）
        pool = factorData.iloc[-quantity:]
    else:
        pool = factorData.iloc[:quantity]
    #筛选后的写入到temp中并返回
    temp = pd.DataFrame(columns=('date', 'tag', 'percent', 'factor', 'code', 'share', 'longOrShort', 'value'))
    temp['code'] = pool.index
    temp['share'] = list(pool['share'])
    if shortFlag:
        temp['longOrShort'] = 'short'
    else:
        temp['longOrShort'] = 'long'
    temp['tag'] = tag
    temp['percent'] = str(percent * 100) + '%'
    temp['date'] = day
    temp['factor'] = factor
    temp['value'] = list(pool[factor])
    return temp

#循环选股的逻辑
#调仓日
for day in dateList:
    print(day)
    transferDayData = data.loc[day]
    stockList = transferDayData.index

    #本掉仓日在交易日的位置
    todayLocation = marketTime.index(day)
    #根据约定，有的股票需要上市半年后才纳入股票池，有的是一年，有的是10天，这里都算一算吧
    specialHalfYearTransferDayData = transferDayData.copy(deep=True)
    specialOneYearTransferDayData = transferDayData.copy(deep=True)
    temp = pd.DataFrame(columns=('date', 'tag', 'percent', 'factor', 'code', 'share', 'longOrShort', 'value'))
    #判断上市span
    for stock in stockList:
        listedDay = transferDayData.loc[stock]['listedDate']
        # 上市天数
        try:
            # 这里markettime取的区间是04年以后的,上市时间在05年以前,这里index取不到,显然上市天数已经大于10了,扔给except做个简便处理
            num = todayLocation - marketTime.index(listedDay) + 1
        except:
            num = 256

        #获取上市时间
        if num < 250:
            print(stock + '上市不满1年')
            specialOneYearTransferDayData = specialOneYearTransferDayData.drop(stock)
        if num < 125:
            print(stock + '上市不满半年')
            specialHalfYearTransferDayData = specialHalfYearTransferDayData.drop(stock)

        if num<10:
            print(stock+'是新股')
            transferDayData = transferDayData.drop(stock)
            #stockListedCheckFlag.loc[stock]['flag']=1

    for factorSetting in factorSettingList:

        #不到换仓周期
        if (dateList.index(day)-3)%factorSetting[2]!=0:
            continue
        factor = factorSetting[0]
        factorFlag = factorSetting[1]
        print(factor)
        #根据约定，'waveRatio250','waveRatio365','momentum'上市半年才考虑，股息率上市一年才考虑
        if factor in ['waveRatio250','waveRatio365','momentum']:
            factorData = specialHalfYearTransferDayData[factor]
        else:
            if factor == 'interest':
                factorData = specialOneYearTransferDayData[factor]
                factorData = factorData[factorData!=0]
            else:
                factorData = transferDayData[factor]
        factorData = factorData. dropna()
        if len(factorData)==0:
            #有的数据全是nan,drop之后就成了空dataframe后面要出bug,直接下一圈循环就好了
            continue
        #数据预处理，详见datapretreatment接口
        factorData = dp.normalize(factorData)
        factorData = dp.winsorize(factorData)
        factorData = pd.DataFrame(factorData,columns=[factor])
        factorData['share'] = transferDayData['shareCirculation']
        if factor!='shareCirculation':

            #避免出现同样数值的样本太多,比如说股息率,一半多都是0
            #增加一个二级选股指标
            factorData = factorData.sort_values([factor,'share'],ascending=[factorFlag,True])

        else:
            factorData = factorData.sort_values([factor],ascending=[factorFlag])
        factorData['tag'] = transferDayData['tag']

        for tag in ['A', '300', '500']:
            #数据表中非300非500标注的A,而这里是在算所有的A股
            if tag=='A':
                factorDataNew = factorData
            else:
                factorDataNew = factorData.loc[factorData['tag'] == tag]
            if len(factorDataNew)==0:
                print(tag+'指数还没有推出')
                continue
            for percent in [0.2, ]:

                #空
                temp = temp.append(sieve(factorDataNew, percent, True, tag))
                #多
                temp = temp.append(sieve(factorDataNew, percent, False, tag))

    stockPool = stockPool.append(temp)

stockPool.to_csv('stockPool.csv',index=False)
