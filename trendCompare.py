import pandas as pd
import csv

class netValue(object):
    def __init__(self,returnRatio,tagList,factorList,percentList):
        #returnRatio，日线级回报率，一维迭代器即可；tagList，factorList,percentList,分别是标签，因子，百分数的集合
        self.returnRatio = returnRatio
        self.tagList = tagList
        self.factorList = factorList
        self.percentList  = percentList

    @staticmethod
    def calcAccumulatedReturnRatio(returnRatio):
        #计算累计回报率
        accumulatedReturnRatio = [1, ]
        for i in returnRatio:
            accumulatedReturnRatio.append(accumulatedReturnRatio[-1] * (1 + i))
        return accumulatedReturnRatio

    def loop(self):
        #循环逻辑
        netValueAll = pd.DataFrame(columns=['tag', 'factor', 'percent', 'date', 'netValue'])
        for tag in self.tagList:
            try:
                returnRatioGroupByTag = self.returnRatio.loc[tag]
            except:
                continue
            for factor in self.factorList:
                try:
                    returnRatioGroupByTagAndFactor = returnRatioGroupByTag.loc[factor]
                except:
                    continue

                for percent in self.percentList:
                    #loc到具体的回报率df
                    returnRatio = returnRatioGroupByTagAndFactor.loc[percent]
                    temp = pd.DataFrame(columns=['tag', 'factor', 'percent', 'date', 'netValue'])
                    #复制日期
                    temp['date'] = returnRatio['date'].values
                    returnRatio = returnRatio['returnRatio']
                    returnRatio = list(returnRatio)
                    accumulatedReturnRatio = self.calcAccumulatedReturnRatio(returnRatio)
                    temp['netValue'] = pd.DataFrame(accumulatedReturnRatio[1:])
                    temp['tag'] = tag
                    temp['factor'] = factor
                    temp['percent'] = percent
                    netValueAll = netValueAll.append(temp)
        return netValueAll

#计算净值
def calcAccumulatedReturnRatio(returnRatio):
    accumulatedReturnRatio = [1, ]
    for i in returnRatio:
        accumulatedReturnRatio.append(accumulatedReturnRatio[-1]* (1 + i))
    return accumulatedReturnRatio

#读取各个组合每日收益的情况
returnRatioAll = pd.read_csv(r'backTesting.csv')
returnRatioAll = returnRatioAll.set_index(['tag','factor','percent'])
#先复制一个一模一样大小的dataframe
netValueAll = pd.DataFrame(columns=['tag','factor','percent','date','netValue'])
#totalReturn.csv记录总的收益率
f = open('totalReturn.csv','w+', newline='')
dataCsv = csv.writer(f)
factors = returnRatioAll.index.levels[1]
for tag in ['300','500','A']:
    returnRatioGroupByTag = returnRatioAll.loc[tag]
    for factor in factors:
        returnRatioGroupByTagAndFactor = returnRatioGroupByTag.loc[factor]
        #for percent in ['20.0%','30.0%']:
        for percent in ['20.0%', ]:
            returnRatio = returnRatioGroupByTagAndFactor.loc[percent]
            #temp临时储存数据
            temp = pd.DataFrame(columns=['tag', 'factor', 'percent', 'date', 'netValue'])
            temp['date'] = returnRatio['date'].values
            returnRatio = returnRatio['returnRatio']
            returnRatio = list(returnRatio)
            accumulatedReturnRatio = calcAccumulatedReturnRatio(returnRatio)
            temp['netValue'] = pd.DataFrame(accumulatedReturnRatio[1:])
            temp['tag'] = tag
            temp['factor'] = factor
            temp['percent'] = percent

            netValueAll = netValueAll.append(temp)
            dataCsv.writerow([tag,factor,percent,accumulatedReturnRatio[-1]])
f.close()
netValueAll.to_csv('netReturnRatio.csv',index=False)
import matplotlib.pyplot as plt
from os import path,mkdir
#判断有没有trendCompare的文件夹，没有就新建
pathStr = 'trendCompare'
if not path.exists(pathStr):
    mkdir(pathStr)
#这儿画图的时候就只选择了部分factor和percent，当然你愿意的话直接改一下isin的逻辑就好了
data = netValueAll
#data = data[data.factor.isin(['valueFactor','momentum','waveRatio250','turnover30','shareTotal','shareCirculation','interest'])]
#data = data[data.percent.isin(['20.0%'])]
#写个sortindex避免警告
data = data.set_index(['tag','factor','percent']).sort_index()
for tag in ['300','500','A']:
    tempData = data.loc[tag]
    plt.figure()
    plt.title('tag:' + tag)
    maxLength = 0
    for factor in ['valueFactor','momentum','waveRatio250','turnover30','shareTotal','shareCirculation','interest']:
        if tempData.loc[factor,'date'].size>maxLength:
            maxLength = tempData.loc[factor,'date'].size
            date = tempData.loc[factor,'date']
    for factor in ['valueFactor', 'momentum', 'waveRatio250', 'turnover30', 'shareTotal', 'shareCirculation',
                       'interest']:
        tempLength = tempData.loc[factor,'date'].size
        # 折线图
        plt.plot(date, [1,]*int(maxLength-tempLength)+list(tempData.loc[factor,'netValue']),
                 label=factor)

    # 获取句柄
    ax = plt.gca()
    # 设置x轴
    ax.set_xticks(date.iloc[0::250])
    plt.xticks(rotation=45, fontsize=6)
    # 图例
    plt.legend()
    #plt.show()
    plt.savefig('trendCompare\\_tag_'+tag+'.png')
    plt.close()
