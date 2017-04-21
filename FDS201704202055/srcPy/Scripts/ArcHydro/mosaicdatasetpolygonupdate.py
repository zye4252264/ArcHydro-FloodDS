import sys 
import os 
import time 
import datetime
import multiprocessing

import arcpy
import arcpy.sa
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

class MosaicDatasetPolygonUpdate:

    def __init__(self):
        self.DebugLevel = 0
   
    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())
    # Load the configuration xml.


    #def execute(self, parameters, messages):
    def execute(self, flMosaicDS, rasterFolderName=""):
        sOK = apwrutils.C_OK
        scratch_wks =   "%scratchworkspace%"    #flooddsconfig.pScratchWorkspace 
        pEditor = None
        sCurDir = apwrutils.Utils.getcwd()  # os.getcwd()
        pFLPoly = ""
        try:
            oDesc = arcpy.Describe(flMosaicDS) 
            pWorkspace = oDesc.path
            pFolder = os.path.dirname(pWorkspace) 
            sName = oDesc.name 
            spRef = oDesc.spatialReference
            oidFld = oDesc.oidFieldName
            rsPath = os.path.join(pFolder, rasterFolderName)
            if(self.DebugLevel>0):
                arcpy.AddMessage("pFolder={}\nrasterPath={}\npWorkspace={}, Name={}, \nspRef={}".format(pFolder, rsPath, pWorkspace, sName, spRef.name)) 
            arcpy.env.overwriteOutput = True
            nCnt = arcpy.GetCount_management(flMosaicDS)[0]
            i = 0
            pEditor = arcpy.da.Editor(pWorkspace)
            pEditor.startEditing (False,False)
            with arcpy.da.UpdateCursor(flMosaicDS, [apwrutils.FN_ShapeAt, oidFld, apwrutils.FN_NAME]) as upRows:
                for upRow in upRows:
                    i = i + 1
                    try:
                        pExt = upRow[0].extent
                        #arcpy.env.extent = pExt
                        inRaster = os.path.join(rsPath, upRow[2])
                        if(arcpy.Exists(inRaster)==False): inRaster = "{}.tif".format(inRaster)
                        sMsg = "{} of {}, {}".format(i, nCnt, inRaster)
                        if(self.DebugLevel>0): sMsg = "{}. pExt={}".format(sMsg, pExt)
                        arcpy.AddMessage(sMsg)
                        pPolyIsNull = arcpy.sa.IsNull(inRaster)
                        pPolyFC = os.path.join(scratch_wks, "{}_{}".format(upRow[2],upRow[1])) 
                        arcpy.RasterToPolygon_conversion(pPolyIsNull, pPolyFC, "NO_SIMPLIFY")
                        sWhere = "gridcode=0" 
                        #pPolyFL = upRow[2]
                        #arcpy.MakeFeatureLayer_management(pPolyFC,pPolyFL, sWhere)
                        pPolyMerge = None
                        with arcpy.da.SearchCursor(pPolyFC, [apwrutils.FN_ShapeAt, "Shape_Area"], sWhere, None, False, sql_clause=(None, "Order By Shape_Area DESC") ) as rows:
                            for row in rows:
                                pPoly = row[0]
                                try:
                                    if(pPolyMerge==None):
                                        pPolyMerge = pPoly
                                    else:
                                        pPolyMerge = pPolyMerge.union(pPoly)
                                except:
                                    pass
                        if(pPolyMerge!=None):
                            upRow[0] = pPolyMerge
                            upRows.updateRow(upRow)
                                
                    except:
                        arcpy.AddMessage(trace())  


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
                tReturn = (sOK, flMosaicDS)
            else:
                tReturn = (sOK)

        return tReturn

def doWork(flMosaicDS, rasterFolderName="",sWhere="", processID=0, pScratchWorkspace=None):
    sOK = apwrutils.C_OK
    scratch_wks = pScratchWorkspace   # r"C:\Users\ye\Documents\ArcGIS\Default.gdb"    #"%scratchworkspace%"    #flooddsconfig.pScratchWorkspace 
    pEditor = None
    sCurDir = apwrutils.Utils.getcwd()  # os.getcwd()
    pFLPoly = ""
    bIsLicensed = apwrutils.Utils.isLicensedSpatial() 
    if bIsLicensed==False:
        arcpy.AddError("Spatial Analyst extension is not available.")
        print("Spatial Analyst extension is not available.")
        sOK = apwrutils.C_NOTOK
        return (sOK)
    else:
        #Checkout extension
        arcpy.CheckOutExtension('Spatial')

    try:
        oDesc = arcpy.Describe(flMosaicDS) 
        pWorkspace = oDesc.path
        pFolder = os.path.dirname(pWorkspace) 
        sName = oDesc.name 
        spRef = oDesc.spatialReference
        oidFld = oDesc.oidFieldName
        rsPath = os.path.join(pFolder, rasterFolderName)
        if(flooddsconfig.debugLevel>0):
            arcpy.AddMessage("pFolder={}\nrasterPath={}\npWorkspace={}, Name={}, \nspRef={}".format(pFolder, rsPath, pWorkspace, sName, spRef.name)) 
        
        arcpy.env.overwriteOutput = True
        arcpy.env.scratchWorkspace = pScratchWorkspace
        print(arcpy.env.scratchFolder)
        i = 0
        #pEditor = arcpy.da.Editor(pWorkspace)
        #pEditor.startEditing (False,False)
        arcpy.AddMessage("sWhere={}".format(sWhere))
        pFL = "{}_{}".format(oDesc.name, processID)
        arcpy.MakeFeatureLayer_management(flMosaicDS, pFL, sWhere)
        nCnt = arcpy.GetCount_management(pFL)[0]
        pFCOut = os.path.join(pScratchWorkspace, "{}_{}".format(sName, processID))
        arcpy.CopyFeatures_management(pFL, pFCOut)
        with arcpy.da.UpdateCursor(pFCOut, [apwrutils.FN_ShapeAt, oidFld, apwrutils.FN_NAME]) as upRows:
            for upRow in upRows:
                i = i + 1
                try:
                    pExt = upRow[0].extent
                    #arcpy.env.extent = pExt
                    inRaster = os.path.join(rsPath, upRow[2])
                    if(arcpy.Exists(inRaster)==False): inRaster = "{}.tif".format(inRaster)
                    sMsg = "PID{}: {} of {}, {}".format(processID, i, nCnt, inRaster)
                    if(flooddsconfig.debugLevel>0): sMsg = "{}. pExt={}".format(sMsg, pExt)
                    arcpy.AddMessage(sMsg)
                    pPolyIsNull = arcpy.sa.IsNull(inRaster)
                    pPolyFC = os.path.join(scratch_wks, "{}_{}".format(upRow[2],upRow[1])) 
                    arcpy.RasterToPolygon_conversion(pPolyIsNull, pPolyFC, "NO_SIMPLIFY")
                    sWhere = "gridcode=0" 
                    #pPolyFL = upRow[2]
                    #arcpy.MakeFeatureLayer_management(pPolyFC,pPolyFL, sWhere)
                    pPolyMerge = None
                    with arcpy.da.SearchCursor(pPolyFC, [apwrutils.FN_ShapeAt, "Shape_Area"], sWhere, None, False, sql_clause=(None, "Order By Shape_Area DESC") ) as rows:
                        for row in rows:
                            pPoly = row[0]
                            try:
                                if(pPolyMerge==None):
                                    pPolyMerge = pPoly
                                else:
                                    pPolyMerge = pPolyMerge.union(pPoly)
                            except:
                                pass
                    if(pPolyMerge!=None):
                        upRow[0] = pPolyMerge
                        upRows.updateRow(upRow)
                                
                except:
                    arcpy.AddMessage(trace())  

    except arcpy.ExecuteError:
        sOK = str(arcpy.GetMessages(2))
        arcpy.AddError(sOK)
    except:
        sOK = str(trace())
        arcpy.AddError(sOK)
    finally:
        #if(pEditor!=None):
        #    pEditor.stopEditing(True)

        if(sOK==apwrutils.C_OK):
            tReturn = (sOK, flMosaicDS)
        else:
            tReturn = (sOK)

    return tReturn         

if(__name__=='__main__'):
    #D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro
    #python mosaicdatasetpolygonupdate.py D:\Data10\HAND20160804\HAND04\FP.gdb\Depth_Poly Depth 4
    oProcessor = None 
    if(len(sys.argv)<4):
        arcpy.AddMessage("Usage: {} pathToRasterDSPoly RasterFolderName nProcessors".format(sys.argv[0]))
        sys.exit(0)
    arcpy.AddMessage(sys.argv)
    lOutFCs = []
    try:
        sOK = apwrutils.C_OK 
        ds = time.clock()
        oProcessor = None
        interval = 30
        flMosaicDS = arcpy.GetParameterAsText(0) 
        rasterFolderName = arcpy.GetParameterAsText(1)
        nProcessors = arcpy.GetParameterAsText(2)
        
        if(apwrutils.Utils.isNumeric(nProcessors)):
            nProcessors = int(nProcessors)
        else:
            nProcessors = 0

        arcpy.AddMessage("{} processes.".format(nProcessors))

        bIsLicensed = apwrutils.Utils.isLicensedSpatial() 
        if bIsLicensed==False:
            arcpy.AddError("Spatial Analyst extension is not available.")
            print("Spatial Analyst extension is not available.")
            sOK = apwrutils.C_NOTOK
        else:
            #Checkout extension
            arcpy.CheckOutExtension('Spatial')
        
        if(bIsLicensed==False):
            sys.exit(0) 
                                     
        if(rasterFolderName==None):
            rasterFolderName = flMosaicDS.split("_")[0]
                    
        if((flooddsconfig.debugLevel & 1)==1):
            for i in range(0,len(sys.argv)-2):
                arcpy.AddMessage(arcpy.GetParameterAsText(i))
        
        arcpy.env.overwriteOutput = True
        if(nProcessors<=1):
            oProcessor = MosaicDatasetPolygonUpdate()
            oProcessor.DebugLevel = flooddsconfig.debugLevel
            (sOK, pFLPoly) = oProcessor.execute(flMosaicDS, rasterFolderName)             
        else:
            ds1 = time.clock()
            nLower = 0
            nUpper = 0
            oDesc = arcpy.Describe(flMosaicDS)
            sName = oDesc.name 
            pWorkspace = oDesc.path
            pFolderP = os.path.dirname(pWorkspace) 
            oidFld = oDesc.oidFieldName
            #nTotal = int(arcpy.GetCount_management(flMosaicDS)[0])
            #dCnt = nTotal/nProcessors
            pStatTable = os.path.join(pWorkspace, "{}_Stats".format(sName))
            arcpy.Statistics_analysis(flMosaicDS, pStatTable, [[oidFld,"MIN"],[oidFld,"MAX"]])
            with arcpy.da.SearchCursor(pStatTable, ["MIN_{}".format(oidFld),"MAX_{}".format(oidFld)]) as rows:
                for row in rows:
                    nMin = row[0]
                    nMax = row[1]

            nTotal = nMax - nMin + 1
            dCnt = nTotal/nProcessors 
            arcpy.AddMessage("nTotal={}, dCnt={}, nMin={}, nMax={} dt={}".format(nTotal, dCnt, nMin, nMax, apwrutils.Utils.GetDSMsg(ds1)))
            ds1 = time.clock()
            results = []
            for i in range(0, nProcessors):
                nLower = nMin + dCnt * i
                nUpper = nMin + dCnt * (i+1) 
                sWhere = "({} > {} and {} <= {})".format(oidFld, nLower, oidFld, nUpper)
                sWKSName = "SWK{}.gdb".format(i)
                sOutFCName = "{}_{}".format(sName,i)
                
                pFolderPS = os.path.join(pFolderP, "SWK{}".format(i))
                if(os.path.exists(pFolderPS)==False):
                    apwrutils.Utils.makeSureDirExists(pFolderPS)
                    print("pFolderPS:{} is created.".format(pFolderPS))      

                sFWKSFullPath = os.path.join(pFolderPS, sWKSName) 
                if(os.path.exists(sFWKSFullPath)==False):
                    arcpy.CreateFileGDB_management(pFolderPS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                    arcpy.AddMessage("FWKS: {} is created.".format(sFWKSFullPath))
                else:
                    arcpy.Delete_management(sFWKSFullPath)
                    arcpy.AddMessage("FWKS: {} is deleted.".format(sFWKSFullPath))  
                    arcpy.CreateFileGDB_management(pFolderPS, sWKSName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                    arcpy.AddMessage("FWKS: {} is created.".format(sFWKSFullPath))            
                print(sWhere)

                lOutFCs.append(os.path.join(sFWKSFullPath, sOutFCName))  
                p = multiprocessing.Process(target = doWork, args=(flMosaicDS, rasterFolderName, sWhere, i, sFWKSFullPath))
                results.append(p) 
                p.start()   
                           
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

            #pFLPoly = flMosaicDS
            
            arcpy.AddMessage("Multiple processing with {} processors.  dt={}".format(nProcessors, apwrutils.Utils.GetDSMsg(ds)))
            ds1 = time.clock()
            arcpy.DeleteFeatures_management(flMosaicDS)
            sLayers = ""
            for sLayer in lOutFCs:
                if(sLayers==""):
                    sLayers = sLayer 
                else:
                    sLayers = "{};{}".format(sLayers,sLayer)
            arcpy.AddMessage(sLayers)
            arcpy.Append_management(sLayers, flMosaicDS, "NO_TEST")
            arcpy.AddMessage("arcpy.Append_management('{}','{}','NO_TEST'). dt={}".format(sLayers,flMosaicDS, apwrutils.Utils.GetDSMsg(ds1)))
            arcpy.AddMessage("Total processing time.  dt={}".format(apwrutils.Utils.GetDSMsg(ds)))

            if(sOK==apwrutils.C_OK):
                pFLPoly = "FL{}".format(sName)
                arcpy.MakeFeatureLayer_management(flMosaicDS, pFLPoly)
                arcpy.SetParameterAsText(3, pFLPoly)
             
    except arcpy.ExecuteError:
        sMsg = str(arcpy.GetMessages(2))
        arcpy.AddError(sMsg)
    except:
        sMsg = str(trace())
        sMsg = "{} {}".format(sMsg, str(arcpy.GetMessages(2)))
        arcpy.AddError(sMsg)
    finally:
        if (oProcessor !=None):
            del oProcessor
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

