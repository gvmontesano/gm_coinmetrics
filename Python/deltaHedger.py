__author__ = 'GVM'

"""
Basic delta hedger that:

1. Computes step sizes
2. Computes scaling
3. Places or adjusts limit orders
4. Monitors
5. Rinse, repeat
"""

import logging
from StringIO import StringIO
import requests
import os
import pandas as pd
import json
from datetime import datetime, timedelta
import time
from xlwings import Workbook, Range, _xlwindows as xlw


#arc libs
from pyBloombergManager.pyBbgManager import BloombergManager as pybbg
from pyBloombergManager.constants import EmsxConstants, BloombergServices
from pyBloombergManager.objects import EmsxOrder, EmsxRoute
from arcpydb import PostgresConnection


logging.basicConfig(level=logging.INFO)
log = logging.getLogger('DeltaHedger')

USER = 'xxxxx'
PASS = 'xxxxx'
SIGNAL_PASS = 'xxxxx'

def requestToDataframe(url, user, pw):
    '''
    Simple helper for converting csv data to dataframe from a REST call
    :param url:
    :return: dataframe object
    '''
    data = requests.get(url, verify=False, auth=(user,pw))
    csv = StringIO(data.text)
    return pd.DataFrame.from_csv(csv)

def requestFromJsonToDataframe(url, user, pw):
    '''
    Simple helper for converting json to dataframe
    :param url:
    :return:
    '''
    data = requests.get(url, verify=False, auth=(user,pw)).text
    return pd.read_json(data)

class Order(object):
    '''
    Simple class to represent an order and it's state
    '''

    def __init__(self):
        self.id = None
        self.price = 0
        self.quantity = 0
        self.status = None


class PortfolioGreeks(object):
    '''
    Simple container for portfolio level greeks
    '''

    def __init__(self):
        self.dollarDelta = 0
        self.dollarGamma = 0
        self.dollarTheta = 0
        self.dollarVega = 0



class DeltaHedger(object):
    '''
    This class encapsulates delta hedging our enitre portfolio.
    1. Get outstanding hedge orders
    2. Comopute steps for reference
    '''
    LATEST_HEDGE_TRADE = 'SELECT * FROM \"Trades\" LEFT JOIN  \"FutureInstrument\" on \"FutureInstrument\".symbol = \"Trades\".symbol ' \
                         'WHERE  \"Trades\".symbol like %s and \"Trades\".status = ANY(%s) and \"Trades\".filled > 0  and \"Trades\".book = %s order by \"Trades\".timestamp desc LIMIT 1'
    ALL_TRADES = 'SELECT * FROM "Trades" WHERE trade_id != \'Integrata\''
    OPEN_ORDERS = 'SELECT * FROM \"Orders\" WHERE order_id in %s'
    HEDGE_INSTRUMENT = 'ES'
    BOOK = 'ES'
    BLOTTER_URL = 'https://xxxxx/blotter'
    SIGNAL_URL = 'https://xxxxx/signalData.json'
    REALIZED_VOL_URL = 'https://xxxxx/historical/csv/intradayBar/1/futures/realizedVol/{}/start/{}/end/{}'
    DATE_FORMAT = '%Y%m%d'
    WST_KEY = '/xxxxx/prod/keys/wst.pem'

    EXCEL_FILE = 'C:\\xxxxx\\excelDashboard\\Dashboard.xlsm'
    STARTING_CELL = 'E3'

    def __init__(self):
        self.lastTradedPrice = 0
        self.db = PostgresConnection()
        self.workingOrders = {} # these contain only working EMSX Routes (trades)
        self.allOrders = {} # container for all orders (EMSXOrder objects)
        self.portfolioGreeks = PortfolioGreeks()
        self.latestTrades = None #latest trades as per db
        self.pybbg = pybbg(emsxServiceName=BloombergServices.EMSX_SERVICE, customSubscriptionCallback=self) # connect to bloomberg


    def getReferenceVolatility(self, howFarBack = timedelta(weeks=1)):
        '''
        Get the realized vol from the hedge instrument
        :return:
        '''
        today = datetime.now()
        end = today.strftime(DeltaHedger.DATE_FORMAT)
        start = (today - howFarBack).strftime(DeltaHedger.DATE_FORMAT)
        url = DeltaHedger.REALIZED_VOL_URL.format(DeltaHedger.HEDGE_INSTRUMENT,start,end)
        refVolFrame = requestToDataframe(url, USER, PASS)
        if refVolFrame.shape[0] == 1:
            return refVolFrame.REALIZED_VOL.values[0]
        return 0 # no reference vol found


    def getSignal(self):
        '''
        Retrieve current signal from signal server
        :return:
        '''
        signalData = requestFromJsonToDataframe(DeltaHedger.SIGNAL_URL,USER,SIGNAL_PASS)
        signalData['TO_DATE']=pd.to_datetime(signalData['TO_DATE'])
        meanHQ = signalData.iloc[-1]['mean_hqs']
        signalDate = signalData.iloc[-1]['TO_DATE']
        return signalData

    def getLastTradePriceFromIntegrata(self):
        '''
        Get last traded price
        :return:
        '''
        blotter = requestToDataframe(DeltaHedger.BLOTTER_URL, USER, PASS)
        blotter=blotter[(blotter['book_name']==DeltaHedger.BOOK) & (blotter['trade_canceled']==False)&(blotter['instrument_type']=='Future')]
        tradeId=blotter[(blotter['book_name']==DeltaHedger.BOOK) & (blotter['trade_canceled']==False)&(blotter['instrument_type']=='Future')]['trade_id'].max()
        lastTradePrice=blotter[blotter['trade_id']==tradeId]['trade_price'].values[0]
        return lastTradePrice

    def getLatestTrades(self):
        '''
        Return the latest trades from the db for the hedge instruments
        :return:
        '''
        status = ['FILLED','PARTFILL',"CXLPREQ"]
        df = self.db.getDataFrameFromQuery(DeltaHedger.LATEST_HEDGE_TRADE, (DeltaHedger.HEDGE_INSTRUMENT + '%',status,DeltaHedger.BOOK ))
        return df

    def findLastTradedPrice(self):
        '''
        Figure our the last price we used for delta hedging via whicchever instrument we're currently using
        :return:
        '''
        if self.latestTrades is not None:
            lastPriceTraded = self.latestTrades['fill_price'].values[0]
            return lastPriceTraded
        return 0

    def getLatestOrdersFromDb(self):
        '''
        Get outstanding orders as per our db
        :return:
        '''
        try:
            trades= self.db.getDataFrameFromQuery(DeltaHedger.ALL_TRADES,pd.np.NaN)
            trade_ids=trades[(trades['status']=='WORKING')&(~trades['trade_id'].isin(trades[trades['status'].isin(['FILLED','CANCEL','CXLREQ'])]['trade_id'].unique()))]['trade_id'].unique()

            orderArgs = (tuple(trade_ids),)
            orders= self.db.getDataFrameFromQuery(DeltaHedger.OPEN_ORDERS,orderArgs)
            orders['timestamp']=orders['timestamp'].apply(lambda x: x.replace(tzinfo=None))
            orders=orders.groupby('order_id').last().reset_index()

            #remove filled order_status
            orders=orders[orders['order_status']!='FILLED']
        except Exception as e:
            print e
            orders=pd.DataFrame()

        return orders


    def getWstGreeks(self):
        start = time.time()
        res = requests.post(
            'https://arc.wsq.io/r/apps/wmp-proxy/exec',
            cert = DeltaHedger.WST_KEY,
            data = json.dumps({
                'local_tasks': [{
                    'func': 'arc.risk.rt.std_values',
                    'args': [False] #argument to calibrate volatility/refit surface
                }]
            }))
        data=res.json()['results'][0]
        df=pd.read_csv(StringIO(data))
        log.info('took {} seconds for WST call..'.format(time.time() - start))
        return df


    def getWorkbookGreeks(self):
        '''
        Retrieve greeks on entire portfolio
        :return:
        '''
        try:
            path = os.path.abspath(os.path.join(os.path.dirname(__file__), DeltaHedger.EXCEL_FILE))
            Workbook.set_mock_caller(path)
            wb = Workbook.caller()
            # TODO: call dashboards' getPositions() in the case where it hasn't been invoked already
            data = Range(DeltaHedger.STARTING_CELL).table.value
            portfolio = pd.DataFrame(data[1:], columns=data[0])
            portfolio.DELTA_MID_RT = [0 if x == '#N/A N/A' else x for x in portfolio.DELTA_MID_RT]
            portfolio.GAMMA_MID_RT = [0 if x == '#N/A N/A' else x for x in portfolio.GAMMA_MID_RT]
            portfolio.THETA_MID_RT = [0 if x == '#N/A N/A' else x for x in portfolio.THETA_MID_RT]
            portfolio.VEGA_MID_RT = [0 if x == '#N/A N/A' else x for x in portfolio.VEGA_MID_RT]
            portfolio.PX_POS_MULT_FACTOR = portfolio.PX_POS_MULT_FACTOR.astype(float)
            portfolio.OPT_UNDL_PX = portfolio.OPT_UNDL_PX.astype(float)

            portfolio['dollarDelta'] = portfolio.notional_quantity * portfolio.OPT_UNDL_PX * portfolio.DELTA_MID_RT * portfolio.PX_POS_MULT_FACTOR
            portfolio['dollarGamma'] = portfolio.notional_quantity * portfolio.OPT_UNDL_PX * portfolio.GAMMA_MID_RT * portfolio.PX_POS_MULT_FACTOR
            portfolio['dollarTheta'] = portfolio.notional_quantity * portfolio.THETA_MID_RT * portfolio.PX_POS_MULT_FACTOR
            portfolio['dollarVega'] = portfolio.notional_quantity * portfolio.VEGA_MID_RT * portfolio.PX_POS_MULT_FACTOR

            self.portfolioGreeks.dollarDelta = portfolio.dollarDelta.sum()
            self.portfolioGreeks.dollarGamma = portfolio.dollarGamma.sum()
            self.portfolioGreeks.dollarTheta = portfolio.dollarTheta.sum()
            self.portfolioGreeks.dollarVega = portfolio.dollarVega.sum()

        except Exception as e:
            log.error('Exception {}'.format(e))
        return self.portfolioGreeks


    def computeSteps(self):
        '''
        Figure ouit steps of where to place limit orders
        :return:
        '''
        self.latestTrades = self.getLatestTrades()
        lastTradedPrice = self.findLastTradedPrice()
        blotterLast = self.getLastTradePriceFromIntegrata()
        print 'last from db:',lastTradedPrice,'\tfrom blotter:',blotterLast

        greeks = self.getWorkbookGreeks()

        referenceVol = self.getReferenceVolatility()
        print 'Using reference vol of',referenceVol,'for',DeltaHedger.HEDGE_INSTRUMENT

        expectedDaye = 1.0
        expectedMove = lastTradedPrice * .17 * pd.np.sqrt(expectedDaye/365)
        expectedPercent = expectedMove / lastTradedPrice
        print 'Expected move for',expectedDaye, ' day(s) is', expectedPercent

        steps = [x for x in range(-5,4)]
        contractMultiplier = self.latestTrades


        limitLadder=pd.DataFrame([x*expectedPercent for x in steps], index=pd.Series(steps,name='steps'),columns=['expectedMove']).iloc[::-1]

        limitLadder['dDelta']= limitLadder.expectedMove*100*greeks.dollarGamma #*ddelta..
        limitLadder['price']= (limitLadder.expectedMove*lastTradedPrice)+lastTradedPrice
        limitLadder['tradeNotional']=limitLadder.dDelta-greeks.dollarDelta
        limitLadder['qty']=-limitLadder.dDelta/(self.latestTrades.contract_unit.values[0]*limitLadder['price'])
        limitLadder['Last Trade']=self.latestTrades.timestamp.values[0]
        limitLadder['Last Qty']=self.latestTrades.filled.values[0]
        limitLadder['Traded Price']=lastTradedPrice
        limitLadder['refVol']=referenceVol
        limitLadder['$ Gamma']=greeks.dollarGamma

        #format
        limitLadder['expectedMove']=(100.0*limitLadder['expectedMove']).map('{:,.1f}%'.format)
        print limitLadder.head()



    def sendOrders(self):
        '''
        Send orders to exhange
        :return:
        '''

    def monitorOrders(self):
        pass


    def cleanupAfterInitialSubscribe(self):
        '''
        Make sure local orders/working orders cache is clean
        :return:
        '''
        for orderId,order in self.workingOrders.items():
            if orderId not in self.allOrders:
                del self.workingOrders[orderId]

    def callback(self,bbgEvent):
        '''
        Callback
        :param bbgEvent:
        :return:
        '''
        for msg in bbgEvent:
            msgType = msg.getElementAsString(EmsxConstants.MSG_TYPE)
            if msgType == EmsxConstants.MESSAGE_TYPES.EVENT:
                eventStatus = msg.getElementAsInteger(EmsxConstants.MSG_EVENT_STATUS)
                if eventStatus == EmsxConstants.EVENT_STATUS.HEARTBEAT:
                    print 'Heartbeat...'
                else:
                    if msg.hasElement(EmsxConstants.MSG_SUBTYPE):
                        subType = msg.getElementAsString(EmsxConstants.MSG_SUBTYPE)
                        if subType == EmsxConstants.MESSAGE_SUBTYPES.ORDER:
                            order = EmsxOrder(msg)
                            if DeltaHedger.HEDGE_INSTRUMENT in order.getTicker():
                                print 'adding key',order.getOrderId(),'for order\t',order
                                self.allOrders[order.getOrderId()] = order
                        if subType == EmsxConstants.MESSAGE_SUBTYPES.ROUTE:
                            route = EmsxRoute(msg)
                            if  route.getStatus() == EmsxConstants.ORDER_STATUS.WORKING  :
                                self.workingOrders[route.getOrderId()] = route
                                if route.getOrderId() in self.allOrders:
                                    print 'route event for ',self.allOrders[route.getOrderId()].getTicker,'\t',route
                                else:
                                    print 'first route msg:',route

def runMain():
    log.info('Launching delta hedger...')
    deltaHedger = DeltaHedger()
    deltaHedger.computeSteps()
    while True:
        x = raw_input('Enter q to quit')
        if x == 'q':
            break


if __name__ == '__main__':
    runMain()
