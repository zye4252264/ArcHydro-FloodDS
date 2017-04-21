'''***********************************************************************************************
Tool Name:  floodplainfrom3driverraster (SourceName=floodplainfrom3driverraster.py)
Version:  ArcGIS 10.0
Author:  zye 5/1/2014 (Environmental Systems Research Institute Inc.)
ConfigFile: 
    (0) Input workspace (Workspace)
    (1) WatershedName (or WatershedID as integer)
Optional Arguments:
              
Description:  
History:  Initial coding zye - 6/1/2014.

Usage:  floodplainfrom3driverraster.py <inRasterRiv3D> <inRasterElev> <inRWKS> <inStep> [<inMultiplier>] [<inCat>]
        # arcpy.GetParameterAsText(0)  - starting with 0, = argv[1].  if len(argv) == 7, max index used for GetParameterAsText=5.
        # when len(sys.argv)==7, MaxIndex for arcpy.GetParameterAsText = 5.
# C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\ThreeDR C:\10Data\FloodplainOP\Layers\fillgrid  20140105 C:\10Data\FloodplainOP\RUNONE\results 100 C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\layers\Catchment
# C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\ThreeDR C:\10Data\FloodplainOP\Layers\fillgrid 20140105 C:\10Data\FloodplainOP\RUNONE\results 100 
# C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\RST1171A C:\10Data\FloodplainOP\Layers\fillgrid 20140105 C:\10Data\FloodplainOP\RUNONE\results 100
# C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\RST1282 C:\10Data\FloodplainOP\Layers\fillgrid 20140105 C:\10Data\FloodplainOP\RUNONE\results 100  
# C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\RST1282 C:\10Data\FloodplainOP\Layers\fillgrid 1 C:\10Data\FloodplainOP\RUNONE\results 100 C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\layers\Catchment C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\Line3DZM1282 "1992-01-02 12:23:35"
# *********************************
#C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\RST1283 C:\10Data\FloodplainOP\Layers\fillgrid "2000-07-05 04:00:00" C:\10Data\FloodplainOP\RUNTWO\results 100 # C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\Line3DZM1283  
#C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\RST1283 C:\10Data\FloodplainOP\Layers\fillgrid "2000-07-05 04:00:00" C:\10Data\FloodplainOP\RUNTWO\results 100 # C:\10Data\FloodplainOP\FLOODPLAINOP.GDB\Line3DZM1283
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import xml.dom.minidom
import xml 

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
    #
    synerror = traceback.format_exc().splitlines()[-1]
    return line, filename, synerror

class ApFloodplainFrom3DRiverRaster:
    #variables:

    def __init__(self):
        self.dWatersheds = dict()
        self.lNames = []
        self.lNamesEx = []
        self.DebugLevel = 3

    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())


    #def execute(self, parameters, messages):
    def execute(self, inRasterRiv3D, inRasterElev, inStep, inRWKS, inFWKS, inRiv, inCat, inMultiplier = 100, inDeltaH = None, bConnectedOnly = True, pScratchWorkspace = None, nProcessors = 0): 
    #def ConstructFloodplain(self, inRasterRiv3D, inRasterElev, inStep, inRWKS, inFWKS, inRiv, inCat, inMultiplier = 100, inDeltaH = None): 
        ''' for a given inRiver3DRaster, construct the floodplain
        1. inRasterRiv3D - raster of river water level Z
        2. inRasterElev - DEM of the terrain 
        3. inStep - index of the waterlevel in a sequence of waterlevel, used to construct the output raster name (R+inStep)
        4. inCat - catchment used to limit the floodplain
        '''
        sOK = apwrutils.C_OK 
        dCatID2RivID = dict()
        pMask = ""
        flZoneTempRiver = ""
        flZoneDslv = ""
        flRiv = ""
        arcpy.AddMessage("{} {}".format(pScratchWorkspace,nProcessors) ) 
        if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("in floodplainfrom3driverraster: os.environ['TMP']={}, os.environ['TEMP']={}".format(os.environ['TMP'], os.environ['TEMP']))
        try:
            lRiverFlds = [apwrutils.FN_HYDROID, apwrutils.FN_DRAINID]
            with arcpy.da.SearchCursor(inRiv, lRiverFlds) as rows:
                for row in rows:
                    try:
                        dCatID2RivID.setdefault(row[1],row[0])    #Catchment.HYDROID->River.HYDROID
                    except:
                        pass

            if((flooddsconfig.debugLevel & 2)==2):
                for catid, rivid in iter(dCatID2RivID.items()):
                    arcpy.AddMessage("catID={} rivID={}".format(catid,rivid))

            if (not inStep): inStep=0
            arcpy.CheckOutExtension("Spatial")
            if((flooddsconfig.debugLevel & 1)==1):
                sMsg = "inRasterRiv3D={} \ninRasterElev={} \ninStep={} \ninRWKS={} \ninFWKS={} \ninRiv={} \ninCat={} \ninMultiplier={} \ninDeltaH={}".format(inRasterRiv3D,inRasterElev, inStep, inRWKS, inFWKS,inRiv,inCat,inMultiplier,inDeltaH)
                apwrutils.Utils.ShowMsg(sMsg)
            
            if(pScratchWorkspace==None):  
                scratch_wks = flooddsconfig.pScratchWorkspace      #   arcpy.env.scratchWorkspace  
                scratchFolder = flooddsconfig.pScratchFolder         #  arcpy.env.scratchFolder
                arcpy.env.scratchWorkspace = scratch_wks
            else:
                scratch_wks = pScratchWorkspace
                arcpy.env.scratchWorkspace = scratch_wks
                scratchFolder = arcpy.env.scratchFolder 

            #..arcpy.AddMessage("arcpy.env.scratchFolder={} scratch_wks={}".format(scratchFolder, pScratchWorkspace))
            if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("arcpy.env.scratchFolder={} scratch_wks={}".format(scratchFolder, pScratchWorkspace))
            if((flooddsconfig.debugLevel & 1)==1):
                sMsg = "arcpy.env.scratchFolder={}, scratch_wks={}".format(scratchFolder, scratch_wks)
                arcpy.AddMessage(sMsg)
            #if(scratch_wks==None):
            #    scratch_wks = os.path.join(scratchFolder, "scratch.gdb") 
            #    if(arcpy.Exists(scratch_wks)==False):
            #        arcpy.CreateFileGDB_management(scratchFolder, "scratch.gdb") 
            #    arcpy.env.scratchWorkspace = scratch_wks

            rasterDescribe = arcpy.Describe(inRasterElev)
            arcpy.env.snapRaster = rasterDescribe.catalogPath #SnapRaster
            arcpy.env.overwriteOutput = True

            bExists = apwrutils.Utils.makeSureDirExists(inRWKS)
            #filGrdInt = os.path.join(scratchFolder, arcpy.CreateUniqueName('filGrdInt', scratchFolder)) 
            cellSize = arcpy.GetRasterProperties_management(inRasterElev, "CELLSIZEX") 
            sr = arcpy.Describe(inRasterElev).spatialReference
            inMultiplier = int(inMultiplier)    
            filGrdX100 = arcpy.sa.Times(inRasterElev, inMultiplier) 
            river3DX100 = arcpy.sa.Times(inRasterRiv3D, inMultiplier) 
            filGrdInt = arcpy.sa.Int(filGrdX100)
            river3DInt = arcpy.sa.Int(river3DX100)
        
            #Holdes final raster results (depth grid)
            sDepthRWKS = os.path.join(inRWKS,flooddsconfig.FDN_Depth)   #Depth folder
            bExists = apwrutils.Utils.makeSureDirExists(sDepthRWKS)     #Depth folder
            sWseRWKS = os.path.join(inRWKS, flooddsconfig.FDN_WSE)      #WSE folder
            bExists = apwrutils.Utils.makeSureDirExists(sWseRWKS)       #WSE folder
            sUwseRWKS = os.path.join(inRWKS, flooddsconfig.FDN_UWSE)    #UWSE folder
            bExists = apwrutils.Utils.makeSureDirExists(sUwseRWKS)      #UWSE folder
            sGDepth = os.path.join(inRWKS, flooddsconfig.FND_G_Depth)
            bExists = apwrutils.Utils.makeSureDirExists(sGDepth)
            sGPFZone = os.path.join(inRWKS, flooddsconfig.FND_G_PFZone)
            bExists = apwrutils.Utils.makeSureDirExists(sGPFZone)
            sp = " "*2
            if(inCat!=None):
                #..Create floodzone featureclass to hold fp polygons for each river
                fcZoneRiver = os.path.join(inFWKS, flooddsconfig.LN_FPZoneRiver)
                if((flooddsconfig.debugLevel & 1) == 1):  arcpy.AddMessage("fcZoneRiver: {}".format(fcZoneRiver))
                if(arcpy.Exists(fcZoneRiver)==False):
                    arcpy.CreateFeatureclass_management(inFWKS, flooddsconfig.LN_FPZoneRiver, "POLYGON", None, None, None, sr)

                fieldsRiver = {flooddsconfig.FN_StreamID:'LONG', flooddsconfig.FN_STEP:'TEXT', 
                      flooddsconfig.FN_GridCode:'LONG', flooddsconfig.FN_DateCreated :'TEXT', 
                      flooddsconfig.FN_FLDESC:'DOUBLE', apwrutils.FN_HYDROCODE:'TEXT'}

                try:
                    ii = apwrutils.Utils.addFields(fcZoneRiver, fieldsRiver)
                    if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage("Processing inStep={}. (Fields added={}).".format(inStep,ii))
                   
                except arcpy.ExecuteError:
                    arcpy.AddError(str(arcpy.GetMessages(2)))
                lFieldsRiver = [apwrutils.FN_ShapeAt,flooddsconfig.FN_StreamID, flooddsconfig.FN_STEP, 
                    flooddsconfig.FN_GridCode, flooddsconfig.FN_DateCreated, flooddsconfig.FN_FLDESC, apwrutils.FN_HYDROCODE]
                
                if((flooddsconfig.debugLevel & 1)==1): 
                    sMsg = "Processing raster by each catchment contained in {}".format(inCat)     
                    arcpy.AddMessage(sMsg)
                #  makesure the temp Raster dir exist
                #inRWKSTemp = inRWKS
                #if(os.path.exists(arcpy.env.scratchFolder)): inRWKSTemp = arcpy.env.scratchFolder 
                sCatRWKS = os.path.join(inRWKS, "RCat")
                #sCatRWKS = os.path.join(inRWKSTemp, "RCat")
                bExists = apwrutils.Utils.makeSureDirExists(sCatRWKS)
                #    maskGrd = arcpy.sa.Polygon
                #apwrutils.Utils.ShowMsg("TobeImplemented....")
                oDesc = arcpy.Describe(inCat) 
                sOIDFld = oDesc.OIDFieldName
                lCatFlds = [apwrutils.FN_ShapeAt, sOIDFld, apwrutils.FN_HYDROID]
                rivID = 0
                sRasters = ""
                with arcpy.da.SearchCursor(inCat, lCatFlds) as rows:
                    for row in rows:
                        ddt = time.clock()
                        rivID = 0
                        catID = 0
                        try:        #try in row
                            iOID = row[lCatFlds.index(sOIDFld)]
                            catID = row[lCatFlds.index(apwrutils.FN_HYDROID)]
                            rivID = dCatID2RivID[catID]
                            oPoly = row[lCatFlds.index(apwrutils.FN_ShapeAt)]
                            oExt = oPoly.extent
                            #sWhere = "{}={}".format(sOIDFld, iOID) 
                            sWhere = "{}={}".format(apwrutils.FN_HYDROID, catID) 
                            #fl = arcpy.management.MakeFeatureLayer(inCat, "FL{}_{}".format(inStep,iOID), sWhere)
                            fl = "DH{}_{}".format(inStep, catID)
                            if(arcpy.Exists(fl)):
                                arcpy.Delete_management(fl) 
                            arcpy.MakeFeatureLayer_management(inCat, fl, sWhere)

                            #pMask = os.path.join(sCatRWKS, "d{}c{}".format(inStep,rivID))    #inStep, rivid, rivid is used instead of catid so that it is easier to id the cat/riv relation when debugging.
                            #pMask = os.path.join(sCatRWKS, "cat{}".format(iOID))
                            pMask = os.path.join(sCatRWKS, "cat{}".format(catID))
                            #arcpy.AddMessage("pMask={}  .exist={} {}".format(pMask, os.path.exists(pMask), arcpy.Exists(pMask)))
                            arcpy.env.extent = oExt
                            if(os.path.exists(pMask)==False):
                                if((flooddsconfig.debugLevel & 1)==1):  arcpy.AddMessage("PolygonToRaster_conversion -> {},  {} where {}".format(pMask, inCat, sWhere))
                                arcpy.PolygonToRaster_conversion(fl, sOIDFld, pMask, None, None, cellSize)
                                #flOutFile = arcpy.management.MakeRasterLayer(pMask, "flCat{}".format(rivID))
                            else:
                                #flOutFile = arcpy.management.MakeRasterLayer(pMask, "flCat{}".format(rivID))
                                 if((flooddsconfig.debugLevel & 8) == 8):  arcpy.AddMessage("{} already existed for catchment {}".format(pMask, sWhere))
                            
                            #arcpy.AddMessage("after: pMask={}  .exist={}  {}".format(pMask, os.path.exists(pMask), arcpy.Exists(pMask)))  
                            riv3D = arcpy.sa.ExtractByMask(river3DInt, fl)      #inRasterRiv3DRaster
                            ssOutFile = os.path.join(sCatRWKS, "d{}r{}".format(inStep,rivID))   #timestep, rivid
                            if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("  saving extracted riv3D to {} dt={}".format(ssOutFile, apwrutils.Utils.GetDSMsg(ddt)))
                            riv3D.save(ssOutFile)
                            riv3DInt = arcpy.sa.Int(riv3D)
                            riv3DIsNull = arcpy.sa.IsNull(riv3DInt)
                            riv3DSrc = arcpy.sa.Con(riv3DIsNull, riv3DInt, pMask, '"value" = 0')
                            rivNibble = arcpy.sa.Nibble(riv3DSrc, riv3DInt)
                            #..save the rivNibbleResults to the UWSE location
                            uwseNibble = arcpy.sa.Divide(rivNibble, float(inMultiplier))
                            #uwseNibble = arcpy.sa.ExtractByMask(uwseNibble, pMask) 
                            sUwseName = "{}_{}_{}_{}{}".format(flooddsconfig.HD_UWSE,inStep,flooddsconfig.HD_River,rivID, flooddsconfig.Ext_R)
                            uwseNibble.save(os.path.join(sUwseRWKS, sUwseName))
                            #..save the rivNibble to wse location.
                            wseNibble = arcpy.sa.Con(arcpy.sa.GreaterThan(uwseNibble, inRasterElev), uwseNibble, "#")
                            sWseName = "{}_{}_{}_{}{}".format(flooddsconfig.HD_WSE, int(inStep), flooddsconfig.HD_River, rivID, flooddsconfig.Ext_R)
                            wseNibble.save(os.path.join(sWseRWKS, sWseName))
                            #..Get the river depth and save the depth grid  '..ye, @1/28/2016 12:12:40 PM on ZYE1
                            sName = "{}_{}_{}_{}{}".format(flooddsconfig.HD_Depth,int(inStep),flooddsconfig.HD_River, rivID, flooddsconfig.Ext_R) 
                            fpDepth = arcpy.sa.Minus(rivNibble, filGrdInt)
                            fpDepth = arcpy.sa.Con(fpDepth, fpDepth, "#", '"value" >= 0')
                            fpDepthF = arcpy.sa.Divide(fpDepth, float(inMultiplier)) 
                            sDepthFile = os.path.join(sDepthRWKS,sName)
                            fpDepthF.save(sDepthFile)    # Depth grid.

                            #..Save the fpDepth
                            fpZone4PolyRiver = arcpy.sa.Con(fpDepth, 1, 0, '"value" >= 0'  ) 
                            fpZoneTempRiver = os.path.join(scratch_wks, "rz{}_{}".format(int(inStep),rivID)) 
                            #arcpy.RasterToPolygon_conversion(regiongroupg, tmpPolyFCInit, "NO_SIMPLIFY", "Value")  
                            try:
                                arcpy.RasterToPolygon_conversion(fpZone4PolyRiver, fpZoneTempRiver, "NO_SIMPLIFY" )
                                if(bConnectedOnly==True):
                                    sRivWhere = "{}={}".format(apwrutils.FN_HYDROID, rivID)
                                    flZoneTempRiver = "flrz{}_{}".format(int(inStep),rivID)
                                    flRiv = "flrv{}".format(rivID) 
                                    arcpy.MakeFeatureLayer_management(inRiv, flRiv, sRivWhere) 
                                    arcpy.MakeFeatureLayer_management(fpZoneTempRiver, flZoneTempRiver) 
                                    arcpy.SelectLayerByLocation_management(flZoneTempRiver, 'INTERSECT', flRiv)
                                    fpZoneTempDslv = os.path.join(scratch_wks, "fpr{}_{}".format(inStep, rivID))
                                    arcpy.Dissolve_management(flZoneTempRiver, fpZoneTempDslv, [flooddsconfig.FN_GridCode])
                                    sWhereGridCode = "{}>0".format(flooddsconfig.FN_GridCode)
                                    sDslvName = sName.split(".")[0]
                                    flZoneDslv = "{}DSLV".format(sDslvName) 
                                    arcpy.MakeFeatureLayer_management(fpZoneTempDslv, flZoneDslv, sWhereGridCode)
                                    try:
                                        fpDepthMasked = arcpy.sa.ExtractByMask(fpDepthF, flZoneDslv)  #   pMaskFC)   #flZoneDslv)
                                        pRaster = arcpy.sa.Plus(fpDepthMasked, 0.0)    
                                        pRaster.save(sDepthFile) 
                                    except:
                                        arcpy.AddMessage(trace())
                                        pass
                                        #arcpy.CopyRaster_management(ssOutFile, ssOutFileNew) 
                               
                                else:
                                    fpZoneTempDslv = os.path.join(scratch_wks, "fpr{}_{}".format(int(inStep), rivID))
                                    arcpy.Dissolve_management(fpZoneTempRiver, fpZoneTempDslv, [flooddsconfig.FN_GridCode])
                                if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("sName{}, fpZoneTempDslv={}".format(sName, fpZoneTempDslv) )
                                if(sRasters ==""):
                                    sRasters = sName
                                else:
                                    sRasters = sRasters + ";" + sName
                                #arcpy.Dissolve_management(fpZoneTempRiver, fpZoneTempDslv, [flooddsconfig.FN_GridCode])
                                sDateCreated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
                                with arcpy.da.InsertCursor(fcZoneRiver, lFieldsRiver) as inRows:
                                    #with arcpy.da.SearchCursor(fpZoneTempDslv, [apwrutils.FN_ShapeAt,flooddsconfig.FN_GridCode]) as prows:
                                    with arcpy.da.SearchCursor(flZoneDslv, [apwrutils.FN_ShapeAt,flooddsconfig.FN_GridCode]) as prows:
                                        for prow in prows:
                                            try:
                                                #fieldsRiver = {Shape@, flooddsconfig.FN_StreamID:'LONG', flooddsconfig.FN_STEP:'TEXT', 
                                                #      flooddsconfig.FN_GridCode:'LONG', flooddsconfig.FN_DateCreated :'TEXT', 
                                                #      flooddsconfig.FN_FLDESC:'TEXT', apwrutils.FN_HYDROCODE:'TEXT'}
                                                inRow = []
                                                oShp = prow[0]
                                                inRow.append(oShp)
                                                inRow.append(rivID)    #StreamID
                                                inRow.append(inStep)   #FPStep
                                                inRow.append(prow[1])  #GRidCode
                                                inRow.append(sDateCreated)  #DateCreated
                                                inRow.append(inDeltaH)   #FPDESC
                                                inRow.append(rivID)    #HYDROCODE
                                                inRows.insertRow(inRow)       
                                            except:
                                                arcpy.AddMessage(trace()) 
                                
                            except:
                                pass

                        except arcpy.ExecuteError:   #try in row for Cat
                            sMsg = str(arcpy.GetMessages(2))
                            arcpy.AddError("{} {}".format(sMsg, trace()))
                        except:
                            arcpy.AddWarning(arcpy.GetMessages(2))
                            sMsg = trace()
                            arcpy.AddMessage(sMsg)
                        finally:   ##try in row - per catchment
                            if(fl!=""):
                                arcpy.Delete_management(fl)

                            if(flZoneTempRiver!=""):
                                arcpy.Delete_management(flZoneTempRiver)
                            if(flZoneDslv!=""):
                                arcpy.Delete_management(flZoneDslv)

                            if(flRiv!=""):
                                arcpy.Delete_management(flRiv)
                            #sMsg = "Done, processing catchment {} (rivid={} catid={} dt={})".format(sWhere, rivID, catID, apwrutils.Utils.GetDSMsg(ddt))
                            sMsg = "{} (iStep,dh)=({},{}) Done, processing catchment {} (rivid={} catid={} dt={})".format(sp, int(inStep), inDeltaH, sWhere, rivID, catID, apwrutils.Utils.GetDSMsg(ddt)) 
 
                            arcpy.AddMessage(sMsg)
                if (nProcessors<=1) :            
                    try:
                        arcpy.env.extent = inRasterElev                      
                        arcpy.env.workspace = sDepthRWKS
                        arcpy.env.mask = inRasterElev
                    
                        # sDepthName = "{}{}{}".format(flooddsconfig.HD_Depth,inStep,flooddsconfig.Ext_R)  # did not work when .tif is used, it would produce a mosaic ds with Nodata being filled with -128 or 0.
                        sDepthName = "{}_{}".format(flooddsconfig.HD_Depth,int(inStep))
                        #arcpy.MosaicToNewRaster_management(sRasters, inRWKS, sDepthName, sr, "8_BIT_UNSIGNED", cellSize, "1", "LAST","FIRST")
                        #flDepthName = os.path.join(inRWKS, sDepthName)
                        arcpy.MosaicToNewRaster_management(sRasters, sGDepth, sDepthName, sr, "8_BIT_UNSIGNED", cellSize, "1", "LAST","FIRST")
                        flDepthName = os.path.join(sGDepth, sDepthName)

                        if(flooddsconfig.Ext_R!=""):
                             fpDepthF = arcpy.sa.SetNull(flDepthName, flDepthName, '"value" <= 0')
                             fpDepthF.save(flDepthName)
                        else:
                             fpDepthF = flDepthName
                
                        if((flooddsconfig.debugLevel & 1)==1): 
                            sMsg = "mosaic raster depth grid: fpDepthF={}".format(fpDepthF)
                            arcpy.AddMessage(sMsg)

                    except arcpy.ExecuteError:   #try in row for Cat
                        sMsg = str(arcpy.GetMessages(2))
                        arcpy.AddWarning(sMsg)
                    except:
                        arcpy.AddWarning(arcpy.GetMessages(2))
                        sMsg = trace()
                        arcpy.AddMessage(sMsg)

                
                #fpDepth = arcpy.sa.Minus(flDepthName, filGrdInt)
                #if((flooddsconfig.debugLevel & 1)==1): 
                #    sMsg = "Construct fpDepth  {}".format(flDepthName) 
                #    arcpy.AddMessage(sMsg)

            else:
                 isNullGrd = arcpy.sa.IsNull(river3DInt)
                 nibSrc = arcpy.sa.Con(isNullGrd, river3DInt, "-99999", "Value = 0")
                 nibLevel = arcpy.sa.Nibble(nibSrc, river3DInt)  #, "ALL_VALUES") 
                 fpDepth = arcpy.sa.Minus(nibLevel, filGrdInt)
                 fpDepthF = arcpy.sa.Con(fpDepth, fpDepth, "#", '"value" >= 0')     #fpDepth>0, return fpDepth, else null.
            
            fpZoneName = flooddsconfig.LN_FPZone
            fcZoneRslt = os.path.join(inFWKS, fpZoneName)
            fpDepthRName = "{}_{}".format(flooddsconfig.LN_FPZone,int(inStep)) 
            fpRaster = os.path.join(sGPFZone, fpDepthRName)
            if(nProcessors<=1):
                if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage(fpDepthF)
                fpZone4Poly = arcpy.sa.Con(fpDepthF, 1, 0, '"value" >= 0'  )            
                fpZoneTemp = os.path.join(scratch_wks, "r" + str(int(inStep))) 
                arcpy.RasterToPolygon_conversion(fpZone4Poly, fpZoneTemp, "NO_SIMPLIFY")
        
                if(inRiv!=None):
                    #try to remove the floodplain polygons not connected with the inRiv
                    flZoneOnRiv = ""
                    try:
                        flZoneOnRiv = "flZoneOnRiv"    #Zone that overlay with river lines.
                        arcpy.MakeFeatureLayer_management(fpZoneTemp, flZoneOnRiv)    
                        arcpy.SelectLayerByLocation_management(flZoneOnRiv, "INTERSECT", inRiv)
                        #Connected Raster Area:
                        sRasterConn = os.path.join(scratchFolder, "C" + str(int(inStep)))
                        arcpy.PolygonToRaster_conversion(flZoneOnRiv, flooddsconfig.FN_GridCode, sRasterConn,"","",cellSize)
                        fpZone4Poly = arcpy.sa.Con(sRasterConn, fpZone4Poly)
                        fpZone4Poly = arcpy.sa.SetNull(fpZone4Poly, fpZone4Poly, '"value" = 0')
                        arcpy.RasterToPolygon_conversion(fpZone4Poly, fpZoneTemp, "NO_SIMPLIFY")
                    except:
                        arcpy.AddMessage("try to remove floodplain not intersecting with a river. {}".format(trace()))
                    finally:
                        if(flZoneOnRiv!=""):
                            arcpy.Delete_management(flZoneOnRiv)                     
                fpZoneTempDslv = os.path.join(scratch_wks, "FPD" + str(int(inStep)))
                arcpy.Dissolve_management(fpZoneTemp, fpZoneTempDslv, [flooddsconfig.FN_GridCode])
            
                if(arcpy.Exists(fcZoneRslt)==False):
                    arcpy.CreateFeatureclass_management(inFWKS, fpZoneName, "POLYGON", fpZoneTempDslv, None, None, sr)   
        
                oDesc = arcpy.Describe(fcZoneRslt)
                fields = {flooddsconfig.FN_FLDESC:'DOUBLE', flooddsconfig.FN_STEP:'LONG', 
                          flooddsconfig.FN_GridCode:'LONG', flooddsconfig.FN_DateCreated :'TEXT'}

                apwrutils.Utils.addFields(fcZoneRslt, fields)
                
                sDateCreated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
        
                shpFldName = apwrutils.Utils.GetShapeFieldName(fcZoneRslt)            
                lFieldsZR = [apwrutils.FN_ShapeAt,flooddsconfig.FN_STEP,flooddsconfig.FN_FLDESC,flooddsconfig.FN_GridCode, flooddsconfig.FN_DateCreated]
                lFieldsDslv = [apwrutils.FN_ShapeAt, flooddsconfig.FN_GridCode] 
                with arcpy.da.InsertCursor(fcZoneRslt, lFieldsZR) as inRows:
                    with arcpy.da.SearchCursor(fpZoneTempDslv,lFieldsDslv) as rows:
                        for row in rows:
                            try:
                                inRow = []
                                oShp = row[0]
                                inRow.append(oShp)
                                inRow.append(int(inStep))
                                inRow.append(inDeltaH)
                                inRow.append(row[lFieldsDslv.index(flooddsconfig.FN_GridCode)])
                                inRow.append(sDateCreated)
                                inRows.insertRow(inRow)       
                            except:
                                arcpy.AddMessage(trace())  
        
                # ExtractByMask - extract the fpZoneF (floodplain (depth) zone with in float)   
                fpDepthFExt = arcpy.sa.ExtractByMask(fpDepthF, fcZoneRslt)
                #sDepthRName = "{}{}{}{}".format(flooddsconfig.HD_Depth,inStep,flooddsconfig.HD_River,flooddsconfig.Ext_R)
                fpDepthFExt.save(fpRaster)
                #..Construct the Raster/FeatureLayer to send back to the calling program
                #flZone = arcpy.management.MakeFeatureLayer(fcZoneRslt, fpZoneName)
                #rlZone = arcpy.management.MakeRasterLayer(fpRaster, fpDepthRName) 

        except:
            sOK = trace()
            arcpy.AddMessage(sOK)
            
        finally:
            if((flooddsconfig.debugLevel & 1)==1):  arcpy.AddMessage("FloodplainFrom3DRiverRaster Cleaning up...")
            arcpy.ResetEnvironments()

        if(sOK == apwrutils.C_OK):
            tReturn = (sOK, fcZoneRslt, fpRaster)
        else:
            tReturn = (sOK)

        return tReturn
           
 
if __name__ == '__main__':
    try:
        # arcpy.GetParameterAsText(0)  - starting with 0, = argv[1].  if len(argv) == 7, max index used for GetParameterAsText=5.
        # when len(sys.argv)==7, MaxIndex for arcpy.GetParameterAsText = 5.
        if(len(sys.argv) < 5):
            apwrutils.Utils.ShowMsg("Usage: " + sys.argv[0] + " in3DRivRaster inRasterElevation inDeltaH outWorkspace  [inMultiplier=100] [inCatchment=None] [inRiver=None]")
        else:     
            inRasterRiv3D = arcpy.GetParameterAsText(0) 
            inRasterElev = arcpy.GetParameterAsText(1)
            inStep = arcpy.GetParameterAsText(2)
            inRWKS = arcpy.GetParameterAsText(3)
            inFWKS = arcpy.GetParameterAsText(4)
            inRiv = arcpy.GetParameterAsText(5)
            inCat = arcpy.GetParameterAsText(6)
            inMultiplier = arcpy.GetParameterAsText(7)
            inDeltaH = arcpy.GetParameterAsText(8)
            outFL = arcpy.GetParameterAsText(9)   #derived, FloodPlainZone Polygon
            outRL = arcpy.GetParameterAsText(10)  #derived, FloodPlainZone Raster (Depth)
            if(inDeltaH==None):
                inDeltaH = 10.0     #datetime.datetime.now()                
            try:
                inMultiplier = int(inMultiplier)
            except:
                inMultiplier = 100
            #ConstructFloodplain(self, inRasterRiv3D, inRasterElev, inStep, inRWKS, inFWKS, inRiv, inCat, inMultiplier = 100, inDeltaH = None): 
            oProcessor = ApFloodplainFrom3DRiverRaster()
            tReturn = oProcessor.execute(inRasterRiv3D, inRasterElev, inStep, inRWKS, inFWKS, inRiv, inCat, inMultiplier, inDeltaH, True ) 
            if(tReturn[0]==apwrutils.C_OK):
                fcZoneRslt =tReturn[1]
                fpRaster = tReturn[2]
                fpDepthRName = "{}_{}".format(flooddsconfig.LN_FPZone,inStep) 
                flZone = arcpy.management.MakeFeatureLayer(fcZoneRslt, flooddsconfig.LN_FPZone)   #fpZoneName)
                rlZone = arcpy.management.MakeRasterLayer(fpRaster, fpDepthRName) 
                arcpy.SetParameterAsText(9, flZone)   #fpZone polygon
                arcpy.SetParameterAsText(10, rlZone)  #fpZone Raster

    except arcpy.ExecuteError:
        sMsg = str(arcpy.GetMessages(2))
        arcpy.AddError(sMsg)
    except:
        arcpy.AddWarning(arcpy.GetMessages(2))
        sMsg = trace()
        arcpy.AddMessage(sMsg)
    finally:
        dt = datetime.datetime.now()
        print  ('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))  


