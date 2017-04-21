import sys 
import os 
import time 
import datetime
import arcpy
import arcpy.sa
import apwrutils
import flooddsconfig

import floodplainfromhand

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


class ApFloodDSMainHAND:
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
    #oProcessor.execute(runName, inHANDRaster, inCatchment, lDHs, pFolderP, sFWKSFullPath)  
    def execute(self, runName, inStream, inCatchment, inRasterHAND, inRasterMinLocal, inRasterStr, lDHs, bConnectedOnly, pParentFolder, pScratchWorkspace):
        '''Loop through the lDHs and call the following 4 steps, note, step 1. FloodDS is done by this routine, and is therefore, skipped, :
           2. Make3DLine, 3. WaterLevelOnRiver, 4. Convert3DLineToRaster, 5. FloodplainFrom3DRiverRaster
        '''
        if(self.DebugLevel>0): arcpy.AddMessage("Running {}. {}".format(self.thisFileName(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
        #sGRWL = os.path.join(outRWKS, flooddsconfig.FND_G_RWL)
        #bExists = apwrutils.Utils.makeSureDirExists(sGRWL) 
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
 
            outStreamName = flooddsconfig.LN_FP_RIVER       # inStreamName   #  runName + flooddsconfig.C_UL + inStreamName
            outPointsName = flooddsconfig.LN_FP_WATERPOINT   # inPoints       #  runName + flooddsconfig.C_UL + inPoints
            outCatName = flooddsconfig.LN_FP_CATCHMENT      # inCatchment
            inStreamCopy = os.path.join(sFWKSFullPath, outStreamName)
            inCatchmentCopy = os.path.join(sFWKSFullPath, outCatName)
            if(bWKSExist==False): 
                arcpy.CopyFeatures_management(inStream, inStreamCopy)
                arcpy.CopyFeatures_management(inCatchment, inCatchmentCopy)
                #..save the in/out locations:
                with arcpy.da.InsertCursor(pLogTable, lLogFPFields) as inRows:
                    inRows.insertRow((flooddsconfig.FN_DateCreated, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))        
                    inRows.insertRow((flooddsconfig.LN_FP_RIVER, "{}->{}".format(apwrutils.Utils.getLayerFullName(inStream), inStreamCopy)))
                    inRows.insertRow((flooddsconfig.LN_FP_CATCHMENT, "{}->{}".format(apwrutils.Utils.getLayerFullName(inCatchment), inCatchmentCopy)))
       
            pWorkspace = apwrutils.Utils.getWorkspace(inStreamCopy)
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
                    h = float(h) 
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
            with arcpy.da.SearchCursor(pHTable, [flooddsconfig.FN_HIndex, flooddsconfig.FN_HValue, flooddsconfig.FN_ISDONE] ) as rows:
                for row in rows:
                    hToProcess = (row[0], row[1], row[2]);
                    arcpy.AddMessage("HIndex={}, HValue={}, IsDone={} IndexType={}".format(hToProcess[0],hToProcess[1],hToProcess[2], type(hToProcess[0])))
                    lHsToProcess.append(hToProcess)
          
            #arcpy.AddMessage("before deleting")
            if(arcpy.Exists(flooddsconfig.LN_FP_RIVER)): arcpy.Delete_management(flooddsconfig.LN_FP_RIVER)              #"inStream")
            if(arcpy.Exists(flooddsconfig.LN_FP_CATCHMENT)): arcpy.Delete_management(flooddsconfig.LN_FP_CATCHMENT)      #"inCatchment")
            if(arcpy.Exists(flooddsconfig.LN_FP_RIVER)): arcpy.Delete_management(flooddsconfig.LN_FP_RIVER)
            if(arcpy.Exists(flooddsconfig.LN_FP_CATCHMENT)): arcpy.Delete_management(flooddsconfig.LN_FP_CATCHMENT)
            pFLStream = arcpy.management.MakeFeatureLayer(inStreamCopy, flooddsconfig.LN_FP_RIVER)
            pFLCatchment = arcpy.management.MakeFeatureLayer(inCatchmentCopy, flooddsconfig.LN_FP_CATCHMENT)
            for hToProcess in lHsToProcess:
                i = hToProcess[0]
                h = hToProcess[1]
                if(hToProcess[2]==1):
                    continue
                try:
                    fldWL = "{}_{}".format(flooddsconfig.HD_WL,i)
                    dt1 = time.clock()
                    ddt = time.clock()
                    pHTableView = "{}_{}".format(flooddsconfig.TB_HTable, i)
                    arcpy.MakeTableView_management(pHTable, pHTableView, "{} = {}".format(flooddsconfig.FN_HIndex, i))
                    arcpy.CalculateField_management(pHTableView, flooddsconfig.FN_ISDONE, -1, "PYTHON") 
                    #..Potential parallel/multiprocessing can be applied to the codes starting from here.....
                    sMsg = "Processing inStep={} dh={}".format(i, h)
                    ddt = time.clock()
                    pApFloodplainFromHand = floodplainfromhand.ApFloodplainFromHAND()
                    tReturns1 = pApFloodplainFromHand.execute(inStream, inCatchment, inRasterHAND, inRasterMinLocal, inRasterStr, int(i), h, outRWKS, sFWKSFullPath, bConnectedOnly, pScratchWorkspace) 
                    if(tReturns1[0]==apwrutils.C_OK): 
                        (fcZoneRslt, fpRaster) = (tReturns1[1], tReturns1[2])
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
                inRows.insertRow(("dtTotal", apwrutils.Utils.GetDSMsg(dt)))

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
            tReturn = (sOK, pFLStream, pFLCatchment, outHTable)
        else:
            tReturn = (sOK)

        return tReturn
         

if(__name__=='__main__'):
    #HAND (Height Above Nearest Drainage Point)
    try:
        arcpy.AddMessage("2016/11/07->2016/11/10->2017/04/10")
        runName = arcpy.GetParameterAsText(0)
        inStream = arcpy.GetParameterAsText(1)
        inCatchment = arcpy.GetParameterAsText(2)
        inRasterHAND = arcpy.GetParameterAsText(3)
        inRasterMinLocal = arcpy.GetParameterAsText(4)   #LocalMin is used to get HAND (=DEM-MinLocal), wse0 = con(hand,hand,"","Value<deltaH"), final wse=sa.Plus(wse0, MinLocal)
        inRasterStr = arcpy.GetParameterAsText(5)        
        bRiverConnectedOnly = arcpy.GetParameterAsText(6)
        sDH = arcpy.GetParameterAsText(7)         #comma delimited dhs (1;2;5;10 etc) 
        outFLStream = arcpy.GetParameterAsText(8)
        outFLCatchment = arcpy.GetParameterAsText(9)
        
        bRiverConnectedOnly = apwrutils.Utils.str2Bool(bRiverConnectedOnly) 

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
            oProcessor = ApFloodDSMainHAND()
            # pFolderP is the parent folder, default=apwrutils.Utils.getcwd(), pFolderPS=ScratchFolder under the pFolderP, a scratchworkspace = SWK.GDB would be created under pFolderPS folder.
            # sFWKSFullPath is the run's scratchworkspace...
            lResults = oProcessor.execute(runName, inStream, inCatchment, inRasterHAND, inRasterMinLocal, inRasterStr, lDHs, bRiverConnectedOnly, pFolderP, sFWKSFullPath)  
            if(lResults[0]== apwrutils.C_OK) :
                outFLStream = lResults[1]
                outFLCatchment = lResults[2]
                outHTable = lResults[3]
                #outWorkspace = lResults[4]
                #outRWKS = lResults[5]
                arcpy.SetParameterAsText(8, outFLStream)
                arcpy.SetParameterAsText(9, outFLCatchment)
                arcpy.SetParameterAsText(10, outHTable)
        else:
            arcpy.AddMessage("No Delta H is specified.")
         
    except arcpy.ExecuteError:
        sMsg = str(arcpy.GetMessages(2))
        arcpy.AddError("{} {}".format(sMsg,trace()))

    except:
        sMsg = str(trace())
        sMsg = "{} {}".format(sMsg, str(arcpy.GetMessages(2)))
        arcpy.AddError(sMsg)
    finally:
        del oProcessor
        dt = datetime.datetime.now()
        print ( 'Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

