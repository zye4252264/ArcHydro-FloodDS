# Calling 1. make3dline.ApMake3DLine()
#         2. for each dH in dHs, convert3dlinetoraster.ApConvert3DLinetoRasterPy() , floodplainfrom3driverraster.ApFloodplainFrom3DRiverRaster()
import sys 
import os 
import time 
import datetime
import arcpy
import arcpy.sa
import apwrutils
import flooddsconfig

import make3dline
import waterlevelonriver
import convert3dlinetoraster
import floodplainfrom3driverraster

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
    def execute(self, runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch, sOpType, pParentFolder, pScratchWorkspace):
        '''Loop through the lDHs and call the following 4 steps, note, step 1. FloodDS is done by this routine, and is therefore, skipped, :
           2. Make3DLine, 3. WaterLevelOnRiver, 4. Convert3DLineToRaster, 5. FloodplainFrom3DRiverRaster
        '''
        sOK = apwrutils.C_OK
        pEditor = None
        sCurDir = pParentFolder  # os.getcwd()
        runName = runName.strip()
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = pScratchWorkspace

        #outRWKS = os.path.join(outRWKS, inStep)
        if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage(sCurDir)
        outRWKS = os.path.join(sCurDir, runName)
        apwrutils.Utils.makeSureDirExists(outRWKS)
        arcpy.AddMessage("RWKS: {} is created".format(outRWKS))
        #sWKS = runName + ".gdb"
        sWKSName = "{}.gdb".format(flooddsconfig.GDB_NAME)  # + ".gdb"
        sFWKSFullPath = os.path.join(outRWKS, sWKSName)      #sFWKSFullPath = os.path.join(sCurDir, sWKS)
        sGRWL = os.path.join(outRWKS, flooddsconfig.FND_G_RWL)
        bExists = apwrutils.Utils.makeSureDirExists(sGRWL) 
        dt = time.clock()       
        bWKSExist = arcpy.Exists(sFWKSFullPath) 
        try:
            dLogFPFields = {flooddsconfig.FN_ParamName: "TEXT", flooddsconfig.FN_ParamDesc: "TEXT"}
            lLogFPFields = [flooddsconfig.FN_ParamName, flooddsconfig.FN_ParamDesc]
            pLogTable = os.path.join(sFWKSFullPath, flooddsconfig.TB_LogTable) 

            if(bWKSExist==False):
                arcpy.CreateFileGDB_management(outRWKS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                arcpy.AddMessage("FWKS: {} is created".format(sFWKSFullPath))
                #..Create log table
                arcpy.CreateTable_management(sFWKSFullPath, flooddsconfig.TB_LogTable)
                
                apwrutils.Utils.addFields(pLogTable, dLogFPFields)
            else:
                pass
 
            #..make a copy of inStream and inPoints.
            inStreamName = os.path.basename(inStream)
            inPointsName = os.path.basename(inPoints)

            outStreamName = flooddsconfig.LN_FP_RIVER       # inStreamName   #  runName + flooddsconfig.C_UL + inStreamName
            outPointsName = flooddsconfig.LN_FP_WATERPOINT   # inPoints       #  runName + flooddsconfig.C_UL + inPoints
            outCatName = flooddsconfig.LN_FP_CATCHMENT      # inCatchment
            inStreamCopy = os.path.join(sFWKSFullPath, outStreamName)
            inPointsCopy = os.path.join(sFWKSFullPath, outPointsName)
            inCatchmentCopy = os.path.join(sFWKSFullPath, outCatName)
            
            if(bWKSExist==False): 
                arcpy.CopyFeatures_management(inStream, inStreamCopy)
                arcpy.CopyFeatures_management(inPoints, inPointsCopy)
                arcpy.CopyFeatures_management(inCatchment, inCatchmentCopy)
                #..save the in/out locations:
                with arcpy.da.InsertCursor(pLogTable, lLogFPFields) as inRows:
                    inRows.insertRow((flooddsconfig.FN_DateCreated, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))        
                    inRows.insertRow((flooddsconfig.LN_FP_RIVER, "{}->{}".format(apwrutils.Utils.getLayerFullName(inStream), inStreamCopy)))
                    inRows.insertRow((flooddsconfig.LN_FP_WATERPOINT,"{}->{}".format(apwrutils.Utils.getLayerFullName(inPoints), inPointsCopy)))
                    inRows.insertRow((flooddsconfig.LN_FP_CATCHMENT, "{}->{}".format(apwrutils.Utils.getLayerFullName(inCatchment), inCatchmentCopy)))
                    
                       
            #- move this codeblock to after pHTable is populated and dFIeldsH, V etc will be re-read in from pHTable to allow the incremental runs.
            #..add fields to the inPointsCopy  
            #dFieldsH = dict()      #..holdes field names: key:H_[index], value:[fieldtype:double]
            #dFieldsHV = dict()     #..holds dH field values key:H_[index], value:[fieldvalues 1, 2, 5.5,10...] ft etc
            #lFieldsH = []          #..keep the field order so that the fields are added in the order of H_1,H_2 etc.
            #for i,h in enumerate(lDHs):
            #    fld = self.C_WLFld + str(i)
            #    lFieldsH.append(fld)
            #    dFieldsH.setdefault(fld,"DOUBLE")
            #    dFieldsHV.setdefault(fld, h)
            #apwrutils.Utils.addFields(inPointsCopy, dFieldsH)

            pWorkspace = apwrutils.Utils.getWorkspace(inPointsCopy)

            #..Create H table
            #  HIndex HValue
            pHTable = os.path.join(pWorkspace, flooddsconfig.TB_HTable)
            if(arcpy.Exists(pHTable)==False):  
                arcpy.CreateTable_management(pWorkspace, flooddsconfig.TB_HTable)
                arcpy.AddMessage("{} table is created.".format(pHTable))

            dFields = {flooddsconfig.FN_HIndex :'LONG', flooddsconfig.FN_HValue :'DOUBLE', flooddsconfig.FN_ISDONE : 'LONG'}
            apwrutils.Utils.addFields(pHTable, dFields)
            
            #..***zye*** needs update so that it would check the existing values before inserting.. to allow the incremental update.
            lHFields = [flooddsconfig.FN_HIndex, flooddsconfig.FN_HValue, flooddsconfig.FN_ISDONE]
            #..Populate the HTable
            lExistHs = []
            existH = []    #0=OID, 1=HIndex, 2=HValue, 3=IsDone
            iBase = 0
            with arcpy.da.SearchCursor(pHTable, "*" ) as rows:
                for row in rows:
                    existH = row;
                    lExistHs.append(existH)
                    arcpy.AddMessage(existH) 
                    iBase = iBase + 1
            
            iAdded = 0
            with arcpy.da.InsertCursor(pHTable, lHFields) as inRows:
                for i,h in enumerate(lDHs):
                    bCanAdd = False 
                    if(len(lExistHs)==0):
                        bCanAdd = True 
                    else:
                        bCanAdd = True    
                        for existH in lExistHs:
                            arcpy.AddMessage("{} {}|(existH[2]==float(h))={}".format(existH[2], h, existH[2]==float(h)))
                            if(existH[2]==float(h)):
                                bCanAdd = False
                                break
                    arcpy.AddMessage("{}. {} bCanAdd={}".format(i, h, bCanAdd))
                    if(bCanAdd==True):
                        iAdded = iAdded + 1 
                        inRow = [iAdded+iBase,h,0]
                        inRows.insertRow(inRow)
            

            #..Construct the lHsToProcess, lDHs is no longer needed for the rest of the codes,  Modified for the incremental updates.
            lHsToProcess = []            
            with arcpy.da.SearchCursor(pHTable, "*" ) as rows:
                for row in rows:
                    hToProcess = row;
                    lHsToProcess.append(hToProcess)
           

            #..add fields to the inPointsCopy
            dFieldsH = dict()      #..holdes field names: key:H_[index], value:[fieldtype:double]
            dFieldsHV = dict()     #..holds dH field values key:H_[index], value:[fieldvalues 1, 2, 5.5,10...] ft etc
            lFieldsH = []          #..keep the field order so that the fields are added in the order of H_1,H_2 etc.
            for i, hToProcess in enumerate(lHsToProcess):
                fld = "{}{}".format(self.C_WLFld, hToProcess[1])
                lFieldsH.append(fld)
                dFieldsH.setdefault(fld,"DOUBLE")
                dFieldsHV.setdefault(fld, hToProcess[2])
                if((self.DebugLevel & 2) ==2): arcpy.AddMessage("{}. {}".format(i, hToProcess))
                  
            apwrutils.Utils.addFields(inPointsCopy, dFieldsH)
            #pEditor = arcpy.da.Editor(pWorkspace)
            #pEditor.startEditing(False,False)
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
            #arcpy.AddMessage("before deleting")
            if(arcpy.Exists(flooddsconfig.LN_FP_RIVER)): arcpy.Delete_management(flooddsconfig.LN_FP_RIVER)              #"inStream")
            if(arcpy.Exists(flooddsconfig.LN_FP_WATERPOINT)): arcpy.Delete_management(flooddsconfig.LN_FP_WATERPOINT)    #"inPoints")
            if(arcpy.Exists(flooddsconfig.LN_FP_CATCHMENT)): arcpy.Delete_management(flooddsconfig.LN_FP_CATCHMENT)      #"inCatchment")
            
            pFLStream = arcpy.management.MakeFeatureLayer(inStreamCopy, flooddsconfig.LN_FP_RIVER)
            pFLPoint = arcpy.management.MakeFeatureLayer(inPointsCopy, flooddsconfig.LN_FP_WATERPOINT) 
            pFLCatchment = arcpy.management.MakeFeatureLayer(inCatchmentCopy, flooddsconfig.LN_FP_CATCHMENT)

            ddt = time.clock()
            if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Running script make3dline.ApMake3DLine")
            pMake3DLine = make3dline.ApMake3DLine()
            tResults0 = pMake3DLine.execute(inStreamCopy, inDemRaster) 
            if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Completed.  dt={}".format(apwrutils.Utils.GetDSMsg(ddt)))

            if(tResults0[0]==apwrutils.C_OK):
                pFC3DLine = tResults0[1]
                if((flooddsconfig.debugLevel & 1)==1):  arcpy.AddMessage("pFC={}".format(pFC3DLine))
                for hToProcess in lHsToProcess:
                    i = hToProcess[1]
                    h = hToProcess[2]
                    if(hToProcess[3]==1):
                        continue
                    try:
                        fldWL = "{}_{}".format(flooddsconfig.HD_WL,i)
                        dt1 = time.clock()
                        ddt = time.clock()
                        pHTableView = "{}_{}".format(flooddsconfig.TB_HTable, i)
                        arcpy.MakeTableView_management(pHTable, pHTableView, "{} = {}".format(flooddsconfig.FN_HValue, h))
                        arcpy.CalculateField_management(pHTableView, flooddsconfig.FN_ISDONE, -1, "PYTHON") 
                        #..Potential parallel/multiprocessing can be applied to the codes starting from here.....
                        sMsg = "Processing inStep={} dh={}".format(i, h)
                        pWaterLevelOnRiver = waterlevelonriver.ApWaterLevelOnRiver()
                        if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage("Before calling... {},{},{},{},{}".format(pFC3DLine, inPointsCopy, fldWL, sConfMatch, sOpType))
                        if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Running script waterlevelonriver.ApWaterLevelOnRiver")                    
                        tResults1 = pWaterLevelOnRiver.execute(pFC3DLine, inPointsCopy, fldWL, sConfMatch, sOpType)
                        if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Completed. ddt={} dt={}".format(apwrutils.Utils.GetDSMsg(ddt), apwrutils.Utils.GetDSMsg(dt) ))
                        if(tResults1[0]==apwrutils.C_OK):
                            pFCWaterLevel = tResults1[1]
                            ddt = time.clock()
                            if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Running script convert3dlinetoraster.ApConvert3DLinetoRasterPy") 
                            pApConvert3DLinetoRasterPy = convert3dlinetoraster.ApConvert3DLinetoRasterPy()                            
                            out3DGrid = os.path.join(sGRWL,"rwl_{}".format(i))    #i=inStep
                            #out3DGridInMemory = os.path.join("in_memory","rwl_{}".format(i))
                            tReturns2 = pApConvert3DLinetoRasterPy.execute(inDemRaster, pFCWaterLevel,  out3DGrid)   # out3DGridInMemory)  # out3DGrid)
                            #arcpy.sa.Raster(out3DGridInMemory).save(out3DGrid)
                            if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Completed. ddt={} dt={} {}".format(apwrutils.Utils.GetDSMsg(ddt), apwrutils.Utils.GetDSMsg(dt),datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            ddt = time.clock()
                            if(tReturns2[0]==apwrutils.C_OK):
                                pRasterWL = tReturns2[1]    # should have: pRasterWL = out3DGrid
                                if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Running script floodplainfrom3driverraster.ApFloodplainFrom3DRiverRaster") 
                                pApFloodplainFrom3DRiverRaster = floodplainfrom3driverraster.ApFloodplainFrom3DRiverRaster()
                                tReturns3 = pApFloodplainFrom3DRiverRaster.execute(pRasterWL, inDemRaster, i, outRWKS, sFWKSFullPath, pFC3DLine, inCatchmentCopy, 100, h, True, pScratchWorkspace, 0 ) 
                                if(tReturns3[0]==apwrutils.C_OK): 
                                    (fcZoneRslt, fpRaster) = (tReturns3[1], tReturns3[2])
                                if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Completed. ddt={} dt={} {}".format(apwrutils.Utils.GetDSMsg(ddt), apwrutils.Utils.GetDSMsg(dt), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") ))
                        sMsg = "{} Done. ddt={} dt={} @{}".format(sMsg, apwrutils.Utils.GetDSMsg(dt1), apwrutils.Utils.GetDSMsg(dt), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        arcpy.AddMessage(sMsg)
                        arcpy.CalculateField_management(pHTableView, flooddsconfig.FN_ISDONE, 1, "PYTHON") 
                    except:
                        arcpy.AddMessage(trace())

            outHTable = arcpy.management.MakeTableView(pHTable, flooddsconfig.TB_HTable)    
            
            #..save the in/out locations:
            with arcpy.da.InsertCursor(pLogTable, lLogFPFields) as inRows:
                inRows.insertRow(("Completed At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))        
                inRows.insertRow(("dt", apwrutils.Utils.GetDSMsg(dt)))

            #outWKS = sFWKSFullPath
        except arcpy.ExecuteError:
            sOK = str(arcpy.GetMessages(2))
            arcpy.AddError(sOK)
        except:
            sOK = str(trace())
            arcpy.AddError(sOK)
        finally:
            #if(pEditor!=None):
            #    pEditor.stopEditing(True)
            pass

        if(sOK==apwrutils.C_OK):
            #tReturn = (sOK, outStreamFL, outPointFL, outCatchmentFL, outWKS, outRWKS)
            tReturn = (sOK, pFLStream, pFLPoint, pFLCatchment, outHTable)
        else:
            tReturn = (sOK)

        return tReturn
         

if(__name__=='__main__'):
    try:
        arcpy.AddMessage("2016/10/12")
        runName = arcpy.GetParameterAsText(0)
        inStream = arcpy.GetParameterAsText(1)    #inStream
        inPoints = arcpy.GetParameterAsText(2)    #10/85 points, 10%-85% measured from downstream.
        inCatchment = arcpy.GetParameterAsText(3)
        inDemRaster = arcpy.GetParameterAsText(4)
        sDH = arcpy.GetParameterAsText(5)         #comma delimited dhs (1;2;5;10 etc) 
        sConfMatch = arcpy.GetParameterAsText(6)
        inOpType = arcpy.GetParameterAsText(7)

        outFLStream = arcpy.GetParameterAsText(8)
        outFLPoint = arcpy.GetParameterAsText(9)
        outFLCatchment = arcpy.GetParameterAsText(10)
        
        #outWorkspace = arcpy.GetParameterAsText(11)
        #outRWKS = arcpy.GetParameterAsText(12) 
      
        bIsLicensed = apwrutils.Utils.isLicensedSpatial() 
        if bIsLicensed==False:
            arcpy.AddError("Spatial Analyst extension is not available.")
            print("Spatial Analyst extension is not available.")
            sOK = apwrutils.C_NOTOK
            sys.exit(0)
        else:
            #Checkout extension
            arcpy.CheckOutExtension('Spatial')
                  
        if((flooddsconfig.debugLevel & 1)==1):
            for i in range(0,len(sys.argv)-2):
                arcpy.AddMessage(arcpy.GetParameterAsText(i))
        
        pFolderP = apwrutils.Utils.getcwd()
        pFolderPRunName = os.path.join(pFolderP, runName) 
        pFolderPS = os.path.join(pFolderPRunName, "WKSP")
        if(os.path.exists(pFolderPS)==False):
            apwrutils.Utils.makeSureDirExists(pFolderPS)
        
        sWKSName = "SWK.gdb"
        sFWKSFullPath = os.path.join(pFolderPS, sWKSName) 
        if(os.path.exists(sFWKSFullPath)==False):
            arcpy.CreateFileGDB_management(pFolderPS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
            arcpy.AddMessage("FWKS: {} is created.".format(sFWKSFullPath))
        else:
            arcpy.Delete_management(sFWKSFullPath)
            arcpy.AddMessage("FWKS: {} is deleted.".format(sFWKSFullPath))  
            arcpy.CreateFileGDB_management(pFolderPS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
            arcpy.AddMessage("FWKS: {} is created.".format(sFWKSFullPath))            

        ddt = time.clock()
        #..Create GDB with the runName, copy the inStream, inPoints etc to that GDB.
        lDHs = sDH.split(";")
        if(len(lDHs)>0): 
            #..Create H+idx field to hold the s
            oProcessor = ApFloodDS()
            # pFolderP is the parent folder, default=apwrutils.Utils.getcwd(), pFolderPS=ScratchFolder under the pFolderP, a scratchworkspace = SWK.GDB would be created under pFolderPS folder.
            # sFWKSFullPath is the run's scratchworkspace...
            lResults = oProcessor.execute(runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch, inOpType, pFolderP, sFWKSFullPath)  
            if(lResults[0]== apwrutils.C_OK) :
                outFLStream = lResults[1]
                outFLPoint = lResults[2]
                outFLCatchment = lResults[3]
                outHTable = lResults[4]
                #outWorkspace = lResults[4]
                #outRWKS = lResults[5]
                arcpy.SetParameterAsText(8, outFLStream)
                arcpy.SetParameterAsText(9, outFLPoint)
                arcpy.SetParameterAsText(10, outFLCatchment)
                arcpy.SetParameterAsText(11, outHTable)
                
        else:
            arcpy.AddMessage("No Delta H is specified.")
         
    except arcpy.ExecuteError:
        sMsg = str(arcpy.GetMessages(2))
        arcpy.AddError(sMsg)
    except:
        sMsg = str(trace())
        sMsg = "{} {}".format(sMsg, str(arcpy.GetMessages(2)))
        arcpy.AddError(sMsg)
    finally:
        del oProcessor
        dt = datetime.datetime.now()
        print ( 'Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

