__author__ = 'GVM'

import psycopg2 as postgres
import psycopg2.extras as postgresExtras
import pandas as pd
import sys
from config import *



class PostgresConnection:
    '''
    Simple wrapper around psycopg2 to connect to Postgres database and expose some
    facilities for interacting with the database.
    '''
    def __init__(self):
        self.connection = None

    def getConnection(self):
        '''
        Initialize a database connection if needed, and return connected database
        '''
        if self.connection is None:
            try:
                self.connection = postgres.connect(database=DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PW, host=DATABASE_IP, port=DATABASE_PORT)
            except :
                print "Unable to establish database connection. Please check connection parameters and/or database."
                exception = sys.exc_info()[0]
                print 'Exception:',exception
        return self.connection

    def executeCopyData(self, table, columns, data, dataSeperator):
        '''
        Excecute a copy of data into a table
        '''
        cursor = self.getConnection().cursor()
        print 'About to copy data into table',table,'for columns',columns
        cursor.copy_from(data,table,columns=columns, sep=dataSeperator)
        self.getConnection().commit()
        cursor.close()

    def executeQuery(self, query, args=None, cursorType=None):
        '''
        Execute a query and return the cursor to the results
        Args must be in tuple format
        '''
        cursor = self.getConnection().cursor() if cursorType is None else self.getConnection().cursor(cursor_factory = cursorType)
        print 'About to execute:',query,' with args:',args
        cursor.execute(query, args)
        return cursor

    def executeSingleInsert(self, query, args):
        '''
        Execute an insert statement and commit it to the database
        '''
        cursor = self.executeQuery(query, args)
        self.getConnection().commit()
        cursor.close()

    def getDataFrameFromQuery(self, query, args):
        '''
        Return a pandas dataframe from a query
        :param query:
        :param args:
        :return:
        '''
        cursor = self.executeQuery(query, args, postgresExtras.RealDictCursor)
        dataframe = pd.DataFrame(cursor.fetchall())
        cursor.close()
        return dataframe


if __name__ == '__main__':
    print 'Running driver...'
    query = 'SELECT * FROM "SecurityMaster" WHERE symbol like %s and instrument_type=\'Equity\''
    args = ('%IBM%',)
    dbObj = PostgresConnection()
    print dbObj.getDataFrameFromQuery(query,args)
