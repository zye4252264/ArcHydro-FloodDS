'''***********************************************************************************************
Tool Name:  ApConstructMosaicDS (SourceName=ApConstructMosaicDS.py)
Version:  ArcGIS 10.3
Author:  zye 2/2/2016 (Environmental Systems Research Institute Inc.)
ConfigFile: flooddsconfig.py located in the same place as source .py file. 
Required Arguments:
    (0) pWorkspace = arcpy.GetParameterAsText(0)
    (1) pFCRef (optional for spatialRef)
          
Description: Create mosaic dataset and add rasters to it.  
  
  1. find the 6 folders based on the location of the workspace:
    flooddsconfig.FDN_Depth, flooddsconfig.FDN_UWSE, flooddsconfig.FDN_WSE: flooddsconfig.HD_WSE,
    flooddsconfig.FND_G_Depth,flooddsconfig.FND_G_PFZone,flooddsconfig.FND_G_RWL
  2. Create 6 masicrasterdatasets (whose names come from the folders found in 1) in pWorkspace=FloodDS.gdb, 
  3. Add rasters from those 6 folders.
  4. Add fields to the mosaicdataset (PFStep, StreamID, PFDesc)
  5. Assigne the field values (from parsing the rasternames (e.g., d_0_r_40.tif)
Usage:  constructmosaicds.py pWorkspace pFCRef (optional for spatialRef)
***********************************************************************************************'''
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

""" Making the ApUniqueID table """
class ApConstructMosaicDS:
    #variables:
    def __init__(self):
        self.DebugLevel = 0
   

    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())

    #def execute(self, parameters, messages):
    def execute(self, pParentFolder, pFCRef):
        sOK = apwrutils.C_OK
        ds = time.clock()
        try:
            dFields = {flooddsconfig.FN_StreamID:'LONG', flooddsconfig.FN_STEP:'LONG',  
                       flooddsconfig.FN_FLDESC:'DOUBLE'}

            sCodeBLK = "def SetID(Name, iPosition):"
            sCodeBLK = sCodeBLK + "\n  try:"
            sCodeBLK = sCodeBLK + "\n    l = Name.split('_')"
            sCodeBLK = sCodeBLK + "\n    n = int(l[iPosition])"
            sCodeBLK = sCodeBLK + "\n  except:"
            sCodeBLK = sCodeBLK + "\n    n = -9"
            sCodeBLK = sCodeBLK + "\n  return n"

            exprStreamID = "SetID( !{}!, 3)".format(apwrutils.FN_NAME)
            exprPFStep = "SetID( !{}!, 1)".format(apwrutils.FN_NAME)
            exprPFDesc = "Index2HV(!{}!)".format(flooddsconfig.FN_STEP)
            pWorkspace = os.path.join(pParentFolder, "FP.gdb")
            #pParentFolder = os.path.dirname(pWorkspace)
            #(pRasterFolder, sExt) = os.path.splitext(pWorkspace)
            runName = os.path.basename(pParentFolder)
            #pRasterFolder = os.path.join(pParentFolder, runName)
            pRasterFolder = pParentFolder
            oDesc = arcpy.Describe( pFCRef)
            pSpRef = oDesc.spatialReference 
            
            dDS2FD = {flooddsconfig.FDN_Depth: flooddsconfig.HD_Depth,
                  flooddsconfig.FDN_DepthC: flooddsconfig.HD_Depth,
                  flooddsconfig.FDN_UWSE: flooddsconfig.HD_UWSE,
                  flooddsconfig.FDN_WSE: flooddsconfig.HD_WSE,
                  flooddsconfig.FND_G_Depth: flooddsconfig.HD_G_Depth, 
                  flooddsconfig.FND_G_PFZone:flooddsconfig.HD_G_PFZone,
                  flooddsconfig.FND_G_RWL:flooddsconfig.HD_G_RWL}

            arcpy.env.workspace = pWorkspace
            pHTable = os.path.join(pWorkspace, flooddsconfig.TB_HTable)
            arcpy.AddMessage(pHTable)
            sCodesBLKH = "dHV = {"
            with arcpy.da.SearchCursor(pHTable, [flooddsconfig.FN_HIndex, flooddsconfig.FN_HValue]) as rows:
                for row in rows:
                    try:
                        if(self.DebugLevel>0):  arcpy.AddMessage("{} {}".format(row[0],row[1]))
                        if(sCodesBLKH=="dHV = {"):
                            sCodesBLKH = "{}{}:{}".format(sCodesBLKH,row[0],row[1])
                        else:      
                            sCodesBLKH = "{},{}:{}".format(sCodesBLKH, row[0],row[1])

                    except:
                        arcpy.AddMessage(trace())
                        pass
            sCodesBLKH = sCodesBLKH + "}"
            sCodesBLKH = "{}\ndef Index2HV(iIndex):".format(sCodesBLKH)
            sCodesBLKH = "{}\n  try:".format(sCodesBLKH)
            sCodesBLKH = "{}\n    sVal = dHV[int(iIndex)]".format(sCodesBLKH)
            sCodesBLKH = "{}\n  except:".format(sCodesBLKH)
            sCodesBLKH = "{}\n    sVal = -0.001".format(sCodesBLKH)
            sCodesBLKH = "{}\n  return sVal".format(sCodesBLKH)

            arcpy.AddMessage(sCodesBLKH)

            lNames = []
            for sDSName in dDS2FD:
                ds = time.clock()                
                sPath = os.path.join(pRasterFolder, sDSName)
                if(os.path.exists(sPath)):                    
                    if(arcpy.Exists(sDSName)):
                        arcpy.Delete_management(sDSName)
                        sMsg = "Deleting the existed mosaic dataset {}".format(sDSName)
                        arcpy.AddMessage(sMsg)
                    sMsg = "Construct mosaic dataset for {}.".format(sDSName)
                    arcpy.AddMessage(sMsg)
                
                    arcpy.CreateMosaicDataset_management(pWorkspace, sDSName, pSpRef, 1, "8_BIT_UNSIGNED", "False Color Infrared", "#")
                    mdname = os.path.join(pWorkspace, sDSName)
                    rastype = "Raster Dataset"
                    inpath =  os.path.join(pRasterFolder, sDSName)
                    updatecs = "UPDATE_CELL_SIZES"
                    updatebnd = "UPDATE_BOUNDARY"
                    updateovr = "UPDATE_OVERVIEWS"
                    maxlevel = "2"
                    maxcs = "#"
                    maxdim = "#"
                    spatialref = "#"
                    if(sDSName.startswith("G_")==False): 
                        inputdatafilter = "*{}".format(flooddsconfig.Ext_R)   # "*.tif"
                    else:
                        inputdatafilter = "*"
                    subfolder = "NO_SUBFOLDERS"
                    duplicate = "EXCLUDE_DUPLICATES"
                    buildpy = "BUILD_PYRAMIDS"
                    calcstats = "CALCULATE_STATISTICS"
                    buildthumb = "NO_THUMBNAILS"
                    comments = "Mosaiced dataset for {}".format(sDSName)
                    forcesr = "#"
                
                    arcpy.AddRastersToMosaicDataset_management(
                         mdname,  rastype, inpath, updatecs, updatebnd, updateovr,
                         maxlevel, maxcs, maxdim, spatialref, inputdatafilter,
                         subfolder, duplicate, buildpy, calcstats, 
                         buildthumb, comments, forcesr)
                    sMDSFullName = os.path.join(pWorkspace, sDSName)
                    lNames.append(sMDSFullName)
                 
                    apwrutils.Utils.addFields(sDSName, dFields)
                    if(sDSName.startswith("G_")==False):
                        try:
                            arcpy.management.CalculateField(sDSName, "StreamID", exprStreamID, 'PYTHON', sCodeBLK)
                        except:
                            pass
                    try: 
                        arcpy.management.CalculateField(sDSName, flooddsconfig.FN_STEP, exprPFStep, 'PYTHON', sCodeBLK)                #"FPStep"
                        #sDSView = "{}V".format(sDSName)
                        #arcpy.MakeTableView_management(sMDSFullName, sDSView)
                        arcpy.management.CalculateField(sDSName, flooddsconfig.FN_FLDESC, exprPFDesc, 'PYTHON', sCodesBLKH)            #"FPDesc"
                    except:
                        pass
                    sMsg = "  Done.  ds={}".format(apwrutils.Utils.GetDSMsg(ds))
                    arcpy.AddMessage(sMsg)
                    rl = None
                    try:
                        rl = "TB{}".format(sDSName)
                        if(arcpy.Exists(rl)): arcpy.Delete_management(rl) 
                        rl = arcpy.management.MakeTableView(sDSName,rl, "{}=-9".format(flooddsconfig.FN_STEP))
                        arcpy.DeleteRows_management(rl)
                        if((flooddsconfig.debugLevel & 1)==1): 
                            sMsg = "  Deleting {} where {}".format(sDSName, "{}=-9".format(flooddsconfig.FN_STEP))
                            arcpy.AddMessage(sMsg) 

                    except arcpy.ExecuteError:
                        sMsg = str(arcpy.GetMessages(2))
                        sOK = sMsg
                        arcpy.AddError(sMsg)                    
                    except:
                        sOK = str(trace())
                    finally:
                        if(rl!=None):
                            del rl 
                
               
                                  
        except arcpy.ExecuteError:
            sMsg = str(arcpy.GetMessages(2))
            sOK = sMsg
            arcpy.AddError(sMsg)                    
        except:
            sOK = str(trace())
                

        if(sOK==apwrutils.C_OK):
            l = [sOK]
            l.extend(lNames)
            tReturns = tuple(l)
        else:
            arcpy.AddMessage(sOK)
            tReturns(sOK)

        return tReturns

                 
if __name__ == '__main__':
    #oProcessor = None
    try:
        debugLevel = 0
        pWorkspace = arcpy.GetParameterAsText(0)
        pFCRef = arcpy.GetParameterAsText(1) 
        ddt = time.clock()
        oProcessor = ApConstructMosaicDS()
        oProcessor.DebugLevel = flooddsconfig.debugLevel

        tReturns = oProcessor.execute(pWorkspace, pFCRef)       
        if(tReturns[0] == apwrutils.C_OK): 
            ii = 1
            for s in tReturns:
                if(s!=apwrutils.C_OK):
                    if ((flooddsconfig.debugLevel & 1) == 1) : arcpy.AddMessage("{} {}".format(ii, s))
                    ii = ii + 1
                    arcpy.SetParameterAsText(ii, s)
        else:
            arcpy.AddMessage(tReturns[0])
            #sFullFC = tReturns[1]
            #arcpy.AddMessage(sFullFC)
            #arcpy.SetParameterAsText((len(sys.argv)-2), sFullFC) 
         
    except arcpy.ExecuteError:
        print str(arcpy.GetMessages(2))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    except:
        print trace()
        arcpy.AddError(str(trace()))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    finally:
        if(oProcessor!=None):
            del oProcessor
        dt = datetime.datetime.now()
        print  ('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))


