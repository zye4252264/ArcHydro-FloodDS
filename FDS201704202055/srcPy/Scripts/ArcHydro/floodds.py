import sys 
import os 
import time 
import datetime
import arcpy
import apwrutils
import flooddsconfig

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

class ApFloodDS:
    #variables:
    #C_OK = 'OK'
    #C_NOTOK = 'NOTOK'
    C_WLFld = 'WL_'
    FN_Elev = "Elev"

    def __init__(self):
        self.DebugLevel = 0
   
    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())
    # Load the configuration xml.
    def LoadConfigXML(self, sFileName):
        if(sFileName.find(os.sep) < 0):
            sXmlFile = sys.path[0] + os.sep + sFileName
        doc = xml.dom.minidom.parse(sXmlFile) 
        try:
            oNode = doc.getElementsByTagName("DebugLevel")[0]
            if(oNode!=None):
                self.DebugLevel=int(oNode.firstChild.nodeValue)
        except:
            self.DebugLevel=0

        del doc

    #def execute(self, parameters, messages):
    def execute(self, runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch, sOpType = flooddsconfig.WLOpType.pDeltaH):
    #def doWork(self, runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch):
        sOK = apwrutils.C_OK
        pEditor = None
        sCurDir = apwrutils.Utils.getcwd()  # os.getcwd()
        runName = runName.strip()
        #outRWKS = os.path.join(outRWKS, inStep)
        if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage(sCurDir)
        outRWKS = os.path.join(sCurDir, runName)
        apwrutils.Utils.makeSureDirExists(outRWKS)
        arcpy.AddMessage("Rasterworkspace {} is created".format(outRWKS))
        sWKSName = "{}.gdb".format(flooddsconfig.GDB_NAME)  # + ".gdb"
        sFWKSFullPath = os.path.join(outRWKS, sWKSName) 
        arcpy.AddMessage(sFWKSFullPath)
        #sFWKSFullPath = os.path.join(sCurDir, sWKSName)
        try:
            if(arcpy.Exists(sFWKSFullPath)==False):
                arcpy.CreateFileGDB_management(outRWKS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                arcpy.AddMessage("FWKS: {} is created.".format(sFWKSFullPath))
            else:
                arcpy.Delete_management(sFWKSFullPath)
                arcpy.AddMessage("FWKS: {} is deleted.".format(sFWKSFullPath))  
                arcpy.CreateFileGDB_management(outRWKS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                arcpy.AddMessage("FWKS: {} is created.".format(sFWKSFullPath))            

            #..make a copy of inStream and inPoints.
            inStreamName = os.path.basename(inStream)
            inPointsName = os.path.basename(inPoints)

            #..Create log table 
            dLogFPFields = {flooddsconfig.FN_ParamName: "TEXT", flooddsconfig.FN_ParamDesc: "TEXT"}
            arcpy.CreateTable_management(sFWKSFullPath, flooddsconfig.TB_LogTable)
            pLogTable = os.path.join(sFWKSFullPath, flooddsconfig.TB_LogTable) 
            apwrutils.Utils.addFields(pLogTable, dLogFPFields)
            lLogFPFields = [flooddsconfig.FN_ParamName, flooddsconfig.FN_ParamDesc]

            outStreamName = flooddsconfig.LN_FP_RIVER       # inStreamName   #  runName + flooddsconfig.C_UL + inStreamName
            outPointsName = flooddsconfig.LN_FP_WATERPOINT   # inPoints       #  runName + flooddsconfig.C_UL + inPoints
            outCatName = flooddsconfig.LN_FP_CATCHMENT      # inCatchment
            inStreamCopy = os.path.join(sFWKSFullPath, outStreamName)
            inPointsCopy = os.path.join(sFWKSFullPath, outPointsName)
            inCatchmentCopy = os.path.join(sFWKSFullPath, outCatName) 
            arcpy.CopyFeatures_management(inStream, inStreamCopy)
            arcpy.CopyFeatures_management(inPoints, inPointsCopy)
            arcpy.CopyFeatures_management(inCatchment, inCatchmentCopy)

            #..save the in/out locations:
            with arcpy.da.InsertCursor(pLogTable, lLogFPFields) as inRows:
                inRows.insertRow((flooddsconfig.FN_DateCreated, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))        
                inRows.insertRow((flooddsconfig.LN_FP_RIVER, "{}->{}".format(apwrutils.Utils.getLayerFullName(inStream), inStreamCopy)))
                inRows.insertRow((flooddsconfig.LN_FP_WATERPOINT,"{}->{}".format(apwrutils.Utils.getLayerFullName(inPoints), inPointsCopy)))
                inRows.insertRow((flooddsconfig.LN_FP_CATCHMENT, "{}->{}".format(apwrutils.Utils.getLayerFullName(inCatchment), inCatchmentCopy)))
                    
            #..add fields to the inPointsCopy
            dFieldsH = dict()      #..holdes field names: key:H_[index], value:[fieldtype:double]
            dFieldsHV = dict()     #..holds dH field values key:H_[index], value:[fieldvalues 1, 2, 5.5,10...] ft etc
            lFieldsH = []          #..keep the field order so that the fields are added in the order of H_1,H_2 etc.
            for i,h in enumerate(lDHs):
                fld = self.C_WLFld + str(i)
                lFieldsH.append(fld)
                dFieldsH.setdefault(fld,"DOUBLE")
                dFieldsHV.setdefault(fld, h)
            apwrutils.Utils.addFields(inPointsCopy, dFieldsH)
            pWorkspace = apwrutils.Utils.getWorkspace(inPointsCopy)

            #..Create H table
            #  HIndex HValue
            pHTable = os.path.join(pWorkspace, flooddsconfig.TB_HTable)
            arcpy.CreateTable_management(pWorkspace, flooddsconfig.TB_HTable)
            dFields = {flooddsconfig.FN_HIndex :'LONG', flooddsconfig.FN_HValue :'DOUBLE', flooddsconfig.FN_HCode: 'TEXT' }
         
            apwrutils.Utils.addFields(pHTable, dFields)
            lHFields = [flooddsconfig.FN_HIndex, flooddsconfig.FN_HValue, flooddsconfig.FN_HCode]

            pEditor = arcpy.da.Editor(pWorkspace)
            pEditor.startEditing(False,False)

            #..Populate the HTable
            with arcpy.da.InsertCursor(pHTable, lHFields) as inRows:
                for i,h in enumerate(lDHs):
                    inRow = [i,h,"W{}".format(h)]
                    inRows.insertRow(inRow)

            lFieldsH.append(self.FN_Elev)
            iFldElev = lFieldsH.index(self.FN_Elev)
            with arcpy.da.UpdateCursor(inPointsCopy, lFieldsH) as uprows:
                for uprow in uprows:
                    try:
                        dElev = float(uprow[iFldElev])
                        for fld in lFieldsH:
                            if(fld!=self.FN_Elev):
                                i = lFieldsH.index(fld)
                                uprow[i] = dElev + float(dFieldsHV[fld])
                        uprows.updateRow(uprow)
                    except:
                        arcpy.AddMessage(trace())
            
            
            if(arcpy.Exists(flooddsconfig.LN_FP_RIVER)): arcpy.Delete_management(flooddsconfig.LN_FP_RIVER)              #"inStream")
            if(arcpy.Exists(flooddsconfig.LN_FP_WATERPOINT)): arcpy.Delete_management(flooddsconfig.LN_FP_WATERPOINT)    #"inPoints")
            if(arcpy.Exists(flooddsconfig.LN_FP_CATCHMENT)): arcpy.Delete_management(flooddsconfig.LN_FP_CATCHMENT)      #"inCatchment")
                    
            outStreamFL = arcpy.management.MakeFeatureLayer(inStreamCopy, flooddsconfig.LN_FP_RIVER)
            outPointFL = arcpy.management.MakeFeatureLayer(inPointsCopy, flooddsconfig.LN_FP_WATERPOINT) 
            outCatchmentFL = arcpy.management.MakeFeatureLayer(inCatchmentCopy, flooddsconfig.LN_FP_CATCHMENT)
            outHTable = arcpy.management.MakeTableView(pHTable, flooddsconfig.TB_HTable) 

            outWKS = sFWKSFullPath
        except arcpy.ExecuteError:
            sOK = str(arcpy.GetMessages(2))
            arcpy.AddError(sOK)
        except:
            sOK = str(trace())
            arcpy.AddError(sOK)
        finally:
            if(pEditor!=None):
                pEditor.stopEditing(True)
        
        if(sOK==apwrutils.C_OK):
            tReturn = (sOK, outStreamFL, outPointFL, outCatchmentFL, outWKS, outRWKS, outHTable)
        else:
            tReturn = (sOK)

        return tReturn
         

if(__name__=='__main__'):
    try:
        runName = arcpy.GetParameterAsText(0)
        inStream = arcpy.GetParameterAsText(1)    #inStream
        inPoints = arcpy.GetParameterAsText(2)    #10/85 points, 10%-85% measured from downstream.
        inCatchment = arcpy.GetParameterAsText(3)
        inDemRaster = arcpy.GetParameterAsText(4)
        sDH = arcpy.GetParameterAsText(5)         #comma delimited dhs (1;2;5;10 etc) 
        sConfMatch = arcpy.GetParameterAsText(6)
        outFLStream = arcpy.GetParameterAsText(7)
        outFLPoint = arcpy.GetParameterAsText(8)
        outFLCatchment = arcpy.GetParameterAsText(9)
        outWorkspace = arcpy.GetParameterAsText(10)
        outRWKS = arcpy.GetParameterAsText(11) 
        outHTable = arcpy.GetParameterAsText(12)
        
        for i in range(0,len(sys.argv)-2):
            arcpy.AddMessage(arcpy.GetParameterAsText(i))
             
        ddt = time.clock()
        #..Create GDB with the runName, copy the inStream, inPoints etc to that GDB.
        lDHs = sDH.split(";")
        if(len(lDHs)>0): 
            #..Create H+idx field to hold the s
            oProcessor = ApFloodDS()
            lResults = oProcessor.execute(runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch)
            if(lResults[0]== apwrutils.C_OK) :
                outFLStream = lResults[1]
                outFLPoint = lResults[2]
                outFLCatchment = lResults[3]
                outWorkspace = lResults[4]
                outRWKS = lResults[5]
                outHTable = lResults[6]
                arcpy.SetParameterAsText(7, outFLStream)
                arcpy.SetParameterAsText(8, outFLPoint)
                arcpy.SetParameterAsText(9, outFLCatchment)
                arcpy.SetParameterAsText(10, outWorkspace)
                arcpy.SetParameterAsText(11, outRWKS)
                arcpy.SetParameterAsText(12, outHTable)
        else:
            arcpy.AddMessage("No Delta H is specified.")
         
    except arcpy.ExecuteError:
        print(str(arcpy.GetMessages(2)))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    except:
        print (trace())
        arcpy.AddError(str(trace()))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    finally:
        #if(pFLOut!=''):
            #arcpy.SetParameterAsText(2, pFLOut)
        del oProcessor
        dt = datetime.datetime.now()
        print ( 'Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

