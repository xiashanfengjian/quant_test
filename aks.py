import akshare as ak
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import dateutil
import random


if True:
    matplotlib.rcParams['axes.linewidth']       = 1
    matplotlib.rcParams['xtick.major.size']     = 6
    matplotlib.rcParams['xtick.major.width']    = 1
    matplotlib.rcParams['xtick.minor.size']     = 6
    matplotlib.rcParams['xtick.minor.width']    = 1
    matplotlib.rcParams['ytick.major.size']     = 6
    matplotlib.rcParams['ytick.major.width']    = 1
    matplotlib.rcParams['ytick.minor.size']     = 6
    matplotlib.rcParams['ytick.minor.width']    = 1
    matplotlib.rcParams['ytick.direction']     = 'in'
    matplotlib.rcParams['xtick.direction']    = 'in'

    matplotlib.rcParams['xtick.major.pad']      = 10
    matplotlib.rcParams['ytick.major.pad']      = 10

    matplotlib.rcParams['mathtext.default']     = 'regular'
#-- End

def trade_get():
    enable_hist_df = ak.tool_trade_date_hist_sina()
    enable_hist_df.columns = ['list','trade_date',]
    enable_hist_df['trade_date'] = pd.to_datetime(enable_hist_df['trade_date'])
    return enable_hist_df

def get_stock(code,fq):
    # 获取并保存数据
    try:
        f = open(code+'.csv','r')
        stock_df = pd.read_csv(f)
    except:
        print(1)
        stock_df = ak.stock_zh_a_hist(symbol=code, adjust=fq).iloc[:, :6]
        stock_df.columns = [
            'date',
            'open',
            'close',
            'high',
            'low',
            'volume',
        ]
        stock_df.to_csv(code + '.csv')
    stock_df.index = pd.to_datetime(stock_df['date'])
    stock_df.index_col = 'date'
    return stock_df

# 获取一定范围内的数据
def Stock_range(stock_df,Context,enable_hist_df,td,count):
    list = stock_df['date'].tolist()
    try:
        index = list.index(td.strftime('%Y-%m-%d'))
        stock_range = stock_df[stock_df['date'].between(stock_df['date'][index-count],stock_df['date'][index-1])]
    except:
        stock_range = []
    # print(stock_range)
    return stock_range

# 预留，上面函数似乎过于复杂，留待简化
def Stock_hist(td,code,count):
    return

# 后续考虑滑点
def get_today_data(Context,code):
    today = Context.dt.strftime('%Y-%m-%d')
    da = get_stock(code,Context.fq)
    data = da[da['date']==today][:]
    return data

# 已经考虑停牌，后续考虑分红
def order_root(Context,today_price,code,amount,o_or_c):
    if len(today_price) == 0:
        print(f"\033[33m{'今日停牌！'}\033[0m")
        return
    ymd = today_price['date'][0]
    today_price = today_price[o_or_c][0]
    if amount>0:
        if Context.cash - amount*today_price < 0:
            amount = int(int(Context.cash/today_price)/100)
            if amount == 0:
                print(f"\033[31m{ymd}\033[0m",f"\033[33m{':现金严重不足，无法买入！！！'}\033[0m")
            else:
                amount = amount*100
                print(f"\033[31m{ymd}\033[0m",f"\033[33m{':现金不足，已帮您调整为%d' % (amount)}\033[0m")
        else:
            amount = int(amount/100)
            amount = amount*100
            print(f"\033[31m{ymd}\033[0m",f"\033[33m{':现金充足，已做整数调整，调整后买入%d' % (amount)}\033[0m")
    else:
        if amount+Context.positions.get(code,0)<=0:
            if amount+Context.positions.get(code,0)<0:
                amount = -Context.positions.get(code,0)
                print(f"\033[31m{ymd}\033[0m",f"\033[33m{':持仓不足，全仓卖出！'}\033[0m")
            elif Context.positions.get(code,0)==0:
                amount = -Context.positions.get(code,0)
                print(f"\033[31m{ymd}\033[0m",f"\033[33m{':持仓为0，无法卖出！'}\033[0m")
            elif amount+Context.positions.get(code,0)==0:
                amount = -Context.positions.get(code,0)
                print(f"\033[31m{ymd}\033[0m",f"\033[33m{':持仓刚好，全仓卖出！'}\033[0m")
            

        else:
            amount = int(amount/100)
            amount = amount*100
            print(f"\033[31m{ymd}\033[0m",f"\033[33m{':持仓充足，已做整数调整，调整后卖出%d' % -amount}\033[0m")

    Context.cash -= amount*today_price
    # print(Context.cash)
    Context.positions[code] = Context.positions.get(code,0)+amount
    # print(Context.positions)
    if Context.positions[code] == 0:
        del Context.positions[code]
    return

def order(Context,code,amount,o_or_c):
    today_price = get_today_data(Context,code)
    order_root(Context,today_price,code,amount,o_or_c)

def order_target(Context,code,amount,o_or_c):
    if amount<0:
        print('数量不能为负，已调整为0')
    today_price = get_today_data(Context,code)
    hold_amount = Context.positions.get(code,0)
    delta_amount = amount - hold_amount
    order_root(Context,today_price,code,delta_amount,o_or_c)

def order_value(Context,code,value,o_or_c):
    today_price = get_today_data(Context,code)
    amount = int(value/today_price[o_or_c][0])
    order_root(Context,today_price,code,amount,o_or_c)

def order_target_value(Context,code,value,o_or_c):
    if value<0:
        print('价值不能为负，已调整为0')

    # 停牌是否有问题
    today_price = get_today_data(Context,code)
    hold_value = Context.positions.get(code,0)*today_price[o_or_c][0]
    delta_value = value - hold_value
    order_value(Context,code,delta_value,o_or_c)

# 非常重要，这是一个全局类，用于方便用户在初始化函数和策略函数里随心所欲地定义变量，这些变量都会被存在g的属性里
class G:
    pass
g = G()

# 回测函数
def run(Context):
    Init(Context)
    init_ben = benchmark(Context)
    init_cash = Context.cash
    plt_value = pd.DataFrame(index=pd.to_datetime(Context.date_range['trade_date']),columns=['value'])
    last_prize = {}
    for td in Context.date_range['trade_date']:
        Context.dt = dateutil.parser.parse(str(td))
        handle(Context,td)
        Cash = Context.cash
        for stock_code in Context.positions:
            today_p = get_today_data(Context,stock_code)
            if len(today_p) == 0:
                p = last_prize[stock_code]
            else:
                p = today_p['open'][0]
                last_prize[stock_code] = p
            Cash += p*Context.positions[stock_code]
            
        plt_value.loc[td,'value'] = Cash

        # benchmark
        today_p_ben = get_today_data(Context,Context.benchmark)
        if len(today_p_ben) == 0:
            p2 = last_prize[Context.benchmark]
        else:
            p2 = today_p_ben['close'][0]
            last_prize[Context.benchmark] = p2
        plt_value.loc[td,'value_ben'] = p2
        # print(Cash)

    # plot
    plt_value['return'] = (plt_value['value']-init_cash) / init_cash
    plt_value['benchmarker'] = (plt_value['value_ben'] - init_ben) / init_ben
    plt_value[['return','benchmarker']].plot()
    plt.axhline(y=0,c='grey',ls='--',lw=1,zorder=0)
    plt.grid(alpha=0.4)
    plt.xlabel(u'Date',fontsize=16)
    plt.ylabel(u'Return',fontsize=16)
    plt.show()

def set_benchmark(Context,code):
    Context.benchmark = code

def benchmark(Context):
    stock_df = get_stock(Context.benchmark,Context.fq)
    stock_range = stock_df[stock_df['date'].between(Context.date_start,Context.date_end)]
    # stock_range[['close']].plt()
    init_r = stock_range['close'][0]
    return init_r

class Context:
    def __init__(self, cash, date_start, date_end, fq):
        self.cash = cash
        self.date_start = date_start
        self.date_end = date_end
        self.fq = fq
        self.positions = {}
        self.benchmark = '00'
        self.date_range = enable_hist_df[enable_hist_df['trade_date'].between(date_start,date_end)]
        self.dt = None  # dateutil.parser.parse(date_start)

def print_end():
    print('初始化完成')

# # 用户函数：

# def Init(Context):
#     g.code = '600036'
#     set_benchmark(Context,g.code)
#     g.c = 'open'
#     g.k = 2
#     g.cash = Context.cash
#     print_end()
#     pass

# # ---------------------------------------------
# enable_hist_df = pd.read_csv('history.csv',parse_dates=['trade_date'])
# enable_hist_df.columns = [
#     'list',
#     'trade_date',
# ]
# # ---------------------------------------------

# def handle0(Context,td):
#     # 是否要考虑停牌？
#     history = Stock_range(get_stock(g.code,Context.fq),Context,enable_hist_df,td,10)
#     if len(history) == 0:
#         print(f"\033[34m{'今日停牌，不交易'}\033[0m")
#     else:
#         ma5 = history['close'][-5:].mean()
#         ma20 = history['close'][:].mean()
#         if ma5>ma20 and g.code not in Context.positions:
#             order_value(Context,g.code,Context.cash,g.c)
#         elif ma5<ma20 and g.code in Context.positions:
#             order_target(Context,g.code,0,g.c)
#     return

# def handle1(Context,td):
#     # 是否要考虑停牌？
#     history = Stock_range(get_stock(g.code,Context.fq),Context,enable_hist_df,td,20)
#     if len(history) == 0:
#         print(f"\033[34m{'今日停牌，不交易'}\033[0m")
#     else:
#         ma = history['close'][:].mean()
#         up = ma + g.k*history['close'].std()
#         low = ma - g.k*history['close'].std()

#         p = get_today_data(Context,g.code)['close'][0]

#         cash = Context.cash
#         if p <= low and g.code:
#             order_value(Context,g.code,g.cash/5,g.c)
#         elif p >= up and g.code in Context.positions:
#             order_target(Context,g.code,0,g.c)
#     return

# def handle(Context,td):
#     p = get_today_data(Context,g.code)
#     if len(p) == 0:
#         print(f"\033[34m{'今日停牌，不交易'}\033[0m")
#     else:
#         a = random.choice([0,1])
#         if a==0:
#             order_value(Context,g.code,Context.cash/2,g.c)
#         else:
#             order_target(Context,g.code,Context.positions[g.code]/2,g.c)



        



