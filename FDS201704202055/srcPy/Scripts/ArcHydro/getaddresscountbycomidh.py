'''***********************************************************************************************
Tool Name:  GetAddressCountByComIDH (SourceName=GetAddressCountByComIDH.py)
Version:  ArcGIS 10.0
Author:  zye 3/1/2015 (Environmental Systems Research Institute Inc.)
ConfigFile: AHPyConfig.xml located in the same place as source .py file. 
Required Arguments:
     pFL = arcpy.GetParameterAsText(0)
     pTblTS = arcpy.GetParameterAsText(1)
     pTblTSSum = arcpy.GetParameterAsText(2) 
          
Description: Create ApUniqueID FC in a given workspace (and optionally, populated with some records dRecs = {"HYDROID": 1, "MYHYDROID": 2}
  FC is used (instead of Table) to support the publishing of the function as a GP service.
History:  Initial coding -  3/1/2015
Usage:  GetAddressCountByComIDH.py pFLAddress, pTSTbl, pTSTblSum
  The codes expects 
  1. field HAND_cm of long type existed and populated in the pFLAddress  [CalculateField TxAddrPt_254Counties_HAND_Comid HAND_cm int( !HAND__m!*100) PYTHON_9.3]
  2. field H_CM of long type exiested  and populated in the pTSTbl   [arcpy.CalculateField_management(in_table="tsshort1hq", field="H_CM", expression="int( !H!*100)"]
***********************************************************************************************'''
import sys
import os
import time 
import datetime

import arcpy
import apwrutils


FN_ADDRCNT = "ADDRCNT"

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
class GetAddressCountByComIDH:
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
    
    """ createApUniqueIDFC(self, pFLAddress, pTSTbl, pTSTblSum) """
    def execute(self, pParams):
        sOK = apwrutils.C_OK 
        (pFLAddress, pTSTbl, pTSTblSum) = pParams 
        pEditor = None
        pTableView = ""
        try:
            pWorkspace = apwrutils.Utils.getWorkspace(pTSTbl)
            oDesc = arcpy.Describe(pTSTbl) 
            sName = oDesc.name
            sQT = ""
            lFlds = arcpy.ListFields(pTSTbl, apwrutils.FN_FEATUREID)
            if(len(lFlds)==0):
                arcpy.AddError("required field {} does not exist.".format(apwrutils.FN_FEATUREID))
                sOK = apwrutils.C_NOTOK
                return (sOK, )
            pFld = lFlds[0]
            sType = pFld.type
            if(sType == 'String' or sType=='Date'):
                sQT = "'"
            ds = time.clock()
            if(pTSTblSum==""): pTSTblSum = os.path.join(pWorkspace, "{}_sum".format(sName))
            if(arcpy.Exists(pTSTblSum)==False):
                pTSTblSum = os.path.join(pWorkspace, "{}_sum".format(sName))
                arcpy.Statistics_analysis(in_table=pTSTbl, out_table=pTSTblSum, statistics_fields="FeatureID COUNT", case_field="FeatureID")
                arcpy.AddMessage("Create/pouplate {} table".format(pTSTblSum, apwrutils.Utils.GetDSMsg(ds)))

            sTblWithCnt = "{}_WithCnt".format(sName)
            pTblWithCnt = os.path.join(pWorkspace, sTblWithCnt)
            pTableView = sTblWithCnt                       
            ds = time.clock()
            if(arcpy.Exists(pTblWithCnt)):  
                arcpy.Delete_management(pTblWithCnt)
                arcpy.AddMessage("Deleting {}.  dt={}".format(pTblWithCnt, apwrutils.Utils.GetDSMsg(ds)))
                 
            arcpy.CreateTable_management(pWorkspace, sTblWithCnt)
            if(sQT=="'"):
                arcpy.AddField_management(pTblWithCnt, apwrutils.FN_FEATUREID, "TEXT","","",30)
            else: 
                arcpy.AddField_management(pTblWithCnt, apwrutils.FN_FEATUREID, "LONG")

            arcpy.AddField_management(pTblWithCnt, "H_CM", "LONG")
            arcpy.AddField_management(pTblWithCnt, FN_ADDRCNT,"LONG")
            arcpy.AddMessage("Creating {}.  dt={}".format(pTblWithCnt, apwrutils.Utils.GetDSMsg(ds)))

            nCnt = int(arcpy.GetCount_management(pTSTblSum)[0])
            nMod = 1
            if (nCnt>100):
                nMod = int(nCnt/99)
            ds1 = time.clock()                
            nAdded = 0
            arcpy.SetProgressor('step', 'Processing 0 of {} records.'.format(nCnt), 0, nCnt, nMod)      
            arcpy.SetProgressorPosition(0)
            dHCnt = {}
            pEditor = arcpy.da.Editor(pWorkspace)
            pEditor.startEditing(False,False)
            #sIDs = ""

            with arcpy.da.InsertCursor(pTblWithCnt, [apwrutils.FN_FEATUREID, "H_CM", FN_ADDRCNT]) as inRows:
                with arcpy.da.SearchCursor(pTSTblSum, [apwrutils.FN_FEATUREID]) as rows:
                    for i, row in enumerate(rows):
                        if(i % nMod)==0:
                            nn = arcpy.GetCount_management(pTblWithCnt)[0]
                            sMsg = "Process {} of {} features. {} recs added to {}. dt={} ".format(i+1, nCnt, nn, pTblWithCnt, apwrutils.Utils.GetDSMsg(ds1))
                            arcpy.SetProgressorLabel(sMsg)
                            arcpy.AddMessage(sMsg) 
                            arcpy.SetProgressorPosition(i+1)
                            ds1 = time.clock()

                        sFeatureID = row[0]
                        sWhere = "{} = {}{}{} and {} >=0 ".format(apwrutils.FN_FEATUREID, sQT, sFeatureID, sQT, "H_CM")
                        tblView = "tbl{}".format(sFeatureID)
                        if(arcpy.Exists(tblView)): arcpy.Delete_management(tblView)
                        arcpy.MakeTableView_management(pTSTbl, tblView, sWhere)
                        dHCnt = dict()
                        with arcpy.da.UpdateCursor(tblView, ["H_CM", FN_ADDRCNT]) as upRows:
                            for upRow in upRows:
                                intH = upRow[0]
                                try:
                                    if(intH in dHCnt)==False:
                                        nAddCnt = 0
                                        try:
                                            sWhereTS = "{} = {} and {} <= {}".format("STATION_ID", sFeatureID, "HAND_cm", intH)
                                            thmName = "thm{}".format(intH) 
                                            if(arcpy.Exists(thmName)): arcpy.Delete_management(thmName)
                                            arcpy.MakeFeatureLayer_management(pFLAddress, thmName, sWhereTS)
                                            nAddCnt = int(arcpy.GetCount_management(thmName)[0])
                                            pRowCnt = (sFeatureID, intH, nAddCnt)
                                            arcpy.AddMessage("sWhereTS: {} nCnt: {}".format(sWhereTS, pRowCnt))
                                            dHCnt.setdefault(intH, nAddCnt) 
                                            #if(sIDs==""):
                                            #    sIDs = sFeatureID
                                            #else:
                                            #    sIDs = "{},{}".format(sIDs, sFeatureID)
                                            if(nAddCnt>0):
                                                nAdded = nAdded + 1 
                                                #arcpy.AddMessage("Added={} nThisCnt={}".format(nAdded, nAddCnt))
                                                #arcpy.AddMessage(sIDs)
                                                inRows.insertRow(pRowCnt)
                                                upRow[1] = nAddCnt
                                                upRows.updateRow(upRow)
                                                arcpy.Delete_management(thmName)
                                                arcpy.AddMessage("Added={} nThisCnt={}".format(nAdded, nAddCnt))
                                        except:
                                            sMsg = "{} {}".format(arcpy.GetMessages(2), trace())
                                            arcpy.AddMessage(sMsg)
                                        finally:
                                            dHCnt.setdefault(intH, nAddCnt) 
                                            
                                    else:
                                        nAddCnt = dHCnt[intH]
                                        if(nAddCnt>0):
                                            upRow[1] = nAddCnt
                                            upRows.updateRow(upRow)
                                except:
                                    pass

            arcpy.MakeTableView_management(pTblWithCnt, pTableView)
        except:
            sMsg = "{} {}".format(arcpy.GetMessages(2), trace())
            arcpy.AddError(sMsg)
            sOK = apwrutils.C_NOTOK
        finally:
            if(pEditor!=None):
                pEditor.stopEditing(True)

        return (sOK, pTableView) 
            
if __name__ == '__main__':
    #oProcessor = None
    try:
        debugLevel = 0
        pFL = arcpy.GetParameterAsText(0)
        pTblTS = arcpy.GetParameterAsText(1)
        pTblTSSum = arcpy.GetParameterAsText(2) 
        if pTblTSSum == '#' or not pTblTSSum:
           pTblSum = ""

        ddt = time.clock()
        oProcessor = GetAddressCountByComIDH()
        oProcessor.DebugLevel = debugLevel
        pParams = (pFL, pTblTS, pTblTSSum) 
        tReturns = oProcessor.execute(pParams)       
        if(tReturns[0] == apwrutils.C_OK): 
            pTableView = tReturns[1]
            arcpy.SetParameterAsText(3, pTableView) 
         
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        if(oProcessor!=None):
            del oProcessor
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

