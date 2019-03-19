__author__ = 'GVM'

from StringIO import StringIO

import pandas as pd

from xxxxx.databaseDriver import PostgresConnection

db = PostgresConnection()

seperator = ','

#TODO : replace this with process for dumping hanweck tables to csv
equityPath = '/path/to/equities.csv'
optionsPath = '/path/to/options.csv'

updateUnderliersQuery = 'update "EquityOptionInstrument"  as e set underlying_ticker = s.symbol from  "SecurityMaster" s where s.instrument_type = \'Equity\' and e.hanweck_equity_id = s.hanweck_id'

def loadHanweckEquitiesIntoSecurityMasters():
    '''
    A data dump from hanweck's equity security master into our own database
    Requires a .csv of the their table to be used as the data source
    :return:
    '''
    equityFrame = pd.read_csv(equityPath)
    print 'loaded equities csv data...'

    equityFrame['instrumentType'] = 'Equity'
    equityFrame['currency'] = 'USD'
    cols = ['instrumentType', 'ticker', 'currency', 'eqId', 'cusip', 'startDate', 'endDate']

    # Copy to 'SecurityMaster' table
    secMasterFrame = equityFrame[cols]
    data = StringIO(secMasterFrame.to_csv(header=False,index=False))
    db.executeCopyData(table='"SecurityMaster"', columns=('instrument_type','symbol','currency','hanweck_id','cusip', 'start_date','end_date'), data=data, dataSeperator=',')

    # Copy to 'EquityInstrument' table
    commonColumn = ['arc_id']
    originalHanweckColumns = ['issuer']
    dbSecMasterFrame = db.getDataFrameFromQuery('Select * from "SecurityMaster" where instrument_type = \'Equity\'', None)
    equityInstrumentTableData = pd.concat([dbSecMasterFrame[commonColumn], equityFrame[originalHanweckColumns]], axis = 1) #assume dataframes sorted the same
    data = StringIO(equityInstrumentTableData.to_csv(header=False,index=False, sep='\t'))
    db.executeCopyData(table='"EquityInstrument"', columns=('arc_id', 'company_name'), data=data, dataSeperator='\t')
    print 'finished populating equity data from hanweck source...'


def loadHanweckOptionsIntoSecurityMasters():
    '''
    A data dump from hanweck's option security master into our own database
    :return:
    '''
    optionsFrame = pd.read_csv(optionsPath)
    optionsFrame.expDate = pd.to_datetime(optionsFrame.expDate)
    optionsFrame.strike = optionsFrame.strike.apply(lambda x : x if str(x).find(',') == False else str(x).replace(',','')).astype(float) #convert to numerical value
    optionsFrame.multiplier = optionsFrame.multiplier.apply(lambda x : float(x) if str(x).find(',') == False else str(x).replace(',','')).astype(float) #convert to numerical value
    print 'loaded options csv data...'

    optionsFrame['instrumentType'] = 'EquityOption'
    optionsFrame['currency'] = 'USD'
    cols = ['instrumentType', 'osiTicker', 'currency', 'optId', 'startDate', 'endDate']

    # Copy to 'SecurityMaster' table
    secMasterFrame = optionsFrame[cols]
    data = StringIO(secMasterFrame.to_csv(header=False,index=False))
    #db.executeCopyData(table='"SecurityMaster"', columns=('instrument_type','symbol','currency','hanweck_id', 'start_date','end_date'), data=data, dataSeperator=',')

    # Copy to 'EquityOptionInstrument' table

    # Combine dataframes for insertion
    commonColumn = ['arc_id']
    originalHanweckColumns = ['strike', 'osiTicker', 'expDate', 'exercise', 'putCall', 'multiplier', 'eqId']
    dbSecMasterFrame = db.getDataFrameFromQuery('Select * from "SecurityMaster" where instrument_type = \'EquityOption\'', None)
    equityOptionInstrumentTableData = pd.concat([dbSecMasterFrame[commonColumn], optionsFrame[originalHanweckColumns]], axis = 1) #assume dataframes sorted the same
    data = StringIO(equityOptionInstrumentTableData.to_csv(header=False,index=False, sep='\t'))
    db.executeCopyData(table='"EquityOptionInstrument"', columns=('arc_id', 'strike', 'osi_code', 'expiration_date', 'exercise_type', 'put_call', 'multiplier', 'hanweck_equity_id'), data=data, dataSeperator='\t')

    print 'updating underliers...'
    db.executeQuery(updateUnderliersQuery, None)
    print 'finished populating equity option data from hanweck source...'





if __name__ == '__main__':
    #loadHanweckEquitiesIntoSecurityMasters()
    loadHanweckOptionsIntoSecurityMasters()
