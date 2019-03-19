__author__ = 'GVM'

import xlwings as xw
import pandas as pd
import os
import ftplib
import Naked.toolshed.shell
from StringIO import StringIO
from arcpydb import PostgresConnection

main_path = 'C:/xxxxx/FTP/'
master_wb_path = 'C:/xxxxx/NAV-Margin_MasterTemplate_Basic_v3.xlsx'

server = 'xxxxx'
username = 'xxxxx'
password = 'xxxxx'
directory = 'xxxxx'
filematch_margin = '*Risk*.pdf'

not_in_dir = []

# Establish FTP connection, download only the PDF Margin files not found in directory.
# Returns not_in_dir list of the files that have been downloaded.

def ftp_get():

    ftp = ftplib.FTP(server)
    ftp.login(username, password)
    ftp.cwd(directory)

    for filename in ftp.nlst(filematch_margin):
		filepath =  os.path.normpath(main_path + filename)
		if os.path.exists(main_path + filename) == False:
			fhandle = open(filepath, 'wb')
			print 'Getting ' + filename
			ftp.retrbinary('RETR %s' % filename, fhandle.write)
			fhandle.close()
			not_in_dir.append(filename)
			print 'Completed ' + filename + ' download.'

    return not_in_dir

# Convert downloaded PDF Margin files into CSV, then use Excel master template to extract only margin data.
# Returns master_pd which contains extracted margin data from not_in_dir list of files.

def convert_into_df():

    master_pd = pd.DataFrame()

    for files in not_in_dir:
        print 'Converting ' + files + ' into CSV.'
        no_ext_name = files.replace(' ','')[:-3]
        csv_name = no_ext_name + "csv"
        pdf_name = no_ext_name + "pdf"

        Naked.toolshed.shell.execute("C:/jruby-1.7.23/bin/tabula.bat -p all -a 18.49,15.09,577.38,742.45 -o " + (main_path+csv_name) + " " + (main_path+pdf_name))

        comp_path = main_path + csv_name

        wb1 = xw.Workbook(comp_path)
        raw_data = xw.Range('A1:H1500', atleast_2d = True, wkb = wb1).value

        wb2 = xw.Workbook(master_wb_path)
        xw.Range('main', 'A1:H1500', atleast_2d = True, wkb = wb2).value = raw_data

        copy_margin = xw.Range('main', 'N9:Q1500', atleast_2d = True, wkb = wb2).value

        margin_data = pd.DataFrame(copy_margin).dropna()
        margin_data = margin_data.reset_index(drop=True)

        master_pd = master_pd.append(margin_data)

        wb1.close()
        wb2.close()

        print 'Completed extracting ' + files + ' CSV data into data frame.'

    master_pd.columns=['Account', 'Date', 'Symbol', 'Margin']
    master_pd = master_pd.reset_index(drop=True)
    master_pd['Date'] = master_pd['Date'].apply(lambda x: x.date())

    return master_pd

# Copy master_pd margin data to "Margins" table in database.

ftp_get()

db = PostgresConnection()

secMasterFrame = convert_into_df()

data = StringIO(secMasterFrame.to_csv(header=False,index=False,sep='\t'))

db.executeCopyData(table='"Margins"', columns=('account','date','symbol','margin'), data=data, dataSeperator='\t')

query = 'SELECT * FROM "Margins"'
args = ()
dbObj = PostgresConnection()

print dbObj.getDataFrameFromQuery(query,args)
