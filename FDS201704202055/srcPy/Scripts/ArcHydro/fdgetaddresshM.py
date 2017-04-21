'''***********************************************************************************************
Tool Name:  fdgetaddresshM (SourceName=fdgetaddresshM.py)
Version:  ArcGIS 10.0
Author:  zye 1/30/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
    (0) pAddressFile= [ComID, H, AddressOID]
    (1) pKisterFile =  [COMDID, Date, Q, H] downloaded ts file 
    (2) Outfile  extracted results [Comid, hmin, AddressOID, ForecastTime, S(m)] 
Description: Find the address whose h value < H of the download.
History:  Initial coding -  zye 2/8/2017
Usage:  fdgetaddresshM.py pAddressFile pKisterFile [OutFile, optional, default=pKisterFile_Out.csv] 
#D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro>
#  python fdgetaddresshM.py D:\10Data\TXDEM\CleanAddress.csv D:\10Data\TXDEM\KisterData\MT20170207134243.csv
## debug:
## D:\10Data\TXDEM\KisterData\MT20170207134243.csv TxAddress100KFilter.csv
## D:\10Data\TXDEM\KisterData\ST20170207233137.csv D:\10Data\TXDEM\CleanAddress.csv
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import numpy as np 

import arcpy

import apwrutils
import fdgetaddressh

def trace():
    import traceback, inspect
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    # script name + line number
    line = tbinfo.split(", ")[1]
    filename = inspect.getfile(inspect.currentframe())
    # Get Python syntax error
    synerror = traceback.format_exc().splitlines()[-1]
    return line, filename, synerror

def getcmdargs(l):
    """ print out command arguments so that it can be used to run at the command line """
    sMsg = ""
    for i in range(len(l)):
        if(i==0): 
            sMsg=l[0]
        else:
            sMsg = "{} {}".format(sMsg, l[i])
    return sMsg
            
if __name__ == '__main__':
    #oProcessor = None
    ds = time.clock()
    try:
        arcpy.env.overwriteOutput = True
        iQHType = fdgetaddressh.QHType.H    #default to check only the H
        debugLevel = 0
        sMsg = apwrutils.Utils.getcmdargs(sys.argv)
        arcpy.AddMessage(sMsg)
        pAddressFile = arcpy.GetParameterAsText(0)
        pKisterFile = arcpy.GetParameterAsText(1)
        bImport = arcpy.GetParameterAsText(2)
        pOutFile = arcpy.GetParameterAsText(3)
        pOutFC = arcpy.GetParameterAsText(4) 

        try:
            bImport = apwrutils.Utils.str2Bool(bImport)
        except:
            bImport = False 

        if(pOutFile==""):
            (pOutFile, ext) = os.path.splitext(pKisterFile)
            pOutFile = "{}_out{}".format(pOutFile,ext) 
         
        #pParams = (pQHFile, pFilter, pOutFile, iQHType, 0)   
        pProcessor = fdgetaddressh.ClassOp()
        pProcessor.DebugLevel = debugLevel
        (sOK, pOutFile, sMsg) = pProcessor.execute(pAddressFile, pKisterFile, pOutFile, fdgetaddressh.QHType.H) 
        if(sOK==apwrutils.C_OK):
            arcpy.SetParameterAsText(3, pOutFile)
            if(bImport):
                (fDir, fName, fExt) = apwrutils.Utils.getFilePathExtName(pOutFile)
                pTable = "{}_Tbl".format(fName)
                dds = time.clock()
                try:
                    i = 0
                    recs = []
                    names = ""
                    formats = (np.int, np.float32, np.uint32, np.str, np.float32)
                    #..expecting the first line of the file contains the "," delimited field names
                    with open(pOutFile, 'r') as f:
                         for s in f: 
                             if(i==0):
                                 names = s.split(",") 
                             else:
                                 arr = s.split(",")
                                 recs.append(arr) 
                             i += 1
                    dts = zip(names, formats)   #{'name' : names, 'formats': formats}
                    #for i in range(0,10):
                    #    arcpy.AddMessage(recs[i])

                    npArray = np.rec.fromrecords(recs, dtype=dts)
                    pOutName = os.path.join(arcpy.env.scratchGDB, "tbltest")
                    arcpy.AddMessage("Construct numpy array of {} recs.  ddt={}".format(i, apwrutils.Utils.GetDSMsg(dds)))
                    ddds = time.clock()
                    if(arcpy.Exists(pOutName)): 
                        arcpy.Delete_management(pOutName)
                    arcpy.da.NumPyArrayToTable(npArray, pOutName )
                    arcpy.AddMessage("using arcpy.da.NumPyArrayToTable: file={} ddt={} dt={}".format(pOutName, apwrutils.Utils.GetDSMsg(ddds), apwrutils.Utils.GetDSMsg(dds)))
                except:
                    arcpy.AddWarning("{}, {}".format(arcpy.GetMessages(2), trace()))

                dds = time.clock() 
                pTableView = fName 
                arcpy.CopyRows_management(pOutFile, pTable)
                arcpy.MakeTableView_management(pTable, pTableView) 
                arcpy.SetParameterAsText(4, pTableView) 
                arcpy.AddMessage("using arcpy.CopyRows_management: file={} dt={}".format(pTable, apwrutils.Utils.GetDSMsg(dds)) )
            #arcpy.CopyRows_management(r"D:\10Data\TXDEM\KisterData\ST20170207233137_out.csv", r"D:\10Data\TXDEM\TX_Demo3_Dec2016_TSOnly.gdb\testtb")
        else:
            arcpy.AddWarning(sMsg) 
        del pProcessor        
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        arcpy.ResetEnvironments()
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at {}.  dtTotal={}'.format(dt.strftime("%Y-%m-%d %H:%M:%S"), apwrutils.Utils.GetDSMsg(ds, "")))

