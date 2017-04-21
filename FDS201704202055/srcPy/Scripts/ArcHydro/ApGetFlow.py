'''***********************************************************************************************
Tool Name:  ApGetFlow (SourceName=ApGetFlow.py)
Version:  ArcGIS 10.0
Author:  zye 3/1/2015 (Environmental Systems Research Institute Inc.)
ConfigFile: AHPyConfig.xml located in the same place as source .py file. 
Required Arguments:
    (0) sMsg = arcpy.GetParameterAsText(0)
          
Description: Create ApUniqueID FC in a given workspace (and optionally, populated with some records dRecs = {"HYDROID": 1, "MYHYDROID": 2}
  FC is used (instead of Table) to support the publishing of the function as a GP service.
History:  Initial coding -  3/1/2015
Usage:  ApGetFlow.py 
        pLayer = arcpy.GetParameterAsText(0) 
        tsTableName = arcpy.GetParameterAsText(1) 
        serviceType = arcpy.GetParameterAsText(2)    #="National Model 10 Days" or "National Model 15 Hours" 
        bMultipleValues = arcpy.GetParameterAsText(3) 
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import urllib2
import urllib
import json 

import arcpy
import apwrutils


FN_COMID_DB = "COMID"
FN_COMID = 'egdb.DBO.LargeScale.station_id'
FN_streamOrder= 'egdb.DBO.LargeScale.streamOrder'
FN_GNIS_NAME = 'egdb.DBO.LargeScale.GNIS_NAME'

#FN_timevalue = 'egdb.dbo.short_term_current.timevalue'   #'egdb.dbo.medium_term_current.timevalue'
#FN_qout = 'egdb.dbo.short_term_current.qout'              #'egdb.dbo.medium_term_current.qout'
#FN_flowrate = 'egdb.dbo.short_term_current.flowrate'
#FN_qdiff = 'egdb.dbo.short_term_current.qdiff'
#FN_anomaly = 'egdb.dbo.short_term_current.anomaly'
#http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Medium/MapServer/4/query?where=egdb.DBO.LargeScale.station_id+%3D+25732014&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=flowrate&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson
FN_timevalue = 'egdb.dbo.medium_term_current.timevalue'   #'egdb.dbo.medium_term_current.timevalue'
FN_qout = 'egdb.dbo.medium_term_current.qout'              #'egdb.dbo.medium_term_current.qout'
FN_flowrate = 'egdb.dbo.medium_term_current.flowrate'
FN_qdiff = 'egdb.dbo.medium_term_current.qdiff'
FN_anomaly = 'egdb.dbo.medium_term_current.anomaly'

#egdb.DBO.LargeScale.OBJECTID: 44774
#egdb.DBO.LargeScale.station_id: 25732014
#egdb.DBO.LargeScale.streamOrder: 10
#egdb.DBO.LargeScale.GNIS_NAME: Mississippi River
#egdb.dbo.medium_term_current.timevalue: 1476619200000
#egdb.dbo.medium_term_current.qout: 471075.820674
#egdb.dbo.medium_term_current.flowrate: 5
#egdb.dbo.medium_term_current.qdiff: 458623.737674
#egdb.dbo.medium_term_current.anomaly: 5

#C_URL = 'http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Medium/MapServer/4/query?'    #'http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Medium/MapServer/4/query?'    #where=egdb.DBO.LargeScale.station_id+%3D+8832652+&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=flowrate%2C+station_id%2C+qout&returnGeometry=true&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=html
#C_URL_2 = 'http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Short/MapServer/4'
C_URL10Day = 'http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Medium/MapServer/4/query'
C_URL15Hrs = 'http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Short/MapServer/4/query'
#C_URL_10Day: http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Short/MapServer/4/query?where=egdb.DBO.LargeScale.station_id%3D25732014&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=flowrate&returnGeometry=false&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=html
C_Medium = 'NationalWaterModel_Medium'
#C_RULEnd = 'returnGeometry=false&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson'
C_URLEnd = '&text=&objectIds=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=*&returnGeometry=false&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&f=pjson'

#1. egdb.DBO.LargeScale.streamOrder->7/n
#2. egdb.DBO.LargeScale.GNIS_NAME->Cape Fear River/n
#3. egdb.dbo.short_term_current.qdiff->223664.897617/n
#4. egdb.DBO.LargeScale.station_id->8832652/n
#5. egdb.DBO.LargeScale.OBJECTID->397259/n
#6. egdb.dbo.short_term_current.flowrate->4/n
#7. egdb.dbo.short_term_current.qout->229671.464617/n
#8. egdb.dbo.short_term_current.timevalue->1476262800000/n
#9. egdb.dbo.short_term_current.anomaly->5'

#sURL = "http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Short/MapServer/4/query?where=egdb.DBO.LargeScale.station_id+%3D+8832652+&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=flowrate%2C+station_id%2C+qout&returnGeometry=false&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson"
#sURL = "http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Short/MapServer/4/query?where=egdb.DBO.LargeScale.station_id+%3D+8832652+&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=flowrate%2C+station_id%2C+qout&returnGeometry=false&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson"


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

""" Making the ApUniqueID table """
class ApGetFlow:
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
    
    """ GetFlow(self, comid, tstime) """
    def execute(self, pLayer, tsTableName, url, bMultipleValues = True ):
        sOK = apwrutils.C_OK
        pLogMgr = None 
        #sTBName = "TimeSeries"
        pTableView = "{}View".format(tsTableName)
        FN_TSTIME2 = "TSTIME2"
        dFldsAdd = {FN_TSTIME2: "DATE"}
        ds = time.clock()
        dtBase = datetime.datetime.now()
        detaHr = 1
        iVID = 0
        try:
            if(C_Medium in url):
                iVID = 1
                deltaHr = 3
                dtBase = datetime.datetime(dtBase.year, dtBase.month, dtBase.day, 0, 0, 0) 
                dtBase = dtBase + datetime.timedelta(hours=-1)                       # 10days forecast always starts at 2:00AM of a day.                
                FN_timevalue = 'egdb.dbo.medium_term_current.timevalue'    #'egdb.dbo.medium_term_current.timevalue'
                FN_qout = 'egdb.dbo.medium_term_current.qout'              #'egdb.dbo.medium_term_current.qout'
                FN_flowrate = 'egdb.dbo.medium_term_current.flowrate'
                FN_qdiff = 'egdb.dbo.medium_term_current.qdiff'
                FN_anomaly = 'egdb.dbo.medium_term_current.anomaly'
                nMaxStep = 80
                nMod = 1
            else:
                iVID = 2
                deltaHr=1
                dtBase = datetime.datetime.now()
                dtBase = datetime.datetime(dtBase.year, dtBase.month, dtBase.day, dtBase.hour, 0, 0) 
                FN_timevalue = 'egdb.dbo.short_term_current.timevalue'   #'egdb.dbo.medium_term_current.timevalue'
                FN_qout = 'egdb.dbo.short_term_current.qout'              #'egdb.dbo.medium_term_current.qout'
                FN_flowrate = 'egdb.dbo.short_term_current.flowrate'
                FN_qdiff = 'egdb.dbo.short_term_current.qdiff'
                FN_anomaly = 'egdb.dbo.short_term_current.anomaly'
                nMaxStep = 15
                nMod = 1

            if(self.DebugLevel > 0):
                pLogMgr = apwrutils.LogMgr()
                arcpy.AddMessage("before calling log")
                pLogMgr.openLogFileAtTempLocation()
                arcpy.AddMessage("logfile location:{}".format(pLogMgr.logFileName))

            pWorkspace = apwrutils.Utils.getWorkspace(pLayer)             
            arcpy.env.Workspace = pWorkspace
            pTBTimeSeries = apwrutils.Utils.createTimeSeriesTable(pWorkspace, tsTableName, dFldsAdd)
           
            arcpy.MakeTableView_management(pTBTimeSeries, pTableView)
            nCnt = int(arcpy.GetCount_management(pLayer)[0])
            if nCnt > 100:
                nMod = int(nCnt/99)
            else:                                             
                nMod = 1
            iCnt = 0
            iiTotal = 0
            ds = time.clock()
            ds1 = time.clock()
            nMod = 1
            if(bMultipleValues):
                if (nMaxStep>100):
                    nMod = int(nMaxStep/99)
                else:
                    nMod = 1
                            
                arcpy.SetProgressor('step', 'Download flow Q values {}'.format(url), 0, nMaxStep, nMod)      
                arcpy.SetProgressorPosition(0)
                arcpy.AddMessage("URL={}".format(url))
                sComIDs = ""
                sURL = ""
                iCnt = 0
                with arcpy.da.InsertCursor(pTBTimeSeries, [apwrutils.FN_FEATUREID,apwrutils.FN_VARID,apwrutils.FN_TSTIME,apwrutils.FN_TSVALUE, FN_TSTIME2]) as inRows:
                    for i in range(1, nMaxStep+1):
                        try:
                            #if(arcpy.env.isCancelled==True):
                            #    break
                            ddt = dtBase + datetime.timedelta(hours=i*deltaHr)
                            dthour = datetime.datetime(ddt.year, ddt.month, ddt.day, ddt.hour, 0, 0)
                            dtms =  int(time.mktime(dthour.timetuple()) * 1000)
                            if(sComIDs==""):
                                iCnt = 0
                                with arcpy.da.SearchCursor(pLayer, [FN_COMID_DB]) as rows:
                                    for row in rows:
                                        iCnt = iCnt + 1
                                        if(sComIDs ==""):
                                            sComIDs = "{}".format(row[0])
                                        else:
                                            sComIDs = "{},{}".format(sComIDs, row[0])
                                    if(sComIDs!=""):
                                        arcpy.AddMessage(sComIDs) 
                                        sComIDs = "({})".format(sComIDs)

                            if(sComIDs!=""):
                                sURL = "{}?where={} in {}&time={}&resultRecordCount={}{}".format(url,FN_COMID, sComIDs, dtms, 30, C_URLEnd)
                                pLogMgr.logInfo(sURL)
                                #if(i % nMod)==0:
                                #quoted_url = urllib.quote(sURL)
                                #req = urllib2.Request(quoted_url,)
                                #req.add_header('User-Agent', urllib2.User_Agent)
                                #response = urllib2.urlopen(sURL).read()
                                #ojson = json.loads(response) 
                                try:
                                    dds = time.clock()
                                    sWhere = "{} in {}".format(FN_COMID, sComIDs)   
                                    #http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Short/MapServer/4/query?where=egdb.DBO.LargeScale.station_id+%3D+8832652+&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=flowrate%2C+station_id%2C+qout&returnGeometry=false&returnTrueCurves=false&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&resultOffset=&resultRecordCount=&f=pjson
                                    #arcpy.AddMessage(sMsg) 
                                    #sURL = "http://livefeeds2.arcgis.com/arcgis/rest/services/NFIE/NationalWaterModel_Medium/MapServer/4/query"
                                    sData = {'where' : sWhere, 
                                                'text' : '',
                                                'objectIds' : '',
                                                'time': dtms,   #1476824400000,   # dtms,    #1476824400000,
                                                'geometry' : False,
                                                'geometryType':'',
                                                'esriGeometryEnvelope': '',
                                                'inSR': '',
                                                'spatialRel' : 'esriSpatialRelIntersects',
                                                'relationParam' : '',
                                                'outFields' : '*',
                                                'returnGeometry' : False,
                                                'returnTrueCurves' : False,
                                                'maxAllowableOffset' : '',
                                                'geometryPrecision' : '',
                                                'outSR' : '',
                                                'returnIdsOnly' : False,
                                                'returnCountOnly' : False,
                                                'orderByFields' : '',
                                                'groupByFieldsForStatistics' : '',
                                                'outStatistics' : '',
                                                'returnZ' : False,
                                                'returnM' : False, 
                                                'gdbVersion' : '',
                                                'returnDistinctValues' : False,
                                                'resultOffset' : '',
                                                'resultRecordCount': iCnt,   #   '1000',
                                                'f' : 'pjson'
                                                }

                                    pData = urllib.urlencode(sData)
                                    cReq = urllib2.Request(url, pData) # Post request
                                    response = urllib2.urlopen(cReq)
                                    pageData = response.read()
                                    pageData = pageData.replace('\n','') 
                                    pageData = pageData.replace(' ','')
                                    if(pageData.startswith("{")==False):  
                                        pageData = "{" + pageData        
                                    oJson = json.loads(pageData)          
                                    
                                    features = oJson['features']
                                    nHasData = len(features)
                                    sDT = dthour.strftime("%Y-%m-%d %H:%M:%S") 
                                    sMsg1 = "Step {} of {}. {} {} of {} stations has data. ddt={}".format(i, nMaxStep, sDT, nHasData, nCnt,apwrutils.Utils.GetDSMsg(dds))
                                    arcpy.AddMessage(sMsg1)  
                                    for feature in features:
                                        try:
                                            iiTotal = iiTotal + 1
                                            #s = "{} attributes".format(len(feature['attributes']))
                                            #i = 0
                                            #for a in feature['attributes']:
                                            #    i = i + 1
                                            #    s = "{}/n{}. {}->{}".format(s, i, a, feature['attributes'][a])
                                            #arcpy.AddMessage(s)
                                            n = feature['attributes'][FN_GNIS_NAME]
                                            t = feature['attributes'][FN_timevalue]
                                            q = feature['attributes'][FN_qout]
                                            comID = feature['attributes'][FN_COMID]
                                            ddtWeb = datetime.datetime.fromtimestamp(t/1000.0)
                                            sDTWeb = ddtWeb.strftime("%Y-%m-%d %H:%M:%S") 
                                        
                                            inRow = [comID, iVID, sDTWeb, q, sDT]
                                            inRows.insertRow(inRow)                                          
                                            sMsg1 = "{},ComID={},TSTime={},TimeMS={},Q={},TS:{}of{}".format(n, comID, sDT, t, q, i, nMaxStep)
                                            arcpy.AddMessage(sMsg1)
                                        except:
                                            pass

                                except:
                                    arcpy.AddMessage("sURL={}, err:{}".format(sURL, trace()))
                        except:
                            arcpy.AddMessage("sURL={}, err:{}".format(sURL, trace()))
                        finally:
                            if((i==1) or (i % nMod)==0):
                                sMsg = "Process {} of {} timesteps with {} recs downloaded. dt={}".format(i,nMaxStep,iiTotal, apwrutils.Utils.GetDSMsg(ds1))
                                arcpy.SetProgressorLabel(sMsg)
                                arcpy.SetProgressorPosition(i)
                                ds1 = time.clock()


            else:
                arcpy.SetProgressor('step', 'Download flow Q values {}'.format(url), 0, nCnt, nMod)      
                arcpy.SetProgressorPosition(0)
                arcpy.AddMessage("URL={}".format(url))
                with arcpy.da.InsertCursor(pTBTimeSeries, [apwrutils.FN_FEATUREID,apwrutils.FN_VARID,apwrutils.FN_TSTIME,apwrutils.FN_TSVALUE, FN_TSTIME2]) as inRows:
                    with arcpy.da.SearchCursor(pLayer, [FN_COMID_DB]) as rows:
                        for row in rows:
                            iCnt = iCnt + 1
                            try:
                                comID = row[0]
                                for i in range(1, nMaxStep+1):
                                    try:
                                        #if(arcpy.env.isCancelled==True):
                                        #    break
                                        ddt = dtBase + datetime.timedelta(hours=i*deltaHr)
                                        dthour = datetime.datetime(ddt.year, ddt.month, ddt.day, ddt.hour, 0, 0)
                                        dtms =  str(int(time.mktime(dthour.timetuple()) * 1000)) 
                                        sURL = "{}?where={}={}&time={}&resultRecordCount={}{}".format(url,FN_COMID, comID, dtms,1,C_URLEnd)
                                        if(pLogMgr):
                                            pLogMgr.logInfo(sURL)

                                        #if(i % nMod)==0:
                                        response = urllib2.urlopen(sURL).read()
                                        ojson = json.loads(response) 
                                        features = ojson['features']
                                        for feature in features:
                                            iiTotal = iiTotal + 1
                                            #s = "{} attributes".format(len(feature['attributes']))
                                            #i = 0
                                            #for a in feature['attributes']:
                                            #    i = i + 1
                                            #    s = "{}/n{}. {}->{}".format(s, i, a, feature['attributes'][a])
                                            #arcpy.AddMessage(s)
                                            n = feature['attributes'][FN_GNIS_NAME]
                                            t = feature['attributes'][FN_timevalue]
                                            q = feature['attributes'][FN_qout]
                                            ddtWeb = datetime.datetime.fromtimestamp(t/1000.0)
                                            sDTWeb = ddtWeb.strftime("%Y-%m-%d %H:%M:%S") 
                                            sDT = dthour.strftime("%Y-%m-%d %H:%M:%S") 
                                            inRow = [comID, iVID, sDTWeb, q, sDT]
                                            inRows.insertRow(inRow) 
                                         
                                            sMsg1 = "{},ComID={},TSTime={},TimeMS={},Q={}".format(n, comID, sDT, t, q)
                                            arcpy.AddMessage(sMsg1)
                                    except:
                                        pass 
                                        #arcpy.AddMessage(trace())
                            
                            except:
                                pass 

                            finally:
                                if((iCnt==1) or (iCnt % nMod)==0):
                                    sMsg = "Process " + str(iCnt) + " of " + str(nCnt) + " features. " + str(iiTotal) + " recs downloaded. dt=" + apwrutils.Utils.GetDSMsg(ds1)
                                    arcpy.SetProgressorLabel(sMsg)
                                    arcpy.SetProgressorPosition(iCnt)
                                    ds1 = time.clock()
            sMsg = "Process {} of {} features, {} timesteps with {} recs downloaded. dt={}".format(iCnt, nCnt, nMaxStep, iiTotal, apwrutils.Utils.GetDSMsg(ds))
            arcpy.SetProgressorLabel(sMsg)
            arcpy.SetProgressorPosition(iCnt)
            arcpy.AddMessage(sMsg) 
            dt = datetime.datetime.now()
            s = 'Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S")
            arcpy.AddMessage(s)

            try:
                if(pLogMgr):
                    pLogMgr.logInfo(sMsg) 
                    pLogMgr.logInfo(s)
                    s = "A logfile is saved at {}".format(pLogMgr.logFileName) 
                    arcpy.AddMessage(s) 
         
            except:
                pass
            finally:
                if(pLogMgr!=None):
                    del pLogMgr          
        except:
            sOK = trace()
            arcpy.AddError(sOK)
            sOK = apwrutils.C_NOTOK

        return (sOK, pTableView)
            
if __name__ == '__main__':
    #oProcessor = None
    try:
        debugLevel = 1
        pLayer = arcpy.GetParameterAsText(0)
        tsTableName = arcpy.GetParameterAsText(1)
        serviceType = arcpy.GetParameterAsText(2)    #="National Model 10 Days" or "National Model 15 Hours" 
        bMultipleValues = arcpy.GetParameterAsText(3) 
        arcpy.AddMessage("bMultipleValues={}".format(bMultipleValues))

        if tsTableName == '#' or not tsTableName:
           tsTableName = "TimeSeries"
        
        if(serviceType=="National Model 10 Days"):
            url = C_URL10Day
        else:
            url = C_URL15Hrs

        if(bMultipleValues=='#' or not bMultipleValues):
            bMultipleValues = False  
        else:
            try:
                bMultipleValues = apwrutils.Utils.str2Bool(bMultipleValues)
            except:
                bMultipleValues = False 
      
        arcpy.AddMessage("bMultipleValues={}".format(bMultipleValues))
        ddt = time.clock()
        oProcessor = ApGetFlow()
        oProcessor.DebugLevel = debugLevel
        tReturns = oProcessor.execute(pLayer, tsTableName, url, bMultipleValues)       
        if(tReturns[0] == apwrutils.C_OK): 
            pTblView = tReturns[1]
            arcpy.SetParameterAsText(4, pTblView) 
         
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        if(oProcessor!=None):
            del oProcessor
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

