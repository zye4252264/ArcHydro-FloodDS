'''***********************************************************************************************
Tool Name:  fdgroupbystatsM (SourceName=fdgroupbystatsM.py)
Version:  ArcGIS 10.0
Author:  zye 1/30/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
    (0) pKisterFile =  [COMDID, Date, Q, H] downloaded ts file or (Filtered by address/max operation, Find the address whose h value < H of the download.)
    (1) iValueIndex = int(arcpy.GetParameterAsText(1))
    (2) iGroupIndex = int(arcpy.GetParameterAsText(2))
    (3) iStats = int(arcpy.GetParameterAsText(3)) = (1:Count,2:Avg,4:Max,8:Min,16:Sum,32:Std)
    (4) Outfile Stats [GroupBy, Count, Avg, Max, Min, Sum, Std] 
Description: 
History:  Initial coding -  zye 2/28/2017
Usage:  fdgroupbystatsM.py pAddressFile C:\10DATA\TXDEM\KisterData\KisterDAtaMT_Out.csv 4 0 63 
# D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro>python fdgroupbystats.py C:\10DATA\TXDEM\KisterData\KisterDAtaMT_Out.csv 4 0 63
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import numpy as np 

import arcpy

import apwrutils
import fdgroupbystats

K_Sep = ","

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
    debugLevel = 0
    try:
        bImport = True 
        arcpy.env.overwriteOutput = True
        pQHFile = arcpy.GetParameterAsText(0)  
        iValueIndex = int(arcpy.GetParameterAsText(1))
        iGroupIndex = int(arcpy.GetParameterAsText(2))
        iStats = int(arcpy.GetParameterAsText(3))
        pOutFile = ""
        if(pOutFile==""):
            (pOutFile, ext) = os.path.splitext(pQHFile)
            pOutFile = "{}_stats{}".format(pOutFile,ext) 
         
        #pParams = (pQHFile, pFilter, pOutFile, iQHType, 0)   
        pProcessor = fdgroupbystats.ClassOp()
        pProcessor.DebugLevel = debugLevel
        pParams = (pQHFile, iValueIndex, iGroupIndex, iStats, pOutFile)
        (sOK, pOutFile, sMsg) = pProcessor.execute(pParams)   #pQHFile, pOutFile, iValueIndex, iGroupIndex, iStats) 
        if(sOK==apwrutils.C_OK):
            arcpy.AddMessage("pOutFile={}".format(pOutFile))
            arcpy.SetParameterAsText(4, pOutFile)
            if(bImport):
                (fDir, fName, fExt) = apwrutils.Utils.getFilePathExtName(pOutFile)
                pTable = "{}_Tbl".format(fName)
                dds = time.clock()
                #try:
                #    i = 0
                #    recs = []
                #    names = ""
                #    formats = (np.int, np.float32, np.uint32, np.str, np.float32)
                #    #..expecting the first line of the file contains the "," delimited field names
                #    with open(pOutFile, 'r') as f:
                #         for s in f: 
                #             if(i==0):
                #                 names = s.split(",") 
                #             else:
                #                 arr = s.split(",")
                #                 recs.append(arr) 
                #             i += 1
                #    dts = zip(names, formats)   #{'name' : names, 'formats': formats}
                #    #for i in range(0,10):
                #    #    arcpy.AddMessage(recs[i])

                #    npArray = np.rec.fromrecords(recs, dtype=dts)
                #    pOutName = os.path.join(arcpy.env.scratchGDB, "tbltest")
                #    arcpy.AddMessage("Construct numpy array of {} recs.  ddt={}".format(i, apwrutils.Utils.GetDSMsg(dds)))
                #    ddds = time.clock()
                #    if(arcpy.Exists(pOutName)): 
                #        arcpy.Delete_management(pOutName)
                #    arcpy.da.NumPyArrayToTable(npArray, pOutName )
                #    arcpy.AddMessage("using arcpy.da.NumPyArrayToTable: file={} ddt={} dt={}".format(pOutName, apwrutils.Utils.GetDSMsg(ddds), apwrutils.Utils.GetDSMsg(dds)))
                #except:
                #    arcpy.AddWarning("{}, {}".format(arcpy.GetMessages(2), trace()))
                dds = time.clock() 
                pTableView = fName 
                arcpy.CopyRows_management(pOutFile, pTable)
                arcpy.MakeTableView_management(pTable, pTableView) 
                arcpy.SetParameterAsText(5, pTableView) 
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
        arcpy.AddMessage('Finished at {}. dtTotal={}'.format(dt.strftime("%Y-%m-%d %H:%M:%S"), apwrutils.Utils.GetDSMsg(ds, "")))

