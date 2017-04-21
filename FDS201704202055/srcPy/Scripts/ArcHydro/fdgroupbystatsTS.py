'''***********************************************************************************************
Tool Name:  fdgroupbystatsTS (SourceName=fdgroupbystatsTS.py)
Version:  ArcGIS 10.3
Author:  zye 3/1/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
  0 pQHFile=downloaded ts file [COMDID, Date, Q, H]
  1 iValueIndex=index of the column holding the values to apply statistics to
  2 iGroupByIndex=index of the column to group by   [COMID]   (default 0)
  3 iTSFieldIndex=index of the column to group by   [ForecastTime] = 3 for DownloadedData applying filter of address, 2 for downloaded file.
  4 lParentIDs = list of column indexes holding the parent entities  2:59 PM 3/9/2017
  5 iStats = 1,2,4,8,16,32 (1=Count,2=Avg,4=Max,8=Min,16=Sum,32=Std) and combination of these values: ..3,5,7 etc.
  6 pOutFile (optional) = Output file for extracted values ComID,Date, Q, H

Description: For each comid, ForecastTime find stats of h (or q).
History:  Initial coding -  2/27/2017
Usage:  fdgroupbystatsTS.py C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 4 0 63
#  python fdgroupbystatsTS.py C:\10DATA\TXDEM\KisterData\KisterDataMT_AddH.csv 4 0 63
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
    
    """ execute(self, pParams=(pQHFile, iValueIndex, iGroupByIndex, iDTFieldIndex, iStats, lParentIDs, pOutFile) """
    def execute(self, pParams):    #pQHFile, pOutFile, iValueIndex, iGroupByIndex, iStats):
        """ pQHFile=downloaded ts file [COMDID, Date, Q, H]
            iValueIndex=index of the column holding the values to apply statistics to
            iGroupByIndex=index of the column to group by
            iDTFieldIndex=index of the column to group dt by
            iStats = 1,2,4,8,16,32 (1=Count,2=Avg,4=Max,8=Min,16=Sum,32=Std) and combination of these values: ..3,5,7 etc.
            lParentIDs= list of column indexes of parent ids - id's of entities containing the groupby entity.
            pOutFile = Output file for extracted values ComID,Date, Q, H
            
        """
        #r"D:\ProjectsUtils\HydroProjects\ApUtilityTools\Scripts\ApUtilityTools\nwm.short_range.channel_rt.forecasts_per_section_vertical.csv"
        sMsg = ""
        sOK = apwrutils.C_OK 
        ds = time.clock() 
        try:
            (pQHFile, iValueIndex, iGroupByIndex, iDTFieldIndex, iStats, lParentIDs, pOutFile) = pParams 
            if((self.DebugLevel & 1) == 1):
                sMsg = apwrutils.Utils.getcmdargs(pParams) 
                arcpy.AddMessage(sMsg)   
            bHasParentID = len(lParentIDs) > 0
            sPIDValues = ""
            l = []
            ComIDLast = ""
            valueMax = -999999.0
            lValuesMax = []
            dds = time.clock()
            #Calculate stats as it goes.
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
            if((self.DebugLevel & 1) == 1):
                sMsg = "Constructing group by values..."
                arcpy.AddMessage(sMsg)
            sHeader = ""
            sHeaderP = ""
            lHeaders = []
            sGroupByFieldName = ""
            try:
                sHeader = l[0]
                sHeader = sHeader.replace("\n", "")
                sArr = sHeader.split(K_Sep)
                sGroupByFieldName = sArr[iGroupByIndex] 
                sHeader = "{},{}".format(sArr[iGroupByIndex], sArr[iDTFieldIndex])
                if(len(lParentIDs)>0):
                    for pid in lParentIDs:
                        if(sHeaderP==""):
                            sHeaderP = sArr[pid]
                        else:
                            sHeaderP = "{},{}".format(sHeaderP, sArr[pid])

            except:
                sMsg = trace()
                arcpy.AddMessage(sMsg)
                pass

            if((iStats & flooddsconfig.StatsType.Count)==flooddsconfig.StatsType.Count): sHeader = "{},{}".format(sHeader, "Count")
            if((iStats & flooddsconfig.StatsType.Avg)==flooddsconfig.StatsType.Avg): sHeader = "{},{}".format(sHeader, "Avg")
            if((iStats & flooddsconfig.StatsType.Max)==flooddsconfig.StatsType.Max): sHeader = "{},{}".format(sHeader, "Max")
            if((iStats & flooddsconfig.StatsType.Min)==flooddsconfig.StatsType.Min): sHeader = "{},{}".format(sHeader, "Min")
            if((iStats & flooddsconfig.StatsType.Sum)==flooddsconfig.StatsType.Sum): sHeader = "{},{}".format(sHeader, "Sum")
            if((iStats & flooddsconfig.StatsType.Std)==flooddsconfig.StatsType.Std): sHeader = "{},{}".format(sHeader, "Std")
            if(sHeaderP<>""): sHeader = "{},{}".format(sHeader, sHeaderP) 
            lSort = []
            dds = time.clock()
            if((self.DebugLevel & 1) == 1):
                sMsg = "Collecting {} recs.".format(nCnt)
                arcpy.AddMessage(sMsg) 
            for i, s in enumerate(l):
                try:
                    s = s.replace('\n','')
                    sArr = s.split(K_Sep) 
                    d = -9999
                    try:
                        d = float(sArr[iValueIndex])
                        sArr[iValueIndex] = d
                        lSort.append(sArr) 
                    except:
                        pass
                        #sMsg = trace()
                        #arcpy.AddMessage(sMsg)
                except:
                    sMsg = "2. {}".format(trace())
                    arcpy.AddMessage(sMsg)
                finally:
                    if((self.DebugLevel & 1)==1):
                        if(i % nMod)==0:
                            sMsg = "  processing {} of {} recs with {} values added. ddt={}".format(i+1, nCnt, len(lSort), apwrutils.Utils.GetDSMsg(dds))
                            arcpy.AddMessage(sMsg)
            nCnt = len(lSort)
            if((self.DebugLevel & 1)==1):
                sMsg = "Completed collecting {} recs. dt={}".format(nCnt, apwrutils.Utils.GetDSMsg(dds))
                arcpy.AddMessage(sMsg) 
                dds = time.clock()

            lSort.sort(key=lambda x: x[iGroupByIndex])
            nCnt = len(lSort)
            if((self.DebugLevel & 1)==1):
                sMsg = "Completed sorting {} recs on {}. Sorted recs={}.  dt={}".format(nCnt, sGroupByFieldName, nCnt, apwrutils.Utils.GetDSMsg(dds))
                arcpy.AddMessage(sMsg) 
            nMod = nCnt/20
            if(nMod<1):
                nMod=1 
            dds = time.clock()
            
            iGroupByCnt = 1    #..1st GroupBy (COMID, RegionID etc), 2nd GroupBy DateTime
            if((self.DebugLevel & 1)==1):
                sMsg = "Calculating statistics of dataset of {} recs.".format(nCnt)
                arcpy.AddMessage(sMsg) 
            sPIDValues = ""
            with open(pOutFile,'w') as fout:
                fout.write("{}\n".format(sHeader))
                sGroupByLast = ""
                sDT = ""
                for i, sArr in enumerate(lSort):
                    try:
                        sGroupBy = sArr[iGroupByIndex]
                        d = -9999
                        try:
                            d = float(sArr[iValueIndex])
                        except:
                            arcpy.AddMessage(trace())
                        if(d!=-9999):
                            if(sGroupByLast==""):
                                sGroupByLast = sGroupBy
                                if((sPIDValues=="") and (bHasParentID)):
                                    for pid in lParentIDs:
                                        if(sPIDValues)=="":
                                            sPIDValues = sArr[pid]
                                        else:
                                            sPIDValues = "{},{}".format(sPIDValues, sArr[pid])
                                
                            if(sGroupBy==sGroupByLast):
                                sDT = sArr[iDTFieldIndex]
                                              
                                if(sDT==sGroupBy):
                                    arcpy.AddMessage("sDT==sGroupBy {}".format(sGroupBy))
                                if(sDT in dDataset):
                                    l = dDataset[sDT]
                                    l.append(d) 
                                else:
                                    l = []
                                    l.append(d)
                                    dDataset.setdefault(sDT, l)
                            else:
                                #..Apply stats:
                                for ii, sKey in enumerate(dDataset):
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
                                            sout = "{},{},{}".format(sGroupByLast, sKey, sout)
                                            if(bHasParentID):
                                                sout = "{},{}".format(sout, sPIDValues)
                                            #for debugging  (sKey==ForecastDate, sGroupByID (ComID, RegID, DistID etc)
                                            if(sGroupByLast!=sKey):
                                                fout.write("{}\n".format(sout))
                                            else:
                                                pass
                                                #arcpy.AddMessage("{}:{} e.q. value".format(sGroupByLast, sKey))
                                        except:
                                            sMsg = trace()
                                            arcpy.AddMessage(sMsg)
                                    except:
                                        sMsg = trace()
                                        arcpy.AddMessage(sMsg)
                                    finally:
                                        pass
                                #..Restart another groupBy dDataset, l etc.
                                sPIDValues=""
                                iGroupByCnt = iGroupByCnt + 1
                                sGroupByLast = sGroupBy
                                dDataset = dict()     
                                l = []
                                l.append(d)
                                dDataset.setdefault(sGroupBy, l) 
                                if((sPIDValues=="") and (bHasParentID)):
                                    for pid in lParentIDs:
                                        if(sPIDValues)=="":
                                            sPIDValues = sArr[pid]
                                        else:
                                            sPIDValues = "{},{}".format(sPIDValues, sArr[pid])

                                  
                        #*****************
                        if((self.DebugLevel & 1)==1):            
                            if(i % nMod)==0:
                                sMsg = "  processing {} of {} recs with {} distinct group values found. ddt={}".format(i+1, nCnt, iGroupByCnt, apwrutils.Utils.GetDSMsg(dds))
                                arcpy.AddMessage(sMsg)
                    except:
                        sMsg = trace()
                        arcpy.AddMessage(sMsg)
                if((self.DebugLevel & 1)==1):            
                    sMsg = "Completed calculating statistics of {} recs on {} group by values.  dt={}".format(nCnt, iGroupByCnt, apwrutils.Utils.GetDSMsg(ds))
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
    try:
        iValueIndex = flooddsconfig.QHType.H    #default to check only the H
        iGroupByIndex = 0
        iStats =  flooddsconfig.StatsType.Count + flooddsconfig.StatsType.Avg + flooddsconfig.StatsType.Max + flooddsconfig.StatsType.Min + flooddsconfig.StatsType.Sum + flooddsconfig.StatsType.Std 
        lParentIDs = []
        debugLevel = 0
        if(len(sys.argv)<2):
            arcpy.AddMessage("Usage: {} {} {}".format(sys.argv[0], "ComIDHQFile", "OutFile (Optional)"))
            sys.exit(0)
        pQHFile = sys.argv[1]
        if(len(sys.argv)>2):
            iValueIndex = int(sys.argv[2])
        else:
            iValueIndex = 4

        if(len(sys.argv)>3):
            iGroupByIndex = int(sys.argv[3])
        else:
            iGroupByIndex = 0
        
        if(len(sys.argv)>4):
            iDTFieldIndex = int(sys.argv[4])
        else:
            iDTFieldIndex = 3


        if(len(sys.argv)>5):
            iStats = int(sys.argv[5])
        else:
            iStats =  flooddsconfig.StatsType.Count + flooddsconfig.StatsType.Avg + flooddsconfig.StatsType.Max + flooddsconfig.StatsType.Min + flooddsconfig.StatsType.Sum + flooddsconfig.StatsType.Std 

        pOutFile = ""
        if(len(sys.argv)>6):
            pOutFile = sys.argv[6]
        if(pOutFile==""):
            (pOutFile, ext) = os.path.splitext(pQHFile)
            pOutFile = "{}_statsTS{}".format(pOutFile,ext) 
         
        #pParams = (pQHFile, pFilter, pOutFile, iQHType, 0)   
        pProcessor = ClassOp()
        pProcessor.DebugLevel = debugLevel
        pParams = (pQHFile, iValueIndex, iGroupByIndex, iDTFieldIndex, iStats, lParentIDs, pOutFile)
        (sOK, pOutFile, sMsg) = pProcessor.execute(pParams)   #pQHFile, pOutFile, iValueIndex, iGroupByIndex, iStats) 
        
        arcpy.AddMessage("See results at {}.".format(pOutFile))
        del pProcessor        
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at {}'.format(dt.strftime("%Y-%m-%d %H:%M:%S")))

