# D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro
# python flooddsmainR.py D:\Data10\FloodDS AAA1 D:\Data10\FloodDS\floodds.gdb\Layers\DrainageLine D:\Data10\FloodDS\floodds.gdb\Layers\Slp1085Point D:\Data10\FloodDS\floodds.gdb\Layers\Catchment D:\Data10\FloodDS\Layers\fillgrid10 1;4;6;10 None AddDeltaH 1
#  D:\Data10\FloodDS AAA D:\Data10\FloodDS\floodds.gdb\Layers\DrainageLine D:\Data10\FloodDS\floodds.gdb\Layers\Slp1085Point D:\Data10\FloodDS\floodds.gdb\Layers\Catchment D:\Data10\FloodDS\Layers\fillgrid10 1;4;6;10 None AddDeltaH 1
import sys 
import os 
import time 
import datetime
import multiprocessing
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
    def execute(self, runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch, sOpType, pParentFolder, pVectorFolder, pScratchWorkspace, nProcessors, pTempPath):
        '''
           runName=RunName,
           inStream=River (drainagelines)
           inPoints=Points with WaterElev (10-85Points)
           inCatchment=Catchment
           inDEMRaster=DEM raster.
           lDHs=list of deltaHs
           sConfMatch=Match-operation at the confluences (None,Avg,Max,Min).
           sOpType=AddDeltaH,Interpolate
           pParentFolder=ParentFolder for the whole operation (for common location for resulting rasters=ParentFolder/ModelName)
           pVectorFolder=ParentFolder for multipleProcessing
           pScratchWorkspace=The location for scratch vector results.
           Loop through the lDHs and call the following 4 steps, note, step 1. FloodDS is done by this routine, and is therefore, skipped, :
           2. Make3DLine, 3. WaterLevelOnRiver, 4. Convert3DLineToRaster, 5. FloodplainFrom3DRiverRaster
        '''
        sOK = apwrutils.C_OK
        pEditor = None
        sCurDir = pParentFolder  # os.getcwd()
        runName = runName.strip()
        arcpy.env.overwriteOutput = True
        if pScratchWorkspace!=None:
            arcpy.env.scratchWorkspace = pScratchWorkspace
        if(pTempPath!=None):
            os.environ['TEMP'] = pTempPath   #arcpy.env.scratchFolder 
            os.environ['TMP'] = pTempPath    #arcpy.env.scratchFolder 

            if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("in flooddsmainR: os.environ['TMP']={}, os.environ['TEMP']={}".format(os.environ['TMP'], os.environ['TEMP']))
        #outRWKS = os.path.join(outRWKS, inStep)
        if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage(sCurDir)
        outRWKS = os.path.join(sCurDir, runName)
        bExists = apwrutils.Utils.makeSureDirExists(outRWKS)
        if(bExists == False): 
            arcpy.AddMessage("RWKS: {} is created".format(outRWKS))
        else:
            arcpy.AddMessage("RWKS: {} already existed.".format(outRWKS))

        #sWKS = runName + ".gdb"
        sWKSName = "{}.gdb".format(flooddsconfig.GDB_NAME)  # + ".gdb"
        pVectorFolder = os.path.join(pVectorFolder, runName) 
        apwrutils.Utils.makeSureDirExists(pVectorFolder)
        sFWKSFullPath = os.path.join(pVectorFolder, sWKSName)      #sFWKSFullPath = os.path.join(sCurDir, sWKS)
        sGRWL = os.path.join(outRWKS, flooddsconfig.FND_G_RWL)
        bExists = apwrutils.Utils.makeSureDirExists(sGRWL) 
        dt = time.clock()       
        bWKSExist = arcpy.Exists(sFWKSFullPath) 
        try:
            dLogFPFields = {flooddsconfig.FN_ParamName: "TEXT", flooddsconfig.FN_ParamDesc: "TEXT"}
            lLogFPFields = [flooddsconfig.FN_ParamName, flooddsconfig.FN_ParamDesc]
            pLogTable = os.path.join(sFWKSFullPath, flooddsconfig.TB_LogTable) 
            if(bWKSExist==False):
                arcpy.CreateFileGDB_management(pVectorFolder, sWKSName)
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
                arcpy.AddMessage("{}. {}".format(i, hToProcess))
                  
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
            tResults0 = pMake3DLine.execute(inStreamCopy, inDemRaster, pScratchWorkspace) 
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
                        tResults1 = pWaterLevelOnRiver.execute(pFC3DLine, inPointsCopy, fldWL, sConfMatch, sOpType, pScratchWorkspace)
                        if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Completed. ddt={} dt={}".format(apwrutils.Utils.GetDSMsg(ddt), apwrutils.Utils.GetDSMsg(dt) ))
                        if(tResults1[0]==apwrutils.C_OK):
                            pFCWaterLevel = tResults1[1]
                            ddt = time.clock()
                            if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Running script convert3dlinetoraster.ApConvert3DLinetoRasterPy") 
                            pApConvert3DLinetoRasterPy = convert3dlinetoraster.ApConvert3DLinetoRasterPy()                            
                            out3DGrid = os.path.join(sGRWL,"rwl_{}".format(i))    #i=inStep
                            #out3DGridInMemory = os.path.join("in_memory","rwl_{}".format(i))
                            tReturns2 = pApConvert3DLinetoRasterPy.execute(inDemRaster, pFCWaterLevel,  out3DGrid, pScratchWorkspace)   # out3DGridInMemory)  # out3DGrid)
                            #arcpy.sa.Raster(out3DGridInMemory).save(out3DGrid)
                            if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Completed. ddt={} dt={} {}".format(apwrutils.Utils.GetDSMsg(ddt), apwrutils.Utils.GetDSMsg(dt),datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            ddt = time.clock()
                            if(tReturns2[0]==apwrutils.C_OK):
                                pRasterWL = tReturns2[1]    # should have: pRasterWL = out3DGrid
                                if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Running script floodplainfrom3driverraster.ApFloodplainFrom3DRiverRaster") 
                                pApFloodplainFrom3DRiverRaster = floodplainfrom3driverraster.ApFloodplainFrom3DRiverRaster()
                                tReturns3 = pApFloodplainFrom3DRiverRaster.execute(pRasterWL, inDemRaster, i, outRWKS, sFWKSFullPath, pFC3DLine, inCatchmentCopy, 100, h, flooddsconfig.bConnectedPolyOnly, pScratchWorkspace, nProcessors) 
                                if(tReturns3[0]==apwrutils.C_OK): 
                                    (fcZoneRslt, fpRaster) = (tReturns3[1], tReturns3[2])
                                if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("Completed. ddt={} dt={} {}".format(apwrutils.Utils.GetDSMsg(ddt), apwrutils.Utils.GetDSMsg(dt), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") ))
                        sMsg = "{} Done. ddt={} dt={} @{}".format(sMsg, apwrutils.Utils.GetDSMsg(dt1), apwrutils.Utils.GetDSMsg(dt), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        arcpy.AddMessage(sMsg)
                        arcpy.CalculateField_management(pHTableView, flooddsconfig.FN_ISDONE, 1, "PYTHON") 
                    except arcpy.ExecuteError:
                        sOK = str(arcpy.GetMessages(2))
                        sOK = "{} {}".format(sOK, trace())
                        arcpy.AddWarning(sOK)
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
            sOK = "{}{}".format(sOK, trace())
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
    oProcessor = ApFloodDS()
    interval = 30
    try:
        pFolderP = arcpy.GetParameterAsText(0)
        runName = arcpy.GetParameterAsText(1)
        inStream = arcpy.GetParameterAsText(2)    #inStream
        inPoints = arcpy.GetParameterAsText(3)    #10/85 points, 10%-85% measured from downstream.
        inCatchment = arcpy.GetParameterAsText(4)
        inDemRaster = arcpy.GetParameterAsText(5)
        sDH = arcpy.GetParameterAsText(6)         #comma delimited dhs (1;2;5;10 etc) 
        sConfMatch = arcpy.GetParameterAsText(7)
        inOpType = arcpy.GetParameterAsText(8)
        nProcessors = arcpy.GetParameterAsText(9)
        outFLStream = arcpy.GetParameterAsText(10)
        outFLPoint = arcpy.GetParameterAsText(11)
        outFLCatchment = arcpy.GetParameterAsText(12)
        
        try:
            nProcessors = int(nProcessors) 
        except:
            nProcessors = 2

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
        
        #pFolderP = apwrutils.Utils.getcwd()
        pFolderPRunName = os.path.join(pFolderP, runName) 
        pFolderPS = os.path.join(pFolderPRunName, "WKSP")
        if(os.path.exists(pFolderPS)==False):
            apwrutils.Utils.makeSureDirExists(pFolderPS)
        
        ddt = time.clock()
        arcpy.env.overwriteOutput = True 
        #..Create GDB with the runName, copy the inStream, inPoints etc to that GDB.
        lDHs = sDH.split(";")
        if(len(lDHs)>0): 
            if(nProcessors==0):
                arcpy.AddMessage("It is required that nProcessors >  0")
                pass
            else:
                inRaster = arcpy.Raster(inDemRaster)
                arcpy.env.cellSize = inRaster.meanCellWidth 
                oDesc = arcpy.Describe(inCatchment) 
                sName = oDesc.name 
                oidFld = oDesc.oidFieldName 
                pWorkspace = apwrutils.Utils.getWorkspace(inCatchment) 
                pStatTable = os.path.join(pWorkspace, "{}_Stats".format(sName))
                arcpy.Statistics_analysis(inCatchment, pStatTable, [[oidFld,"MIN"],[oidFld,"MAX"]])
                with arcpy.da.SearchCursor(pStatTable, ["MIN_{}".format(oidFld),"MAX_{}".format(oidFld)]) as rows:
                    for row in rows:
                        nMin = row[0]
                        nMax = row[1]

                #..Construct the whereclause 
                #..Select the Catchments
                #..Use catchment to select the lines,
                #..Use catchment to select the 10-85 points.
                nTotal = int(arcpy.GetCount_management(inCatchment)[0])
                dCnt = int(nTotal/nProcessors) + 1 
                results = []
                lOutFCs = []
                lFCRiverZone = []
                lFCFPZone = []

                nLower = 0
                nUpper = 0
                for iProcess in range(nProcessors):
                    sFolder = "Proc{}".format(iProcess)
                    pProcFolder = os.path.join(pFolderP, sFolder) 
                    apwrutils.Utils.makeSureDirExists(pProcFolder) 

                    pProcWKS = os.path.join(pProcFolder, "{}.gdb".format(sFolder))
                    arcpy.CreateFileGDB_management(pProcFolder, sFolder) 
                    nLower = 0 + dCnt*iProcess 
                    nUpper = nLower + dCnt
                    sWhere = "{} > {} and {} <= {}".format(oidFld, nLower, oidFld, nUpper) 
                    arcpy.AddMessage("sWhere={}".format(sWhere))
                    pFLProcCat = "{}{}".format(sName, iProcess ) 
                    arcpy.MakeFeatureLayer_management(inCatchment, pFLProcCat, sWhere) 
                    pFCProcCat = os.path.join(pProcWKS,  "Cat{}".format(iProcess)) 
                    arcpy.CopyFeatures_management(pFLProcCat, pFCProcCat) 
                    dtol = float(arcpy.env.cellSize) * 2.0
                    arcpy.AddMessage("Arcpy.Exists({})={}".format(inStream, arcpy.Exists(inStream)))
                    pFLProcRiver = "Riv{}".format(iProcess)
                    pFCProcRiver = os.path.join(os.path.join(pProcWKS, pFLProcRiver))
                    arcpy.MakeFeatureLayer_management(inStream, pFLProcRiver)
                    arcpy.SelectLayerByLocation_management(pFLProcRiver, "INTERSECT", pFCProcCat, (-1.0*dtol), "NEW_SELECTION", "NOT_INVERT")
                    arcpy.CopyFeatures_management(pFLProcRiver, pFCProcRiver)
                    pFLProcPoints = "Pnt{}".format(iProcess)
                    pFCProcpoints = os.path.join(pProcWKS, pFLProcPoints)
                    arcpy.MakeFeatureLayer_management(inPoints, pFLProcPoints)
                    arcpy.SelectLayerByLocation_management(pFLProcPoints,  "INTERSECT", pFCProcCat, None, "NEW_SELECTION", "NOT_INVERT")
                    arcpy.CopyFeatures_management(pFLProcPoints, pFCProcpoints)
                    sWKSName = "SWK{}.gdb".format(iProcess)
                    sOutFCName = "{}_{}".format(sName,iProcess)
                
                    pFolderPS = pProcFolder   # os.path.join(pProcFolder, "SWK{}".format(iProcess))

                    if(os.path.exists(pFolderPS)==False):
                        apwrutils.Utils.makeSureDirExists(pFolderPS)
                        print("pFolderPS:{} is created.".format(pFolderPS))      

                    pTempPath = os.path.join(pFolderPS, "TEMP")
                    apwrutils.Utils.makeSureDirExists(pTempPath)
                    sFWKSFullPath = os.path.join(pFolderPS, sWKSName) 
                    if(os.path.exists(sFWKSFullPath)==False):
                        arcpy.CreateFileGDB_management(pFolderPS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                        arcpy.AddMessage("FWKS: {} is created.".format(sFWKSFullPath))
                    else:
                        arcpy.Delete_management(sFWKSFullPath)
                        arcpy.AddMessage("FWKS: {} is deleted.".format(sFWKSFullPath))  
                        arcpy.CreateFileGDB_management(pFolderPS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                        arcpy.AddMessage("FWKS: {} is created.".format(sFWKSFullPath))            

                    #oProcessor.execute(runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch, inOpType, pFolderP, sFWKSFullPath)  
                    # runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch, sOpType, pParentFolder, pScratchWorkspace
                    if(nProcessors==1):
                        oProcessor.execute(runName,pFCProcRiver,pFCProcpoints,pFCProcCat,inDemRaster,lDHs,sConfMatch,inOpType,pFolderP,pFolderPS, sFWKSFullPath, nProcessors, pTempPath)
                        #oProcessor.execute(runName,pFCProcRiver,pFCProcpoints,pFCProcCat,inDemRaster,lDHs,sConfMatch,inOpType,pFolderPS,sFWKSFullPath)
                    else:
                        p = multiprocessing.Process(target = oProcessor.execute, args=(runName,pFCProcRiver,pFCProcpoints,pFCProcCat,inDemRaster,lDHs,sConfMatch,inOpType,pFolderP, pFolderPS, sFWKSFullPath, nProcessors, pTempPath))
                        results.append(p) 
                        p.start()

            if(nProcessors>1):               
                for p in results:
                    print("{} joined".format(str(p)))
                    p.join()

                while len(multiprocessing.active_children()) > 0:
                    nProc = len(multiprocessing.active_children())
                    sMsg = "Current active processes={}, {}".format(nProc, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    arcpy.AddMessage(sMsg) 
                    for actProcess in multiprocessing.active_children():
                        dt = (time.clock() - ds)
                        dt = round(dt,2)
                        arcpy.AddMessage("  {} dt={}".format(str(actProcess), dt ))
                    time.sleep(interval)

               




                #for i in range(0, nProcessors):
                #    nLower = dCnt * i
                #    nUpper = dCnt * (i+1) 
                #    sWhere = "({} > {} and {} <= {})".format(oidFld, nLower, oidFld, nUpper)
                #    sWKSName = "SWK{}.gdb".format(i)
                #    sOutFCName = "{}_{}".format(sName,i)
                
#                    pFolderPS = os.path.join(pFolderP, "SWK{}".format(i))


            ##..Create H+idx field to hold the s
            #oProcessor = ApFloodDS()
            ## pFolderP is the parent folder, default=apwrutils.Utils.getcwd(), pFolderPS=ScratchFolder under the pFolderP, a scratchworkspace = SWK.GDB would be created under pFolderPS folder.
            ## sFWKSFullPath is the run's scratchworkspace...
            #lResults = oProcessor.execute(runName, inStream, inPoints, inCatchment, inDemRaster, lDHs, sConfMatch, inOpType, pFolderP, sFWKSFullPath)  
            #if(lResults[0]== apwrutils.C_OK) :
            #    outFLStream = lResults[1]
            #    outFLPoint = lResults[2]
            #    outFLCatchment = lResults[3]
            #    outHTable = lResults[4]
            #    #outWorkspace = lResults[4]
            #    #outRWKS = lResults[5]
            #    arcpy.SetParameterAsText(8, outFLStream)
            #    arcpy.SetParameterAsText(9, outFLPoint)
            #    arcpy.SetParameterAsText(10, outFLCatchment)
            #    arcpy.SetParameterAsText(11, outHTable)
                
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
        if(oProcessor!=None):
            del oProcessor
        dt = datetime.datetime.now()
        print ( 'Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

