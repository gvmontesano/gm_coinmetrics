__author__ = 'GVM'

"""
Simple dashboiard for interfacing our portfolio with screening and execution
"""
import os
import math
import requests
import pandas as pd
from pyBloombergManager import pyBbgManager
from pyBloombergManager.constants import EmsxConstants,BloombergServices
from StringIO import StringIO
from xlwings import Workbook, Range, _xlwindows as xlw

EXCEL_FILE = 'Dashboard_v2.xlsm' #Note: this should be in same dir as this python file
POSITIONS_URL = 'https://xxxxx/positions/latest'
USER = 'xxxxx'
PASS = 'xxxxx'

XL_BUTTON = 0
XL_CHECKBOCK = 1
XL_COMBOBOX = 2
XL_LISTBOX = 6

XL_CHECKBOX_OFF = -4146

STARTING_CELL = 'E3'
STARTING_COLUMN_NUM = 5
MAIN_SHEET = 'ControlPanel'
DATA_SHEET = 'Data'
DATA_CELL = 'A1'
# Add anything here that should stay resident on the sheet
PERMANENT_SHAPES = ['PositionButton','Logo','BookFilter', 'PositionNameFilter', 'BloombergListBox', 'CalcButton', 'CalcsListBox', 'PositionToggler', 'AumToggle', 'StagingButton', 'ProdOption', 'BetaOption']
BLOOMBERG_MAP = { 'Bid' : 'BID', 'Ask' : 'ASK',
                  'Mid' : 'PX_MID', 'Delta' : 'DELTA_MID_RT',
                  'Gamma' : 'GAMMA_MID_RT', 'Vega' : 'VEGA_MID_RT',
                  'Theta' : 'THETA_MID_RT', 'Yesterday Close' : 'QUOTE_PRIOR_MID',
                  'Multiplier' : 'PX_POS_MULT_FACTOR',
                  'UnderlyingPx': 'OPT_UNDL_PX',
                  'ImpliedVol' : 'IVOL_MID_RT'}
BLOOMBERG_MAP_FUTS = { 'Bid' : 'BID', 'Ask' : 'ASK',
                  'Mid' : 'PX_MID', 'Delta' : '1',
                  'Gamma' : '0', 'Vega' : '0',
                  'Theta' : '0', 'Yesterday Close' : 'PREV_CLOSE_VAL',
                  'Multiplier' : 'PX_POS_MULT_FACTOR',
                  'UnderlyingPx' : 'PX_MID',
                  'ImpliedVol' : '0'}



def requestToDataframe(url):
    '''
    Simple helper for converting csv data to dataframe from a REST call
    :param url:
    :return:
    '''
    data = requests.get(url, verify=False, auth=(USER,PASS))
    csv = StringIO(data.text)
    return pd.DataFrame.from_csv(csv)


def clearCheckBoxes(workbook):
    '''
    Delete checkbox objects from the sheet
    :param workbook:
    :return:
    '''
    shapeNames = xlw.get_shapes_names(workbook.xl_workbook, workbook.active_sheet.name)
    for i in shapeNames:
        if i not in PERMANENT_SHAPES:
            workbook.xl_workbook.ActiveSheet.Shapes(i).Delete()


def createCheckBoxes(workbook, numPositions):
    '''
    Create the checkboxes on a per position basis
    :param workbook:
    :param numPositions:
    :return:
    '''
    top = 38
    height = 12.75
    for i in range(numPositions):
        cb = workbook.xl_workbook.ActiveSheet.Shapes.AddFormControl(XL_CHECKBOCK, 180, top, 50, 10)
        cb.TextFrame.Characters().Text = 'On/Off'
        cb.Name = 'PositionCheckBox' + str(i)
        top += height

def addBbgCol(positionFrame, workbook, itemNumber):
    '''
    Function for addeding correct bbg formula dependeing on asset type
    :param bbgFieldName:
    :param positionsFrame:
    :return:
    '''
    if positionFrame.instrument_type == 'EquityOption':
        bbgField = BLOOMBERG_MAP[workbook.xl_workbook.ActiveSheet.ListBoxes('BloombergListBox').List[itemNumber]]
        return  '=BDP(\"'+ positionFrame.bloomberg_symbol + '\", \" '+ bbgField + '\")'
    elif positionFrame.instrument_type == 'Future' or  positionFrame.instrument_type == 'Equity':
        bbgField = BLOOMBERG_MAP_FUTS[workbook.xl_workbook.ActiveSheet.ListBoxes('BloombergListBox').List[itemNumber]]
        if bbgField == '0' or bbgField == '1':
            return bbgField
        else :
            return  '=BDP(\"'+ positionFrame.bloomberg_symbol + '\", \" '+ bbgField + '\")'


def populatePositionsOnSheet(workbook, positionFrame, numColumns = 0):
    '''
    Clear the positions from the sheet and repopulate with positions and controls
    :param workbook:
    :param positionFrame:
    :param numOriginalColumns: columns in dataframe before we add bbg columns to it
    :return:
    '''
    Range(STARTING_CELL).table.clear_contents()
    #Range('E:Z').clear_contents()
    #xlw.clear_contents_range(range)s
    clearCheckBoxes(workbook)

    # populate cells with dataframe and controls
    Range(STARTING_CELL, index = False).value = positionFrame
    if numColumns == 0:
        numColumns = positionFrame.shape[1]
    lastColumn = STARTING_COLUMN_NUM + numColumns - 1
    firstRow = Range(STARTING_CELL).table.row + 1
    selectedBbg = workbook.xl_workbook.ActiveSheet.ListBoxes('BloombergListBox').Selected
    listboxCount = 0
    colCount = 1
    for i in selectedBbg:
        if i is True:
            bbgField = BLOOMBERG_MAP[workbook.xl_workbook.ActiveSheet.ListBoxes('BloombergListBox').List[listboxCount]]
            if bbgField in positionFrame:
                positionFrame.drop(bbgField, axis = 1, inplace = True)
            #positionFrame[bbgField] = '=BDP(\"'+ positionFrame.bloomberg_symbol + '\", \" '+ bbgField + '\")'
            positionFrame[bbgField] = positionFrame.apply(addBbgCol, axis = 1, args = (workbook, listboxCount))
            Range( (firstRow - 1,lastColumn +colCount )).value = bbgField # print header to sheet
            Range( (firstRow,lastColumn +colCount), index = False).value = positionFrame[bbgField] # print formula to sheet
            colCount += 1
        listboxCount += 1

    numPositions = positionFrame.shape[0]
    createCheckBoxes(workbook,numPositions)

    return positionFrame


def rePopulateFilteredPositionsOnSheet(workbook, positionFrame):
    '''
    Clear the positions from the sheet and repopulate with positions and controls
    :param workbook:
    :param positionFrame:
    :param numOriginalColumns: columns in dataframe before we add bbg columns to it
    :return:
    '''
    Range(STARTING_CELL).table.clear_contents()
    clearCheckBoxes(workbook)

    # populate cells with dataframe and controls
    Range(STARTING_CELL, index = False).value = positionFrame
    numPositions = positionFrame.shape[0]
    createCheckBoxes(workbook,numPositions)

def midPriceCalc(positionsFrame):
    bidName = BLOOMBERG_MAP['Bid']
    askName = BLOOMBERG_MAP['Ask']
    return (positionsFrame[bidName] + positionsFrame[askName])/2

def netMV(positionsFrameRow):
    bidName = BLOOMBERG_MAP['Bid']
    askName = BLOOMBERG_MAP['Ask']
    multiplier = BLOOMBERG_MAP['Multiplier']
    mid = (positionsFrameRow[bidName] + positionsFrameRow[askName])/2
    if math.isnan(mid):
        return ''
    return (positionsFrameRow.notional_quantity * mid * float(positionsFrameRow[multiplier]))


def populateFilters(workbook, currentPositionsFrame):
    books = currentPositionsFrame.book.unique()
    bookComboBox = workbook.xl_workbook.ActiveSheet.Shapes('BookFilter')
    bookComboBox.ControlFormat.RemoveAllItems()
    for book in books:
        bookComboBox.ControlFormat.AddItem(book)

    shortnames = currentPositionsFrame.position_shortname.unique()
    shortnameBox = workbook.xl_workbook.ActiveSheet.Shapes('PositionNameFilter')
    shortnameBox.ControlFormat.RemoveAllItems()
    for name in shortnames:
        shortnameBox.ControlFormat.AddItem(name)



############################## FUNCTIONS CALLED BY MACROS IN SHEET #################################
def togglePositions():
    '''
    Turn visible checkboxes for each position one or off
    :return:
    '''
    wb = Workbook.caller()
    shapeNames = xlw.get_shapes_names(wb.xl_workbook, wb.active_sheet.name)
    toggleChecked = wb.xl_workbook.ActiveSheet.Shapes('PositionToggler').ControlFormat.Value
    for name in shapeNames:
        if 'PositionCheckBox' in name:
            if toggleChecked == True:
                wb.xl_workbook.ActiveSheet.Shapes(name).ControlFormat.Value = True
            elif toggleChecked == XL_CHECKBOX_OFF:
                wb.xl_workbook.ActiveSheet.Shapes(name).ControlFormat.Value = XL_CHECKBOX_OFF


def getPositions():
    '''
    Populate sheet with all our current positions and add form controls to sheet (checkboxes, comboboxes ets)
    :return:
    '''
    wb = Workbook.caller()
    currentPositionsFrame = requestToDataframe(POSITIONS_URL)

    Range(DATA_SHEET,DATA_CELL).table.clear_contents()  # add positions to a separate sheet used to speed up filtering
    Range(DATA_SHEET,DATA_CELL, index = False).value = currentPositionsFrame
    currentPositionsFrame = populatePositionsOnSheet(wb, currentPositionsFrame)  # populate main 'Control Panel' sheet
    populateFilters(wb, currentPositionsFrame) # populate filters


def filterByBook():
    '''
    Filter existing positions by book name
    :return:
    '''
    wb = Workbook.caller()
    data = Range(DATA_SHEET,DATA_CELL).table.value
    currentPositionsFrame = pd.DataFrame(data[1:], columns=data[0])
    bookComboBox = wb.xl_workbook.ActiveSheet.Shapes('BookFilter')
    selectedIndex = int(bookComboBox.ControlFormat.Value) - 1
    selectedValue = wb.xl_workbook.ActiveSheet.DropDowns('BookFilter').List[selectedIndex]
    if currentPositionsFrame is not None:
        filteredFrame = currentPositionsFrame[currentPositionsFrame.book == selectedValue]
        #rePopulateFilteredPositionsOnSheet(wb, filteredFrame)
        populatePositionsOnSheet(wb, filteredFrame, filteredFrame.shape[1])


def filterByName():
    '''
    Filter existing positions by shortname
    :return:
    '''
    wb = Workbook.caller()
    data = Range(DATA_SHEET,DATA_CELL).table.value
    currentPositionsFrame = pd.DataFrame(data[1:], columns=data[0])
    bookComboBox = wb.xl_workbook.ActiveSheet.Shapes('PositionNameFilter')
    selectedIndex = int(bookComboBox.ControlFormat.Value) - 1
    selectedValue = wb.xl_workbook.ActiveSheet.DropDowns('PositionNameFilter').List[selectedIndex]
    if currentPositionsFrame is not None:
        filteredFrame = currentPositionsFrame[currentPositionsFrame.position_shortname == selectedValue]
        #rePopulateFilteredPositionsOnSheet(wb, filteredFrame)
        populatePositionsOnSheet(wb, filteredFrame, filteredFrame.shape[1])

def calcFields():
    '''
    Retrieve greeks on entire portfolio
    :return:
    '''

    try:
        workbook = Workbook.caller()
        data = Range(MAIN_SHEET,STARTING_CELL).table.value
        portfolio = pd.DataFrame(data[1:], columns=data[0])
        aum = Range('H1').value

        aumToggleChecked = workbook.xl_workbook.ActiveSheet.Shapes('AumToggle').ControlFormat.Value

        portfolio.DELTA_MID_RT = [0 if x == '#N/A N/A' else x for x in portfolio.DELTA_MID_RT]
        portfolio.GAMMA_MID_RT = [0 if x == '#N/A N/A' else x for x in portfolio.GAMMA_MID_RT]
        portfolio.THETA_MID_RT = [0 if x == '#N/A N/A' else x for x in portfolio.THETA_MID_RT]
        portfolio.VEGA_MID_RT = [0 if x == '#N/A N/A' else x for x in portfolio.VEGA_MID_RT]
        portfolio.PX_POS_MULT_FACTOR = portfolio.PX_POS_MULT_FACTOR.astype(float)
        portfolio.OPT_UNDL_PX = portfolio.OPT_UNDL_PX.astype(float)

        if aumToggleChecked == True:
            aumDivisor = aum
        else:
            aumDivisor = 1
        portfolio['dollarDelta'] = (portfolio.notional_quantity * portfolio.OPT_UNDL_PX * portfolio.DELTA_MID_RT * portfolio.PX_POS_MULT_FACTOR) / aumDivisor
        portfolio['dollarGamma'] = (portfolio.notional_quantity * portfolio.OPT_UNDL_PX * portfolio.GAMMA_MID_RT * portfolio.PX_POS_MULT_FACTOR) / aumDivisor
        portfolio['dollarTheta'] = (portfolio.notional_quantity * portfolio.THETA_MID_RT * portfolio.PX_POS_MULT_FACTOR) / aumDivisor
        portfolio['dollarVega'] = (portfolio.notional_quantity * portfolio.VEGA_MID_RT * portfolio.PX_POS_MULT_FACTOR) / aumDivisor

        dollarDelta = portfolio.dollarDelta.sum()
        dollarGamma = portfolio.dollarGamma.sum()
        dollarTheta = portfolio.dollarTheta.sum()
        dollarVega = portfolio.dollarVega.sum()

        FIELD_MAP = {
            'dollarDelta' : dollarDelta,
            'dollarGamma' : dollarGamma,
            'dollarTheta' : dollarTheta,
            'dollarVega'  : dollarVega
        }

        listboxCount = 0
        colCount = 1
        numColumns = portfolio.shape[1] - 4
        lastColumn = STARTING_COLUMN_NUM + numColumns - 1
        firstRow = Range(STARTING_CELL).table.row + 1
        selectedCalcs = workbook.xl_workbook.ActiveSheet.ListBoxes('CalcsListBox').Selected
        for i in selectedCalcs:
            if i is True:
                calcField = workbook.xl_workbook.ActiveSheet.ListBoxes('CalcsListBox').List[listboxCount]
                Range( (firstRow - 1,lastColumn +colCount )).value = calcField # print header to sheet
                Range( (firstRow,lastColumn +colCount), index = False).value = portfolio[calcField] # print formula to sheet
                colCount += 1
                Range( (firstRow - 2, lastColumn -1 +colCount)).value = FIELD_MAP[calcField]
            listboxCount += 1
    except Exception as e:
        print "Exception:",e


def stagePositionsToEmsx():
    wb = Workbook.caller()
    prodOption = wb.xl_workbook.ActiveSheet.Shapes('ProdOption').ControlFormat.Value
    emsxEnvironment = BloombergServices.EMSX_SERVICE if prodOption == 1 else BloombergServices.BETA_EMSX_SERVICE
    bbgManager = pyBbgManager.BloombergManager(emsxEnvironment) # connect to bloomberg TODO: no state so this happens every click - think of something cleverer...

    data = Range(STARTING_CELL).table.value
    selectedPositions = pd.DataFrame(data[1:], columns=data[0])

    # figure out selected positions
    shapeNames = xlw.get_shapes_names(wb.xl_workbook, wb.active_sheet.name)
    rows = []
    count = 0
    for name in shapeNames:
        if 'PositionCheckBox' in name:
            if wb.xl_workbook.ActiveSheet.Shapes(name).ControlFormat.Value == True:
                rows.append(count)
            count += 1
    selectedPositions = selectedPositions.iloc[rows]

    # send orders
    for ticker, qty, limit, book, asset, i in zip(selectedPositions['bloomberg_symbol'], selectedPositions['notional_quantity'], selectedPositions['price'],
                                                 selectedPositions['position_shortname'], selectedPositions['instrument_type'], selectedPositions.index.values):
        if qty > 0 and asset == 'EquityOption':
            side = 'B/O'
        if qty < 0 and asset == 'EquityOption':
            side = 'S/O'

        orderRequest = bbgManager.requestManager.createOrder(ticker=ticker, broker=EmsxConstants.BROKER.PROD, side=side,
                                                              orderType=EmsxConstants.ORDER_TYPE.LIMIT, timeInForce=EmsxConstants.TIME_IN_FORCE.DAY,
                                                              amount=qty, handInstruction='AUTO', **{EmsxConstants.REQUEST_FIELDS.LIMIT_PRICE : limit, EmsxConstants.REQUEST_FIELDS.INVESTOR_ID : book } )
        i = i+1
        bbgManager.requestManager.sendRequest(orderRequest)


###################################### TESTING FUNCTIONS ##############################
def testMain():
    '''
    Simple test of functionality for xlwings based dashboard
    :return:
    '''
    #getPositions()
    #filterByBook()
    #stagePositionsToEmsx()
    calcFields()
    #wb = Workbook.caller()
    #xlrange = xlw.get_range_from_indices(wb.xl_workbook.ActiveSheet, 5,5, 8,10)
    #xlrange.ClearContents()



if __name__ == '__main__':
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), EXCEL_FILE))
    Workbook.set_mock_caller(path)
    testMain()

