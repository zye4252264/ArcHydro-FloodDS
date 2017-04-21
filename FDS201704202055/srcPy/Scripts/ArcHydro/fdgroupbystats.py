'''***********************************************************************************************
Tool Name:  fdgroupbystats (SourceName=fdgroupbystats.py)
Version:  ArcGIS 10.3
Author:  zye 2/27/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
  0 pQHFile=downloaded ts file [COMDID, Date, Q, H]
  1 iValueIndex=index of the column holding the values to apply statistics to
  2 GroupByIndex=index of the column to group by
  3 iStats = 1,2,4,8,16,32 (1=Count,2=Avg,4=Max,8=Min,16=Sum,32=Std) and combination of these values: ..3,5,7 etc.
  4 pOutFile (optional) = Output file for extracted values ComID,Date, Q, H

pQHFile's format: (ST_Data_max_AddH.csv)
COMID,HANDHM,AddressID,AdrsPop10,CountyID,DistrictID,RegionID,TSTime, Sm

Description: For each comid, find stats of h (or q).
History:  Initial coding -  2/27/2017
Usage:  fdgroupbystats.py C:\10DATA\TXDEM\KisterData\KisterDataMT_Out.csv 4 0 63
#  python fdgroupbystats.py C:\10DATA\TXDEM\KisterData\KisterDataMT_Out.csv 4 0 63

#  cmds:
ComID:
python fdgroupbystats.py C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 3 0 63 C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH_StatsComID.csv
C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 3 0 63 C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH_StatsComID.csv
CountyId:
python fdgroupbystats.py C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 3 4 63 C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH_StatsCountyID.csv
C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 3 4 63 C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH_StatsCountyID.csv
DistrictID:
python fdgroupbystats.py C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 3 5 63 C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH_StatsDistID.csv
C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 3 5 63 C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH_StatsDistID.csv
python fdgroupbystats.py C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 3 6 63 C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH_StatsRegD.csv
C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 3 6 63 C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH_StatsRegD.csv
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import numpy as np 
import arcpy
import apwrutils

import flooddsconfig

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

"""define the TSValueStatsOp class"""
class ClassOp:
    #variables:
    def __init__(self):
        self.DebugLevel = 0

    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())
    # Load the configuration xml.
    
    def getWorkspace(self, pFL):
        oDesc = arcpy.Describe(pFL)
        ooDesc = arcpy.Describe(oDesc.path)
        if(ooDesc.dataType=='FeatureDataset'):
            sWorkspace = ooDesc.path
        else:
            sWorkspace = oDesc.path

        return sWorkspace

    """ execute(self, pParams=(pQHFile, iValueIndex, iGroupByIndex, iTSTimeIndex, iStats, lParentIDs, pOutFile, pTblOut, pGDBOut, modelID) """
    def execute(self, pParams):    #pQHFile, iValueIndex, iGroupByIndex, iStats, lParentIDs, pOutFile):
        """ pQHFile=downloaded ts file [COMDID, Date, Q, H]
            iValueIndex=index of the column holding the values to apply statistics to
            GroupByIndex=index of the column to group by
            iStats = 1,2,4,8,16,32 (1=Count,2=Avg,4=Max,8=Min,16=Sum,32=Std) and combination of these values: ..3,5,7 etc.
            lParentIDs = list ParentIDs to be maitained.
            pOutFile = Output file for extracted values ComID,Date, Q, H
        """
        #r"D:\ProjectsUtils\HydroProjects\ApUtilityTools\Scripts\ApUtilityTools\nwm.short_range.channel_rt.forecasts_per_section_vertical.csv"
        sMsg = ""
        sOK = apwrutils.C_OK 
        ds = time.clock()
         
        try:
            (pQHFile,iValueIndex, iGroupByIndex, iTSIndex, iStats, lParentIDs, pOutFile)  = pParams       #, pTblOut, pGDBOut, lFldsOp, modelID) = pParams 
            if((self.DebugLevel & 1)==1):
                sMsg = apwrutils.Utils.getcmdargs(pParams) 
                arcpy.AddMessage(sMsg)   
            l = []
            ComIDLast = ""
            valueMax = -999999.0
            lValuesMax = []
            dds = time.clock()
            with open(pQHFile, 'r') as f:
                l = f.readlines()
            
            nCnt = len(l)
            nMod = nCnt/20
            if(nMod<1):
                nMod=1 
            dds = time.clock()
            iAdded = 0
            dds = time.clock()
            dDataset = dict()   #..dict whose key=groupbyvalue.
            dHeaders = dict()   #..dict, key=groupbyidvalue, value=list of ParentIDs, eg. comid's parentids are CountyID, DistID, and RegID.
            dTSTimes = dict()   #..dict, key=groupbyidvalue, value=DateTime of first accurence of the event.
            sMsg = "Constructing group by values..."
            arcpy.AddMessage(sMsg)
            sHeader = ""
            sHeaderP = ""
            try:
                sHeader = l[0]
                sHeader = sHeader.replace("\n", "")
                arr = sHeader.split(",")
                sHeader = arr[iGroupByIndex]
                if(len(lParentIDs) > 0):
                    for pid in lParentIDs:
                        if(sHeaderP==""):
                            sHeaderP = arr[pid]
                        else: 
                            sHeaderP = "{},{}".format(sHeaderP, arr[pid])
            except:
                sMsg = trace()
                arcpy.AddMessage(sMsg)

            nStatsCnt = 0
            for i, s in enumerate(l):
                try:
                    s = s.replace('\n','')
                    sArr = s.split(K_Sep) 
                    sGroupBy = sArr[iGroupByIndex]
                    d = -9999
                    try:
                        d = float(sArr[iValueIndex])
                        nStatsCnt = nStatsCnt + 1
                    except:
                        pass
                    if(d!=-9999):
                        if(sGroupBy in dDataset):
                            l = dDataset[sGroupBy]
                            l.append(d)
                        else:                        
                            l = []
                            l.append(d)
                            try:
                                lHeaders = [] 
                                for pid in lParentIDs:
                                    lHeaders.append(sArr[pid])
                                dHeaders.setdefault(sGroupBy, lHeaders) 
                            except:
                                pass
                            dDataset.setdefault(sGroupBy, l) 
                         
                        if((iTSIndex>0) and ((sGroupBy in dTSTimes)==False)):
                            try:
                                sTSTime = sArr[iTSIndex]
                                if(sTSTime!=""):
                                    dTSTimes.setdefault(sGroupBy, sTSTime) 
                            except:
                                pass
                             
                    if((self.DebugLevel & 1)==1):
                        if(i % nMod)==0:
                            sMsg = "  processing {} of {} recs with {} distinct group values found. ddt={}".format(i, nCnt, len(dDataset), apwrutils.Utils.GetDSMsg(dds))
                            arcpy.AddMessage(sMsg)
                            dds = time.clock()
                except:
                    pass
                          
            sMsg = "Completed constructing group by values of {} recs with {} distinct group values found.. dt={}".format(nCnt, len(dDataset), apwrutils.Utils.GetDSMsg(ds))
            arcpy.AddMessage(sMsg) 
            if((iStats & flooddsconfig.StatsType.Count)==flooddsconfig.StatsType.Count): sHeader = "{},{}".format(sHeader, "Count")
            if((iStats & flooddsconfig.StatsType.Avg)==flooddsconfig.StatsType.Avg): sHeader = "{},{}".format(sHeader, "Avg")
            if((iStats & flooddsconfig.StatsType.Max)==flooddsconfig.StatsType.Max): sHeader = "{},{}".format(sHeader, "Max")
            if((iStats & flooddsconfig.StatsType.Min)==flooddsconfig.StatsType.Min): sHeader = "{},{}".format(sHeader, "Min")
            if((iStats & flooddsconfig.StatsType.Sum)==flooddsconfig.StatsType.Sum): sHeader = "{},{}".format(sHeader, "Sum")
            if((iStats & flooddsconfig.StatsType.Std)==flooddsconfig.StatsType.Std): sHeader = "{},{}".format(sHeader, "Std")
            if(sHeaderP<>""): sHeader = "{},{}".format(sHeader, sHeaderP) 
            if(iTSIndex>0): sHeader = "{},{}".format(sHeader, "TSTime")

            nKeys = len(dDataset) 
            nMod = int(nKeys/20)
            if(nMod<1): nMod = 1 
            sMsg = "Calculating {} statistics of {} group values".format(nStatsCnt, len(dDataset))
            arcpy.AddMessage(sMsg) 
            with open(pOutFile,'w') as fout:
                fout.write("{}\n".format(sHeader))
                for i, sKey in enumerate(dDataset):
                    try:
                        lValues = dDataset[sKey]
                        arr = np.array(lValues) 
                        lStats = []
                        try:
                            if((iStats & flooddsconfig.StatsType.Count)==flooddsconfig.StatsType.Count): lStats.append(len(arr))
                            if((iStats & flooddsconfig.StatsType.Avg)==flooddsconfig.StatsType.Avg): lStats.append(arr.mean())
                            if((iStats & flooddsconfig.StatsType.Max)==flooddsconfig.StatsType.Max): lStats.append(arr.max())
                            if((iStats & flooddsconfig.StatsType.Min)==flooddsconfig.StatsType.Min): lStats.append(arr.min())
                            if((iStats & flooddsconfig.StatsType.Sum)==flooddsconfig.StatsType.Sum): lStats.append(arr.sum())
                            if((iStats & flooddsconfig.StatsType.Std)==flooddsconfig.StatsType.Std): lStats.append(arr.std())
                            sout = ",".join(str(o) for o in lStats)
                            sout = "{},{}".format(sKey, sout)
                            if(sHeaderP<>""):
                                try:
                                    lParentIDVs = dHeaders[sKey]
                                    for pid in lParentIDVs:
                                        sout = "{},{}".format(sout, pid)

                                except:
                                    pass

                            if(iTSIndex>0):
                                sTSTime = ""
                                if(sKey in dTSTimes):
                                    try:
                                        sTSTime = dTSTimes[sKey]
                                    except:
                                        pass
                                    #..if TSTime is not of a correct value, append a blank (sTSTime=""), for consistency in structure. 
                                sout = "{},{}".format(sout, sTSTime)

                            fout.write("{}\n".format(sout))
                        except:
                            pass

                    except:
                        pass
                    finally:
                        if((self.DebugLevel & 1)==1):
                            if((i % nMod)==0): 
                                sMsg = "  Processing {} stats on {} recs of {}.  dt={}".format(nStatsCnt, i, nKeys, apwrutils.Utils.GetDSMsg(dds))
                                arcpy.AddMessage(sMsg)
                

                sMsg = "Completed processing {} stats on {} group values.  dt={}".format(nStatsCnt, nKeys, apwrutils.Utils.GetDSMsg(dds))
                arcpy.AddMessage(sMsg)   

        except:
            ss = trace()
            arcpy.AddMessage(ss)
            sOK = apwrutils.C_NOTOK
        finally:
            pass 
        return (sOK, pOutFile, sMsg) 
    
            
if __name__ == '__main__':
    #oProcessor = None
    ds = time.clock()
    pGDBOut = r"C:\10DATA\TXDEM\KisterData\TXStats.gdb"
    try:
        iValueIndex = flooddsconfig.QHType.H    #default to check only the H
        lParentIDs = []
        iGroupByIndex = 0
        iStats =  flooddsconfig.StatsType.Count + flooddsconfig.StatsType.Avg + flooddsconfig.StatsType.Max + flooddsconfig.StatsType.Min + flooddsconfig.StatsType.Sum + flooddsconfig.StatsType.Std 
        
        debugLevel = 0
        if(len(sys.argv)<2):
            #C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 4 0 63
            arcpy.AddMessage("Usage: {} {} {}".format(sys.argv[0], "KistDownTSFile_AddH ValueFieldIndex=4 GroupByIndex=0 Stats=63"))
            sys.exit()  
        else:
            pQHFile = sys.argv[1]
        
            if(len(sys.argv)>2):
                iValueIndex = int(sys.argv[2])
            else:
                iValueIndex = 4

            if(len(sys.argv)>3):
                iGroupByIndex = int(sys.argv[3])
            else:
                iGroupByIndex = 0
        
            if(len(sys.argv) > 4):
                iTSIndex = int(sys.argv[4])
            else:
                iTSIndex = 7

            if(len(sys.argv)>5):
                iStats = int(sys.argv[5])
            else:
                iStats =  flooddsconfig.StatsType.Count + flooddsconfig.StatsType.Avg + flooddsconfig.StatsType.Max + flooddsconfig.StatsType.Min + flooddsconfig.StatsType.Sum + flooddsconfig.StatsType.Std 


            pOutFile = ""
            if(len(sys.argv)>6):
                pOutFile = sys.argv[6]

            if(pOutFile==""):
                (pOutFile, ext) = os.path.splitext(pQHFile)
                pOutFile = "{}_stats{}".format(pOutFile,ext) 
            
            lParentIDs = []

            #pParams = (pQHFile, pFilter, pOutFile, iQHType, 0)   
            pProcessor = ClassOp()
            pProcessor.DebugLevel = debugLevel
            pParams = (pQHFile, iValueIndex, iGroupByIndex, iTSIndex, iStats, lParentIDs, pOutFile)
            (sOK, pOutFile, sMsg) = pProcessor.execute(pParams)   #pQHFile, pOutFile, iValueIndex, iGroupByIndex, iStats) 
            arcpy.AddMessage("Completed, dt={}. \nSee results at {}.".format(apwrutils.Utils.GetDSMsg(ds), pOutFile))
            del pProcessor  
             
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at {}'.format(dt.strftime("%Y-%m-%d %H:%M:%S")))

