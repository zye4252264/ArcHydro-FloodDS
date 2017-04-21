'''***********************************************************************************************
Tool Name:  fdgettsvaluekisterurl (SourceName=fdgettsvaluekisterurl.py)
Version:  ArcGIS 10.0
Author:  zye 1/26/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
    (0) url (=http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz)
    (2) targetFolder
    (2) kisterConfig.txt  = store the datetime of last modified.
    (3) kisterFilter.txt = [ComID, minH) filter file for data extraction.
    (4) ds = interval to wait (sleep) before checking the url again.
Description: access kister url to download the Q/H file.
History:  Initial coding -  1/30/2017
Usage:  fdgettsvaluekisterurl.py url targetFolder KisterConfig FilterFile interval (=60s)
  url: url to check datetime/download data.
  short term: http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz
  mid term: https://nwm.kisters.de/nwm/current/medium_range/tx/nwm.medium_range.channel_rt.forecasts_per_section_vertical.csv.gz

  fdgettsvaluekisterurl.py http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz C:\10Data\TXDEM\KisterData kisterConfigST.txt "C:\10DATA\TXDEM\Address05TotPop.csv" 300  C:\10DATA\TXDEM\txdem.sde
***********************************************************************************************'''
import sys
import os
import datetime 
import time 
import requests 
import zipfile
import gzip 
import shutil
import urllib2
import arcpy
import apwrutils 

import flooddsconfig

import fdtsvalueextract
import fdtsvaluemax
import fdgetaddressh
import fdgroupbystats
import fdgroupbystatsTS
import fdtablebackup

# bat file:
# python fdgettsvaluekisterurl.py http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz C:\10Data\TXDEM\KisterData kisterConfigST.txt kisterFilter.txt 60
# from command line:  D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro>
# python fdgettsvaluekisterurl.py http://nwm.kisters.de/nwm/curren/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz kisterConfigST.txt kisterFilter.txt 60
#..download the kister's tsvalues - zye 9:30 PM 1/25/2017
#..https://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz  c:\temp
#..https://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section.csv.gz

C_OK = 'OK'
C_NOTOK = 'NOTOK'
K_Sep = "," 
sValueErr = 'ValueError: could not convert string to float: Count'
exprCalcHour = "getHour(!ForecastTime!,!TSTime!)"
codeblockGetHour = """def getHour(dt1, dt2):
  hrs = 0
  try: 
    ddt1 = datetime.datetime.strptime(dt1, "%m/%d/%Y %H:%M:%S %p")
    ddt2 = datetime.datetime.strptime(dt2, "%m/%d/%Y %H:%M:%S %p")
    c = ddt2 - ddt1
    ds = c.total_seconds()
    hrs = int(ds/3600)

  except:
    hrs = 1
  return hrs
"""

def trace():
    import traceback, inspect
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    # script name + line number
    line = tbinfo.split(", ")[1]
    filename = inspect.getfile(inspect.currentframe() )
    # Get Python syntax error
    #
    synerror = traceback.format_exc().splitlines()[-1]
    return line, filename, synerror

def str2bool(v):
    b = v.lower() in ("yes", "true", "t", "1")
    return b

def GetDSMsg(ds, format="%.3f s."):
    d = time.clock()
    dt = d - ds
    if(format==""):
        format = "%.3f s."
    
    return format % dt

def GetDateTimeString2(d):
        """ format a datetime to string """
        return (d.strftime("%Y%m%d%H%M%S"))

def makeDateTimeFromString(strDateTime, sFormat='%a, %d %b %Y %H:%M:%S'):
    """sDate = 'Wed, 25 Jan 2017 18:31:26' sFormat='%a, %d %b %Y %H:%M:%S' 
        sDate1 = 'Wed, 25 Jan 2017 18:31:26 GMT', sFormat='%a, %d %b %Y %H:%M:%S %Z'
    """
    if(sFormat==""):
        sFormat = "%Y-%m-%d %H:%M:%S"
    d = None
    try:
        d = datetime.datetime.strptime(strDateTime, sFormat)
    except:
        sFormat = '%a, %d %b %Y %H:%M:%S'
        try:
            d = datetime.datetime.strptime(strDateTime, sFormat)
        except:
            arcpy.AddMessage(trace())
            pass 

    return d 

# Derive from Request class and override get_method to allow a HEAD request.
class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"

def downloadurlfile(url):
    filename = os.path.basename(url) 
    localFileName = url.split('/')[-1]
    arcpy.AddMessage("filename={} lf={}".format(filename, localFileName))
    try:
        # NOTE the stream=True parameter
        r = requests.get(url, verify=False,stream=True)    #requests.get(url)    #requests.get(url, stream=True, verify=True)
        #r.raw.decode_content = True
        with open(localFileName, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
    except:
        arcpy.AddMessage(trace())           
    return localFileName

class ClassOp:
    DebugLevel = 0
    def __init__(self, url):
        self.url = url 

    def downloadURLFile(self, url):
        filename = os.path.basename(url) 
        localFileName = url.split('/')[-1]
        arcpy.AddMessage("filename={} lf={}".format(filename, localFileName))
        try:
            # NOTE the stream=True parameter
            r = requests.get(url, verify=False,stream=True)    #requests.get(url)    #requests.get(url, stream=True, verify=True)
            #r.raw.decode_content = True
            with open(localFileName, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024): 
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
        except:
            arcpy.AddMessage(trace())
                       
        return localFileName
            
    def checkHeader(self, url, lastDT):
        """ get the header, if the header is diff from lastDate passed in, return (sOK=C_OK, bCanLoad=True, d1=modifiedDate, sMsg="") 
            otherwise, bCanLoad=False, on Error, sOK=C_NotOK, bCanLoad=False, d1=lastDate, sMsg=ErrMsg)
        """
        sOK = C_OK
        bCanLoad = False 
        d1 = None
        sMsg = "" 
        try:
            request = HeadRequest(url)
            response = urllib2.urlopen(request)
            response_headers = response.info()
            d = response_headers.dict
            #sDate = ""
            #for i, k in enumerate(d):
            #    arcpy.AddMessage("{}. {}={}".format(i, k, d[k]))
            #arcpy.AddMessage("{}={}".format('date', d['date']))
            #arcpy.AddMessage("{}={}".format('last-modified', d['last-modified']))
            #arcpy.AddMessage("dt={}".format(GetDSMsg(ds)))
            sDate = d['last-modified']
            sFormat='%a, %d %b %Y %H:%M:%S %Z'
            d1 = makeDateTimeFromString(sDate, sFormat)
            if(lastDT==None):
                bCanLoad = True
            else:
                deltaT = d1 - lastDT
                if(deltaT.total_seconds()!=0):
                   bCanLoad = True 
        except:
            sOK = C_NOTOK
            sMsg = trace() 
        finally:
            return (sOK, bCanLoad, d1, sMsg) 

    def execute(self, url, configFile, targetFolder = None):
        """ url = url, configFile=file containing the datetime of last download, targetFolder=location to save the .csv 
            1. read the url header (modifieddate) to decide if download is needed.
            2. download the datafile (.gz)
            3. extract the downloaded .gz file and save it to .csv file = 'DT'+str(modifieddatetime).csv
            4. extract the contents based on the filter file provided and save the extracted file to 'DT'+str(modifieddatetime)_out.csv file.
            5. sleep for x(=60) s. and run the process again.
        """
        sFormat = '%a, %d %b %Y %H:%M:%S %Z'
        sFormatGDB = "%m/%d/%Y %H:%M:%S"
        sMsg = ""
        sOK = C_OK
        sFileName = ""
        dtNow = datetime.datetime.utcnow() 

        sFileName = ""
        sFooter = "ST"
        if("MT." in configFile): 
            sFooter = "MT"
        elif("LT." in configFile):
            sFooter = "LT"
        
        if(debugLevel!=0):
            arcpy.AddMessage("url={}\nconfigFile={}\nfileIdentifier={}".format(url, os.path.abspath(configFile), sFooter))
        sLastUpdated = ""
        
        try:
            if(targetFolder!=None):
                if(os.path.exists(targetFolder)==False):
                    try:
                        os.makedirs(targetFolder)
                    except:
                        targetFolder = r"c:\temp"
                        os.makedirs(targetFolder) 

            bExist = os.path.exists(configFile) 
            if(bExist==False):
                dt = datetime.datetime.utcnow()
                with open(configFile,'w') as f:
                    f.write(dt.strftime(sFormat))
            else:
                with open(configFile,'r') as f:
                    sDateTime = f.readline() 
                sDateTime = sDateTime.strip()
                if(sDateTime!=""):  
                    dt = makeDateTimeFromString(sDateTime, sFormat) 
                else:
                    bExist = False
                    dt = datetime.datetime.utcnow()
                    with open(configFile,'w') as f:
                        f.write(dt.strftime(sFormat))

            (sOK, bCanLoad, dt1, sMsg) = self.checkHeader(url, dt)
            dtMin = datetime.datetime.now()
            sDTMin = dtMin.strftime(sFormatGDB)
            if(sOK==C_OK):
                #sLastUpdated = dt1.strftime(sFormat)
                sLastUpdated = dt1.strftime(sFormatGDB)   #    "%m/%d/%Y %H:%M:%S")
                if(debugLevel!=0):  arcpy.AddMessage("LastUpdated={}".format(sLastUpdated))
                #downloadurlfile(url) 
                if(bCanLoad==True):
                    sLastUpdated = dt1.strftime(sFormatGDB)    #("%m/%d/%Y %H:%M:%S")
                    #sLastUpdated = dt1.strftime(sFormat)
                    #Save the date to configFile
                    dds = time.clock()
                    with open(configFile, 'w') as f:
                        f.write(dt1.strftime(sFormat))
                    localFileName = os.path.basename(url) 
                    sName = "{}_Data.csv".format(sFooter)      #MT_Data, ST_Data, LT_Data etc)
                    #sName = "{}{}.csv".format(sFooter, GetDateTimeString2(dt1))
                    sFileName = sName 
                    if(targetFolder!=None):
                        if not os.path.exists(targetFolder):
                            try:
                                os.makedirs(targetFolder)
                            except:
                                targetFolder = ""
                        if(targetFolder !=""):
                            sFileName = os.path.join(targetFolder, sName)
                    dds = time.clock()
                    requests.packages.urllib3.disable_warnings()
                    arcpy.AddMessage("Downloading file from {}".format(url))
                    r = requests.get(url, verify=False, stream=True)    #requests.get(url)    #requests.get(url, stream=True, verify=True)
                    arcpy.AddMessage("Completed downloading file.  dt={}".format(GetDSMsg(dds)))
                    dds = time.clock()
                    with open(localFileName, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024): 
                            if chunk: # filter out keep-alive new chunks
                                f.write(chunk)
                    #..Open the gz file and extract the file as save as .csv file. 
                    #sFileNameCSV = sFileName.replace('.gz', '.csv')
                    sMsg = "Saved downloadGZFile:\t{} dt={}".format(os.path.abspath(localFileName), GetDSMsg(dds))
                    arcpy.AddMessage(sMsg)
                    dds = time.clock()
                    ll = []
                    i = 0
                    with open(sFileName, 'w') as f_out:
                        with gzip.open(localFileName, 'rb') as f_in:
                            for line in f_in:
                                try:
                                    sLine = line.replace("\n","")
                                    values = sLine.split("\t") 
                                    if(i>0):
                                        s = values[2]
                                        dt = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%MZ")
                                        if(dt<dtMin):
                                            dtMin = dt 
                                        #values[2] = dt.strftime("%m/%d/%Y %H:%M:%S %p")
                                        #values[2] = dt.strftime("%m/%d/%Y %H:%M:%S")  
                                        values[2] = dt.strftime(sFormatGDB)   # "%m/%d/%Y %H:%M:%S") 
                                    s = ",".join(str(o) for o in values)
                                    f_out.write("{}\n".format(s))
                                except:
                                    ss = trace()
                                    print(ss) 
                                    pass
                                finally:
                                    i+=1

                    #with gzip.open(localFileName, 'rb') as f_in, open(sFileName, 'w') as f_out:
                    #    shutil.copyfileobj(f_in, f_out)
                    sMsg = "SaveGZFileTo:\t{} dt={}".format(sFileName, GetDSMsg(dds))
                    arcpy.AddMessage(sMsg)
                else:
                    sMsg = "No download is needed.\n{} does not have any updates.\nDateTime LastModified|[Now]={}|[{}](dt={}s)".format(url, str(dt), dtNow.strftime("%Y-%m-%d %H:%M:%S"),(dtNow-dt).total_seconds())
                    arcpy.AddMessage(sMsg)  
                    sOK = C_NOTOK 
            else:
                arcpy.AddMessage(sMsg)  
        except urllib2.HTTPError, e:
            sMsg = "Error code: {} {}".format(e.code, trace())
            arcpy.AddMessage(sMsg)
            sOK = C_NOTOK

        return (sOK, sFileName, sFooter, sLastUpdated, dtMin.strftime(sFormatGDB), sMsg)
        
class ClassOPR:
    DebugLevel = 0
    dTables = dict()

    def __init__(self, debugLevel):
        self.DebugLevel = debugLevel 

    def getSDETableName(self, dSDETableNames, sName):
        sReturn = sName
        try:
            sReturn = dSDETableNames[sName]
        except:
            pass
        return sReturn 

    def execute(self, pParamsR):
        (url, configFile, pAddressFile, targetFolder, pGDBOut, nMaxRepeatCalls, deltaT, pTargetGDB, pBackupGDB) = pParamsR 
        debugLevel = self.DebugLevel
        if(debugLevel!=0):
            #arcpy.AddMessage("arcpy.Exists({})={}".format(pGDBOut, arcpy.Exists(pGDBOut)))
            #arcpy.AddMessage("pEditor={}".format(arcpy.da.Editor(pGDBOut)))
            arcpy.AddMessage("pAddressFile={}".format(pAddressFile))
        dSDETableNames = apwrutils.Utils.getSDEBaseNameDict(pGDBOut) 
        sMsg = apwrutils.Utils.getcmdargs(pParamsR) 
        arcpy.AddMessage(sMsg) 
        nLoops = 1
        dsProcess = time.clock()
        nLoaded = 0
        nStatRecs = 0
        while (True):
            pEditor = None 
            try:
                dsProcess = time.clock()
                pDataLoader = ClassOp(url)
                pDataLoader.DebugLevel = debugLevel
                tReturns = pDataLoader.execute(url, configFile, targetFolder) 
                #tReturns=(C_OK, r"C:\10DATA\TXDEM\KisterData\MT_Data.csv", 'MT', '12/9/2016 6:00:00 AM')
                if(tReturns[0]==C_OK):
                    bOutGDB = arcpy.Exists(pGDBOut)
                    if(bOutGDB):
                        pEditor = arcpy.da.Editor(pGDBOut)
                        pEditor.startEditing(False,False)

                    nLoaded = nLoaded + 1 
                    pTSData = tReturns[1]
                    sFoot = tReturns[2]
                    sLastUpdated = tReturns[3]
                    sDTMin = tReturns[4]
                    modelID = 1
                    if(sFoot=='MT'):
                        modelID = 2
                    
                    arcpy.AddMessage("sFoot={}, modelID={}, ForecastStartTime:{}".format(sFoot, modelID, sDTMin)) 
                    #..CommentedOutBlockStarts  --- uncommented out for apply filter.               
                    #iQHType = fdtsvalueextract.QHType.H
                    #(pOutFile, ext) = os.path.splitext(pTSData)
                    #pOutFile = "{}_Out{}".format(pOutFile,ext) 
                    #pProcessor = fdtsvalueextract.FDTSValueExtractor()
                    #arcpy.AddMessage("Running {}.\n".format(pProcessor.thisFileName())) 
                    #pProcessor.DebugLevel = debugLevel
                    #(sOK, pOutFileTS, sMsg) = pProcessor.execute(pTSData, pFilter, pOutFile, iQHType) 
                    #del pProcessor
                    #..CommentedOutBlockEnds
                    #..CodePattern: 1. Construct pOutFileName, 2. create pProcessXXX, 3. collect pParams, 4. call pProcessorXXX.execute(pParams), 5. get the pOutFile, 6. use pOutFile as input for next step.
                    #..Apply Max for GroupBy ComID, CountyID, DistID, RegID etc
                    iQHType = flooddsconfig.QHType.H    #default to check only the H
                    pQHFile = pTSData
                    #..MAX file - groupby
                    pOutFileMax = ""
                    (pOutFileMax, ext) = os.path.splitext(pQHFile)
                    pOutFileMax = "{}_max{}".format(pOutFileMax,ext) 
                    pProcessorMax = fdtsvaluemax.ClassOp()
                    pProcessorMax.DebugLevel = debugLevel 
                    (sOK, pOutFileMax, sMsg) = pProcessorMax.execute(pQHFile, pOutFileMax, iQHType)                
                    del pProcessorMax 
                    #..Add AddH
                    pProcessorAddH = fdgetaddressh.ClassOp() 
                    pProcessorAddH.DebugLevel = debugLevel
                    pOutFileAddH = ""
                    (pOutFileAddH, ext) = os.path.splitext(pOutFileMax)
                    pOutFileAddH = "{}_AddH{}".format(pOutFileAddH,ext)                     
                    pParams = (pAddressFile, pOutFileMax, pOutFileAddH, iQHType) 
                    (sOK, pOutFileAddH, sMsg) = pProcessorAddH.execute(pParams)  #pAddressFile, pKisterFile, pOutFile, QHType.H )
                    del pProcessorAddH 
                    #..Apply Stats groupby IDs on pOutFileAddH.
                    (pOutFileT, ext) = os.path.splitext(pOutFileAddH) 
                    pOutFileComID = "{}_ComID{}".format(pOutFileT, ext) 
                    pOutFileCountyID = "{}_CountyID{}".format(pOutFileT, ext) 
                    pOutFileDistID = "{}_DistID{}".format(pOutFileT, ext) 
                    pOutFileRegID = "{}_RegID{}".format(pOutFileT, ext) 
                    lStatsOps = []
                    pIDs = [4,5,6]
                    pTbl = os.path.join(pGDBOut, self.getSDETableName(dSDETableNames, flooddsconfig.TB_ComIDImpactMax))

                    lFldNames = [flooddsconfig.FN_ModeID, flooddsconfig.FN_ForecastTime, flooddsconfig.FN_AddressCount, flooddsconfig.FN_TotPop10, flooddsconfig.FN_TOTHU10, flooddsconfig.FN_DistrictID, flooddsconfig.FN_RegionID]
                    pStatsOp = flooddsconfig.StatsOpFile(3, 0, 7, 17, pIDs, pOutFileComID, pTbl, pGDBOut) 
                    lStatsOps.append(pStatsOp)
                    pIDs = [5,6]           
                    pTbl = os.path.join(pGDBOut, self.getSDETableName(dSDETableNames, flooddsconfig.TB_CountyImpactMax))
                    pStatsOp = flooddsconfig.StatsOpFile(3, 4, 7, 17, pIDs, pOutFileCountyID, pTbl, pGDBOut) 
                    lStatsOps.append(pStatsOp)           
                    pIDs = [6]
                    pTbl = os.path.join(pGDBOut, self.getSDETableName(dSDETableNames, flooddsconfig.TB_DistIDImpactMax))
                    pStatsOp = flooddsconfig.StatsOpFile(3, 5, 7, 17, pIDs, pOutFileDistID, pTbl, pGDBOut) 
                    lStatsOps.append(pStatsOp)           
                    pTbl = os.path.join(pGDBOut, self.getSDETableName(dSDETableNames, flooddsconfig.TB_RegIDImpactMax) )
                    pIDs = []
                    pStatsOp = flooddsconfig.StatsOpFile(3, 6, 7, 17, pIDs, pOutFileRegID, pTbl, pGDBOut) 
                    lStatsOps.append(pStatsOp)        
                    for pStatsOp in lStatsOps:
                        pProcessor = fdgroupbystats.ClassOp()
                        pProcessor.DebugLevel = debugLevel
                        arcpy.AddMessage("pOutFileAddH={}".format(pOutFileAddH))
                        pParams = (pOutFileAddH, pStatsOp.ValueIndex, pStatsOp.GroupByIndex, pStatsOp.TSIndex, pStatsOp.Stats, pStatsOp.ParentIDs, pStatsOp.OutFile)    #, pStatsOp.OutTB, pStatsOp.Workspace)
                        (sOK, pOutFile, sMsg) = pProcessor.execute(pParams) 
                        arcpy.AddMessage("Completed, dt={}. \nSee results at {}.".format(apwrutils.Utils.GetDSMsg(ds), pOutFile))
                        del pProcessor 
                        nStatRecs = 0
                        if (bOutGDB==True) :
                            if(pStatsOp.OutTB.endswith(flooddsconfig.TB_CountyImpactMax)):
                                arcpy.AddMessage("  Writing MAX stats into {}, ModelID={}".format(pStatsOp.OutTB, modelID))
                                pTbl = "TblView"
                                if(arcpy.Exists(pTbl)): arcpy.Delete_management(pTbl)
                                sWhere = "{}={}".format(flooddsconfig.FN_ModeID, modelID)
                                arcpy.MakeTableView_management(pStatsOp.OutTB, pTbl, sWhere)
                                arcpy.DeleteRows_management(pTbl)
                                lFlds = [flooddsconfig.FN_ModeID, flooddsconfig.FN_ForecastTime, flooddsconfig.FN_AddressCount, flooddsconfig.FN_TotPop10, flooddsconfig.FN_TOTHU10, flooddsconfig.FN_CountyID, flooddsconfig.FN_DistrictID, flooddsconfig.FN_RegionID]
                                if(pStatsOp.TSIndex>0):
                                    lFlds.append(flooddsconfig.FN_TSTIME)    
                                with arcpy.da.InsertCursor(pStatsOp.OutTB, lFlds) as inRows:
                                    with open(pOutFile, 'r') as f:
                                        for sLine in f:    
                                            try:
                                                sLine = sLine.replace("\n","")
                                                lValues = sLine.split(K_Sep) 
                                                nHouse = 0
                                                try:
                                                    nHouse = float(lValues[2])/float(lValues[1])
                                                except:
                                                    nHouse = 0
                                                inRow = [modelID, sDTMin, float(lValues[1]), float(lValues[2]), nHouse, int(lValues[0]), int(lValues[3]), int(lValues[4])]
                                                if(pStatsOp.TSIndex>0):
                                                    try:
                                                        sTSTime = lValues[len(lValues)-1]
                                                        if(sTSTime !=""):
                                                            inRow.append(sTSTime) 
                                                    except:
                                                        pass 

                                                inRows.insertRow(inRow)
                                                nStatRecs = nStatRecs + 1   
                                            except:
                                                s = trace()
                                                if((sValueErr in s)==False):
                                                    arcpy.AddMessage(trace())

                                arcpy.CalculateField_management(pTbl, flooddsconfig.FN_FEATUREID, "!{}!".format(flooddsconfig.FN_CountyID), "PYTHON_9.3")  
                                arcpy.CalculateField_management(pStatsOp.OutTB, "FHour", exprCalcHour, "PYTHON_9.3", codeblockGetHour)
                                arcpy.AddMessage("  Completed writing MAX stats into {}, ModelID={}, nRecs = {}".format(pStatsOp.OutTB, modelID, nStatRecs))
                            elif(pStatsOp.OutTB.endswith(flooddsconfig.TB_DistIDImpactMax)):
                                arcpy.AddMessage("  Writing MAX stats into {}, ModelID={}".format(pStatsOp.OutTB, modelID))
                                pTbl = "TblView"
                                if(arcpy.Exists(pTbl)): arcpy.Delete_management(pTbl)
                                sWhere = "{}={}".format(flooddsconfig.FN_ModeID, modelID)
                                arcpy.MakeTableView_management(pStatsOp.OutTB, pTbl, sWhere)
                                arcpy.DeleteRows_management(pTbl)
                                lFlds = [flooddsconfig.FN_ModeID, flooddsconfig.FN_ForecastTime, flooddsconfig.FN_AddressCount, flooddsconfig.FN_TotPop10, flooddsconfig.FN_TOTHU10, flooddsconfig.FN_DistrictID, flooddsconfig.FN_RegionID]
                                if(pStatsOp.TSIndex>0):
                                    lFlds.append(flooddsconfig.FN_TSTIME)    
                                with arcpy.da.InsertCursor(pStatsOp.OutTB, lFlds) as inRows:
                                    with open(pOutFile, 'r') as f:
                                        for sLine in f:    
                                            try:
                                                sLine = sLine.replace("\n","")
                                                lValues = sLine.split(K_Sep) 
                                                nHouse = 0
                                                try:
                                                    nHouse = float(lValues[2])/float(lValues[1])
                                                except:
                                                    nHouse = 0
                                                inRow = [modelID, sDTMin, float(lValues[1]), float(lValues[2]), nHouse, int(lValues[0]), int(lValues[3])]
                                                if(pStatsOp.TSIndex>0):
                                                    try:
                                                        sTSTime = lValues[len(lValues)-1]
                                                        if(sTSTime !=""):
                                                            inRow.append(sTSTime) 
                                                    except:
                                                        pass
                                                inRows.insertRow(inRow)   
                                                nStatRecs = nStatRecs + 1   
                                            except:
                                                s = trace()
                                                if((sValueErr in s)==False):
                                                    arcpy.AddMessage(trace())

                                arcpy.CalculateField_management(pTbl, flooddsconfig.FN_FEATUREID, "!{}!".format(flooddsconfig.FN_DistrictID), "PYTHON_9.3")  
                                arcpy.CalculateField_management(pStatsOp.OutTB, "FHour", exprCalcHour, "PYTHON_9.3", codeblockGetHour)  
                                arcpy.AddMessage("  Completed writing MAX stats into {}, ModelID={}, nRecs = {}".format(pStatsOp.OutTB, modelID, nStatRecs))
                            elif(pStatsOp.OutTB.endswith(flooddsconfig.TB_RegIDImpactMax)):
                                arcpy.AddMessage("  Writing MAX stats into {}, ModelID={}".format(pStatsOp.OutTB, modelID))
                                pTbl = "TblView"
                                if(arcpy.Exists(pTbl)): arcpy.Delete_management(pTbl)
                                sWhere = "{}={}".format(flooddsconfig.FN_ModeID, modelID)
                                arcpy.MakeTableView_management(pStatsOp.OutTB, pTbl, sWhere)
                                arcpy.DeleteRows_management(pTbl)
                                lFlds = [flooddsconfig.FN_ModeID, flooddsconfig.FN_ForecastTime, flooddsconfig.FN_AddressCount, flooddsconfig.FN_TotPop10, flooddsconfig.FN_TOTHU10, flooddsconfig.FN_RegionID]
                                if(pStatsOp.TSIndex>0):
                                    lFlds.append(flooddsconfig.FN_TSTIME)    
                                with arcpy.da.InsertCursor(pStatsOp.OutTB, lFlds) as inRows:
                                    with open(pOutFile, 'r') as f:
                                        for sLine in f:    
                                            try:
                                                sLine = sLine.replace("\n","")
                                                lValues = sLine.split(K_Sep) 
                                                nHouse = 0
                                                try:
                                                    nHouse = float(lValues[2])/float(lValues[1])
                                                except:
                                                    nHouse = 0
                                                #inRow = (modelID, sLastUpdated, float(lValues[1]), float(lValues[2]), nHouse, int(lValues[0]))
                                                inRow = [modelID, sDTMin, float(lValues[1]), float(lValues[2]), nHouse, int(lValues[0])]
                                                if(pStatsOp.TSIndex>0):
                                                    try:
                                                        sTSTime = lValues[len(lValues)-1]
                                                        if(sTSTime !=""):
                                                            inRow.append(sTSTime) 
                                                    except:
                                                        pass 
                                                inRows.insertRow(inRow)   
                                                nStatRecs = nStatRecs + 1   
                                            except:
                                                s = trace()
                                                if((sValueErr in s)==False):
                                                    arcpy.AddMessage(trace())

                                arcpy.CalculateField_management(pTbl, flooddsconfig.FN_FEATUREID, "!{}!".format(flooddsconfig.FN_RegionID), "PYTHON_9.3")    
                                arcpy.CalculateField_management(pStatsOp.OutTB, "FHour", exprCalcHour, "PYTHON_9.3", codeblockGetHour)  
                                arcpy.AddMessage("  Completed writing MAX stats into {}, ModelID={}, nRecs = {}".format(pStatsOp.OutTB, modelID, nStatRecs))
               
                    #..Processing the TS stats (groupby comid,countyid,distid,regid and forecasttime)
                    #..NoMaxFile -- Groupby ComID and time
                    pQHFile = pTSData
                    #..Add AddH
                    if((self.DebugLevel & 1)==1): arcpy.AddMessage("pQFile={}".format(pQHFile))
                    pProcessorAddH = fdgetaddressh.ClassOp() 
                    pProcessorAddH.DebugLevel = debugLevel
                    pOutFileAddH = ""
                    (pOutFileAddH, ext) = os.path.splitext(pQHFile)
                    pOutFileAddH = "{}_AddH{}".format(pOutFileAddH,ext) 
                    pParams = (pAddressFile, pQHFile, pOutFileAddH, iQHType) 
                    (sOK, pOutFileAddH, sMsg) = pProcessorAddH.execute(pParams)  #pAddressFile, pKisterFile, pOutFile, QHType.H ) 
                
                    (pOutFileT, ext) = os.path.splitext(pOutFileAddH) 
                    pOutFileComID = "{}_ComID{}".format(pOutFileT, ext) 
                    pOutFileCountyID = "{}_CountyID_TS{}".format(pOutFileT, ext) 
                    pOutFileDistID = "{}_DistID_TS{}".format(pOutFileT, ext) 
                    pOutFileRegID = "{}_RegID_TS{}".format(pOutFileT, ext) 
                    lStatsOps = []
                    pIDs = [4,5,6]
                    pTbl = os.path.join(pGDBOut, self.getSDETableName(dSDETableNames, flooddsconfig.TB_ComIDImpact))
                    pStatsOp = flooddsconfig.StatsOpFile(3, 0, 7, 17, pIDs, pOutFileComID, pTbl, pGDBOut) 
                    lStatsOps.append(pStatsOp)
                    pIDs = [5,6]  
                    pTbl = os.path.join(pGDBOut, self.getSDETableName(dSDETableNames, flooddsconfig.TB_CountyImpact))
                    pStatsOp = flooddsconfig.StatsOpFile(3, 4, 7, 17, pIDs, pOutFileCountyID, pTbl, pGDBOut) 
                    lStatsOps.append(pStatsOp)           
                    pIDs = [6]
                    pTbl = os.path.join(pGDBOut, self.getSDETableName(dSDETableNames, flooddsconfig.TB_DistIDImpact))                         
                    pStatsOp = flooddsconfig.StatsOpFile(3, 5, 7, 17, pIDs, pOutFileDistID, pTbl, pGDBOut) 
                    lStatsOps.append(pStatsOp)           
                    pIDs = []
                    pTbl = os.path.join(pGDBOut, self.getSDETableName(dSDETableNames, flooddsconfig.TB_RegIDImpact))
                    pStatsOp = flooddsconfig.StatsOpFile(3, 6, 7, 17, pIDs, pOutFileRegID, pTbl, pGDBOut) 
                    lStatsOps.append(pStatsOp)           
                    for pStatsOp in lStatsOps:
                        pProcessor = fdgroupbystatsTS.ClassOp()
                        pProcessor.DebugLevel = debugLevel
                        pParams = (pOutFileAddH, pStatsOp.ValueIndex, pStatsOp.GroupByIndex, pStatsOp.TSIndex, pStatsOp.Stats, pStatsOp.ParentIDs, pStatsOp.OutFile)
                        (sOK, pOutFile, sMsg) = pProcessor.execute(pParams) 
                        arcpy.AddMessage("Completed, dt={}. \nSee results at {}.".format(apwrutils.Utils.GetDSMsg(dsProcess), pOutFile))
                        del pProcessor
                        nStatRecs = 0
                        if(bOutGDB==True):
                            if(pStatsOp.OutTB.endswith(flooddsconfig.TB_CountyImpact)):
                                pTbl = "TblView"
                                if(arcpy.Exists(pTbl)): arcpy.Delete_management(pTbl)
                                arcpy.AddMessage(pStatsOp.OutTB)
                                sWhere = "{}={}".format(flooddsconfig.FN_ModeID, modelID)
                                arcpy.MakeTableView_management(pStatsOp.OutTB, pTbl, sWhere)
                                arcpy.DeleteRows_management(pTbl)
                                arcpy.AddMessage("  Writing TS stats into {}".format(pStatsOp.OutTB))
                                with arcpy.da.InsertCursor(pStatsOp.OutTB, [flooddsconfig.FN_ModeID, flooddsconfig.FN_TSTIME, flooddsconfig.FN_ForecastTime, flooddsconfig.FN_AddressCount, flooddsconfig.FN_TotPop10, flooddsconfig.FN_TOTHU10, flooddsconfig.FN_CountyID, flooddsconfig.FN_DistrictID, flooddsconfig.FN_RegionID]) as inRows:
                                    with open(pOutFile, 'r') as f:
                                        for sLine in f:    
                                            try:
                                                sLine = sLine.replace("\n","")
                                                lValues = sLine.split(K_Sep) 
                                                nHouse = 0
                                                try:
                                                    nHouse = float(lValues[3])/float(lValues[2])
                                                except:
                                                    nHouse = 0
                                                #inRow = (modelID, lValues[1], sLastUpdated, float(lValues[2]), float(lValues[3]), nHouse, int(lValues[0]), int(lValues[4]), int(lValues[5]))
                                                inRow = (modelID, lValues[1], sDTMin, float(lValues[2]), float(lValues[3]), nHouse, int(lValues[0]), int(lValues[4]), int(lValues[5]))
                                                inRows.insertRow(inRow)  
                                                nStatRecs = nStatRecs + 1    
                                            except:
                                                s = trace()
                                                if((sValueErr in s)==False):
                                                    arcpy.AddMessage(trace())

                                arcpy.CalculateField_management(pStatsOp.OutTB, flooddsconfig.FN_FEATUREID, "!{}!".format(flooddsconfig.FN_CountyID), "PYTHON_9.3")
                                arcpy.CalculateField_management(pStatsOp.OutTB, "FHour", exprCalcHour, "PYTHON_9.3", codeblockGetHour)  
                                arcpy.AddMessage("  Completed writing TS stats into {}, ModelID={}, nRecs = {}".format(pStatsOp.OutTB, modelID, nStatRecs))
                            elif(pStatsOp.OutTB.endswith(flooddsconfig.TB_DistIDImpact)):
                                pTbl = "TblView"
                                if(arcpy.Exists(pTbl)): arcpy.Delete_management(pTbl)
                                arcpy.AddMessage(pStatsOp.OutTB)
                                sWhere = "{}={}".format(flooddsconfig.FN_ModeID, modelID)
                                arcpy.MakeTableView_management(pStatsOp.OutTB, pTbl, sWhere)
                                arcpy.DeleteRows_management(pTbl)
                                arcpy.AddMessage("  Writing TS stats into {}, ModelID={}".format(pStatsOp.OutTB, modelID))
                                with arcpy.da.InsertCursor(pStatsOp.OutTB, [flooddsconfig.FN_ModeID, flooddsconfig.FN_TSTIME, flooddsconfig.FN_ForecastTime, flooddsconfig.FN_AddressCount, flooddsconfig.FN_TotPop10, flooddsconfig.FN_TOTHU10, flooddsconfig.FN_DistrictID, flooddsconfig.FN_RegionID]) as inRows:
                                    with open(pOutFile, 'r') as f:
                                        for sLine in f:    
                                            try:
                                                sLine = sLine.replace("\n","")
                                                lValues = sLine.split(K_Sep) 
                                                nHouse = 0
                                                try:
                                                    nHouse = float(lValues[3])/float(lValues[2])
                                                except:
                                                    nHouse = 0
                                                inRow = (modelID, lValues[1], sDTMin, float(lValues[2]), float(lValues[3]), nHouse, int(lValues[0]), int(lValues[4]))
                                                inRows.insertRow(inRow) 
                                                nStatRecs = nStatRecs + 1     
                                            except:
                                                s = trace()
                                                if((sValueErr in s)==False):
                                                    arcpy.AddMessage(trace())

                                arcpy.CalculateField_management(pStatsOp.OutTB, flooddsconfig.FN_FEATUREID, "!{}!".format(flooddsconfig.FN_DistrictID), "PYTHON_9.3")
                                arcpy.CalculateField_management(pStatsOp.OutTB, "FHour", exprCalcHour, "PYTHON_9.3", codeblockGetHour)
                                arcpy.AddMessage("  Completed writing TS stats into {}, ModelID={}, nRecs = {}".format(pStatsOp.OutTB, modelID, nStatRecs))
                            elif(pStatsOp.OutTB.endswith(flooddsconfig.TB_RegIDImpact)):
                                pTbl = "TblView"
                                if(arcpy.Exists(pTbl)): arcpy.Delete_management(pTbl)
                                arcpy.AddMessage(pStatsOp.OutTB)
                                sWhere = "{}={}".format(flooddsconfig.FN_ModeID, modelID)
                                arcpy.MakeTableView_management(pStatsOp.OutTB, pTbl, sWhere)
                                arcpy.DeleteRows_management(pTbl)
                                arcpy.AddMessage("  Writing TS stats into {}, ModelID={}".format(pStatsOp.OutTB, modelID))
                                with arcpy.da.InsertCursor(pStatsOp.OutTB, [flooddsconfig.FN_ModeID, flooddsconfig.FN_TSTIME, flooddsconfig.FN_ForecastTime, flooddsconfig.FN_AddressCount, flooddsconfig.FN_TotPop10, flooddsconfig.FN_TOTHU10, flooddsconfig.FN_RegionID]) as inRows:
                                    with open(pOutFile, 'r') as f:
                                        for sLine in f:    
                                            try:
                                                sLine = sLine.replace("\n","")
                                                lValues = sLine.split(K_Sep) 
                                                nHouse = 0
                                                try:
                                                    nHouse = float(lValues[3])/float(lValues[2])
                                                except:
                                                    nHouse = 0
                                                inRow = (modelID, lValues[1], sDTMin, float(lValues[2]), float(lValues[3]), nHouse, int(lValues[0]))
                                                inRows.insertRow(inRow) 
                                                nStatRecs = nStatRecs + 1     
                                            except:
                                                s = trace()
                                                if((sValueErr in s)==False):
                                                    arcpy.AddMessage(trace())

                                arcpy.CalculateField_management(pStatsOp.OutTB, flooddsconfig.FN_FEATUREID, "!{}!".format(flooddsconfig.FN_RegionID), "PYTHON_9.3")
                                arcpy.CalculateField_management(pStatsOp.OutTB, "FHour", exprCalcHour, "PYTHON_9.3", codeblockGetHour)
                                arcpy.AddMessage("  Completed writing TS stats into {}, ModelID={}, nRecs = {}".format(pStatsOp.OutTB, modelID, nStatRecs))

                    #..Updating/backup the 6 tables:
                    if(pTargetGDB!=None):
                        try:
                            arcpy.AddMessage("Updating 6 tables on {}".format(pTargetGDB))
                            lTables = [flooddsconfig.TB_CountyImpact,flooddsconfig.TB_CountyImpactMax, flooddsconfig.TB_DistIDImpact, flooddsconfig.TB_DistIDImpactMax, flooddsconfig.TB_RegIDImpact, flooddsconfig.TB_RegIDImpactMax]
                            pClassOp = fdtablebackup.ClassOp()
                            pUpdateParams = (pGDBOut, pTargetGDB, pBackupGDB, lTables)
                            pClassOp.execute(pUpdateParams) 
                            del lTables 

                        except:
                            pass

                    arcpy.AddMessage("({}) {} time(s) new data downloaded and processed in {}. {}".format(nLoops, nLoaded, apwrutils.Utils.GetDSMsg(dsProcess,""), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))  
                del pDataLoader
            except:
                arcpy.AddMessage(trace())
            finally:
                try:
                    if (pEditor!=None) and (pEditor.isEditing):
                        pEditor.stopEditing(True)
                except:
                    pass 
        
            nLoops = nLoops + 1
            if(nLoops >=nMaxRepeatCalls):
                break
            time.sleep(deltaT)


if(__name__=='__main__'):
    ds = time.clock()
    bOutGDB = False 
    debugLevel = 1
    #pAddressFile = r"D:\10Data\TXDEM\KisterData\Address05TotPop.csv"
    sMsg = apwrutils.Utils.getcmdargs(sys.argv)
    arcpy.AddMessage(sMsg)
    url = 'https://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section.csv.gz'          #h
    if(len(sys.argv)>1):
        url = sys.argv[1]
    else:
        url = 'http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz'  #v
    if(len(sys.argv)>2):
        targetFolder = sys.argv[2]
    else:
        targetFolder = r"C:\10Data\TXDEM\KisterData"
    
    if(len(sys.argv)>3):
        configFile = sys.argv[3]
    else:
        configFile = "kisterConfigST.txt"    #"KisterConfigMT.txt" and "KisterConfigLT.txt"
    
    arcpy.AddMessage("ConfigFile = {}".format(configFile))
    
    if(len(sys.argv) > 4):
        pFilter = sys.argv[4]
    else:
        pFilter = "Address05TotPop.csv"

        #..trying to get deltaT (in secondes).    
    deltaT = 0     # in seconds (interval between the calls)
    if(len(sys.argv) > 5):
        try:
            deltaT = int(sys.argv[5]) 
        except:
            deltaT = 0
   
    if(deltaT >= 60):
        nMaxRepeatCalls = 14400
    else:
        nMaxRepeatCalls = 1

    if(debugLevel>0): arcpy.AddMessage("deltaT={} {}".format(deltaT, nMaxRepeatCalls))
    if(len(sys.argv)>6):
        pGDBOut = sys.argv[6]
    else:
        pGDBOut = r"C:\10DATA\TXDEM\KisterData\TXStats.gdb"

    pTargetGDB = None 
    if(len(sys.argv) > 7):
        pTargetGDB = sys.argv[7]

    pBackupGDB = None
    if(len(sys.argv) > 8):
        pBackupGDB = sys.argv[8]
         
    #if(debugLevel>0):
    #    arcpy.AddMessage("arcpy.Exists({})={}".format(pGDBOut, arcpy.Exists(pGDBOut)))
    #    arcpy.AddMessage("pEditor={}".format(arcpy.da.Editor(pGDBOut)))

    pParamsR = (url, configFile, pFilter, targetFolder, pGDBOut, nMaxRepeatCalls, deltaT, pTargetGDB, pBackupGDB)  
    pRunner = ClassOPR(debugLevel) 
    pRunner.execute(pParamsR) 



        