"""  Create a 3DLine from a 2DLine taking into the consideration of the Zs in junctions and river order  """
#.. D:\10Data\AAAAA\aaa.gdb\Layers\DrainageLine D:\10Data\AAAAA\Layers\fillgrid10
#.. D:\10Data\AAAAA\AAA.mxd
#.. FullDataset: D:\10Data\TXDEM\FP.gdb, D:\10Data\TXDEM\TXDEM.mxd  FPRiver ocdemp[7224,3034], 
import sys 
import os 
import time 
import datetime
import math 
import numpy

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

class RiverOrderType:
    NO_Computation = -1
    PU_Order = 0      #Processing Unit Order, whenever 2 (or more) streams meet, the downstream stream = max_upstream_order + 1
    Strahler = 1      #Horton/Strahler 
    Shreve   = 2      #Shreve


def GetPointIJ(dXMin,dYMin,pPoint, dCellSize):
    """Return col,row indexes of a given pPoint.
       note: when using the i,j=[col,row] to retrive a value from a numpyArray=numpy.flipud(arcpy.RasterToNumPyArray(inRaster,nodata_to_value=0)), 
       value = numpyArray[j][i]=
    """
    tReturn = ()
    i = -1
    j = -1
    try:
        i = int((pPoint.X - dXMin) / dCellSize)
        j = int((pPoint.Y - dYMin) / dCellSize)
    except:
        pass
    tReturn = (i,j)
    return tReturn

def Raster2NumpyArray(inRaster):
    rasterArrayBotLeft = numpy.array([])
    try:
        oDesc = arcpy.Describe(inRaster)
        #coordinates of the lower left corner
        xMin = oDesc.extent.XMin
        yMin = oDesc.extent.YMin

        # Cell size, raster size
        meanCellHeight = oDesc.MeanCellHeight
        meanCellWidth = oDesc.MeanCellWidth
        nRows = oDesc.Height   #rows
        nCols = oDesc.Width     #cols
        llPoint = arcpy.Point(xMin,yMin)   #LowerLeftPoint
        ##Raster conversion to NumPy Array
        #create NumPy array from input rasters 
        rasterArrayTopLeft = arcpy.RasterToNumPyArray(inRaster,llPoint, nCols, nRows, nodata_to_value=0 )
        rasterArrayBotLeft = numpy.flipud(rasterArrayTopLeft)
        #inRasterFullArray = numpy.dstack((inRasterCoordinates, inRasterArray.T))
    except:
        rasterArrayBotLeft = numpy.array([])
        arcpy.AddMessage(trace())

    return rasterArrayBotLeft

def Raster2NumpyArrayByExt(inRaster, xMin,yMin,nRows,nCols):
    rasterArrayBotLeft = numpy.array([])
    try:
        llPoint = arcpy.Point(xMin,yMin)   #LowerLeftPoint
        ##Raster conversion to NumPy Array
        #create NumPy array from input rasters 
        rasterArrayTopLeft = arcpy.RasterToNumPyArray(inRaster,llPoint, nCols, nRows, nodata_to_value=0 )
        rasterArrayBotLeft = numpy.flipud(rasterArrayTopLeft)
        #inRasterFullArray = numpy.dstack((inRasterCoordinates, inRasterArray.T))
    except:
        rasterArrayBotLeft = numpy.array([])
        arcpy.AddMessage(trace())

    return rasterArrayBotLeft

#..Requiring each River has HydroID, NextDownID populated.
class ApRiver3D:
    MissingZValue = -9999
    #..Method starts with lower case word, property, starts with Upcase word.
    #  pRiverIn = row of the line2D 
    def __init__(self, pRiverIn, iShapeField, iHydroIDField, iNextIDField, iROIDField, iPassIDField):
        self.DebugLevel = 0
        self.River = list(pRiverIn)    #..Turn the tuple into list so that it can be updated. 
        self.ShapeField = iShapeField 
        self.HydroIDField = iHydroIDField
        self.NextDownIDField = iNextIDField
        self.ROIDField = iROIDField
        self.PASSIDField = iPassIDField
        self.UpRiverHIDs = []    # holdes list of upstream river's HYDROIDs.
        self.HydroID = self.River[self.HydroIDField]
        self.NextDownID = self.River[self.NextDownIDField]
        self.IsDone = False 
        self.IsHead = False
        self.LastPointZ = apwrutils.C_MissingValue 

    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())
    
    #def LastPointZ(self):
    #    if(self._lastPointZ==self.MissingZValue):
    #        try:
    #            pLine3D = self.River[self.ShapeField]
    #            if (pLine3D !=None):
    #                self._lastPointZ = pLine3D.lastPoint.Z 
    #            return self._lastPointZ

    #        except:
    #            self._lastPointZ==self.MissingZValue
    #    else:
    #        return self._lastPointZ
                 
    def canProcess(self, lDoneHIDs):
        bCantProcess = False 
        if(self.IsHead==True):
            bCanProcess = True
        else:
            bCanProcess = True  
            for hid in self.UpRiverHIDs:
                if((hid in lDoneHIDs)==False):
                    bCanProcess = False 
                    break 
        return bCanProcess
    
    """ Create 3DLine, pRaster=Raster whose value will be used as the Z value  
        lApRivers = list of ApRivers, used to check an ApRiver's tonode's Z value, when bCheckUpStreamZ = True
        iSmoothing = 1, make sure the downstream vertex Z is <= upstream vertex Z, i.e., monotone decreasing. 
        This method also populates the self.LastPointZ 
    """                
    def construct3DLine(self, pRaster, lApRivers, cellsize = -1, bCheckUpStreamZ=True, iSmoothing = 0, iRiverOrderType = RiverOrderType.PU_Order):
        pPoint = arcpy.Point()
        arrPoints = arcpy.Array()
        pPointLast = None  
        pLine3D = None 
        ds = time.clock()
        try:
            pLine = self.River[self.ShapeField]
            if(pLine!=None):
                if(self.IsHead==True):
                    self.River[self.ROIDField] = 1

                if(cellsize<0):
                    dem = arcpy.sa.Raster(pRaster)
                    cellsize = dem.meanCellWidth
                #..Construct a line: pLine(x,y): x=math.sqrt(x*x+y*y),y=z
                pExt = pLine.extent

                (xMin,yMin,xMax,yMax) = (pExt.XMin,pExt.YMin,pExt.XMax,pExt.YMax)
                xMin = xMin - cellsize
                yMin = yMin - cellsize
                xMax = xMax + cellsize
                yMax = yMax + cellsize
                nCols = int((xMax - xMin)/cellsize)
                nRows = int((yMax - yMin)/cellsize) 
                arrRaster = Raster2NumpyArrayByExt(pRaster,xMin,yMin,nRows,nCols)
                if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("{} dt={}".format(arrRaster.shape, apwrutils.Utils.GetDSMsg(ds)))
                iROIDMax = 0
                part = pLine.getPart(0)
                for i, p in enumerate(part):    # the value p==part[i] 
                    pPoint = arcpy.Point()
                    if(i==0): 
                        dLeng = 0.0
                    else:
                        dLeng = dLeng + math.sqrt((part[i].X-part[i-1].X)*(part[i].X-part[i-1].X)+(part[i].Y-part[i-1].Y)*(part[i].Y-part[i-1].Y))
                    pPoint.X = p.X
                    pPoint.Y = p.Y
                    if(len(arrRaster)!=0):
                        (ii,jj) = GetPointIJ(xMin,yMin,pPoint,cellsize)
                        if(ii>=0):
                            try:
                                pPoint.Z = float(arrRaster[jj][ii])
                                if((bCheckUpStreamZ or iRiverOrderType>=0) and self.IsHead==False):
                                    #..make sure first point.Z <= upstream rivers' last point Z.                                    
                                    if(len(arrPoints)==0):
                                        zMin = pPoint.Z
                                        iROID = 0
                                        iROIDMax = 0
                                        for hid in self.UpRiverHIDs:
                                            try:
                                                ll = [o for o in lApRivers if o.HydroID == hid]
                                                if(len(ll)>0): 
                                                    pApUpLine = ll[0]
                                                    zMinT = pApUpLine.LastPointZ
                                                    if(zMinT < zMin):
                                                        zMin = zMinT 
                                                    iROID = pApUpLine.River[pApUpLine.ROIDField]
                                                    if(iRiverOrderType == RiverOrderType.Strahler):
                                                        if(iROIDMax==0):
                                                            iROIDMax = iROID 
                                                        else:
                                                            if(iROIDMax<iROID):
                                                                iROIDMax = iROID
                                                            else:
                                                                if(iROIDMax==iROID):
                                                                    iROIDMax = iROIDMax + 1
                                                    elif(iRiverOrderType == RiverOrderType.PU_Order):
                                                        if(iROIDMax==0):
                                                            iROIDMax = iROID 
                                                        else:
                                                            if(iROIDMax<iROID):
                                                                iROIDMax = iROID
                                                    else:
                                                        iROIDMax = iROIDMax + iROID

                                            except:
                                                sMsg =  "{}, {}".format(arcpy.GetMessages(2), trace())
                                                arcpy.AddMessage(sMsg) 
                                                pass
                                            
                                        if(iRiverOrderType==RiverOrderType.PU_Order):
                                            if(len(self.UpRiverHIDs)>1):
                                                iROIDMax = iROIDMax + 1 

                                        if(self.IsHead):    
                                            self.River[self.ROIDField] = 1
                                        else:
                                            self.River[self.ROIDField] = iROIDMax 
                                        pPoint.Z = zMin 
                            except:
                                pass 
                    pPoint.M = dLeng
                    if(iSmoothing==1):
                        if(pPointLast==None):
                            pPointLast = arcpy.Point()
                            pPointLast.clone(pPoint) 
                        else:
                            if(pPoint.Z >= pPointLast.Z): pPoint.Z = pPointLast.Z 
                            pPointLast.clone(pPoint)                                        
                    arrPoints.add(pPoint)
                    self.LastPointZ = pPoint.Z 
                    try:
                        if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("OID:{} idx:{} PointIJ=[{},{}] Point:x y z m=[{:.2f} {:.2f} {:.2f} {:.2f}]".format(row[1],i,ii,jj,pPoint.X,pPoint.Y,pPoint.Z, pPoint.M))
                    except:
                        pass
                
                pLine3D = arcpy.Polyline(arrPoints,pLine.spatialReference,True,True)

        except:
            sMsg =  "{}, {}".format(arcpy.GetMessages(2), trace())
            arcpy.AddMessage(sMsg) 

        return pLine3D


class ApMake3DLineSystem:
    #variables:
    C_OK = 'OK'
    C_NOTOK = 'NOTOK'
    C_WLFld = 'WL_'
    FN_Elev = "Elev"
    FN_PASSID = "PASSID"

    def __init__(self):
        self.DebugLevel = 0
   
    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())

    #def execute(self, parameters, messages):
    def execute(self, inLine2D, inRaster, pFCLine3DOut, pScratchWorkspace = None, inSmooth = 0, iRiverOrderType = RiverOrderType.PU_Order):
        """Create a 3D line named as [inLine2D]_3D with M=length, Z=inRaster.Value"""
        if(self.DebugLevel>0): arcpy.AddMessage("Running {}. {}".format(self.thisFileName(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        sOK = self.C_OK
        if((pScratchWorkspace!=None) and (arcpy.Exists(pScratchWorkspace))):             
            arcpy.env.scratchWorkspace = pScratchWorkspace
        pEditor = None
        cellsize = arcpy.env.cellSize
        ds = time.clock()
        line3DName = "Line3D"
        lApRivers = []
        arcpy.env.overwriteOutput = True 
        #arcpy.env.addOutputsToMap=False
        sp = " "
        try:
            dem = arcpy.sa.Raster(inRaster)
            arcpy.env.cellSize = dem.meanCellWidth
            oDesc = arcpy.Describe(inRaster)
            cellsize = dem.meanCellWidth
            dXMin = oDesc.extent.XMin
            dYMin = oDesc.extent.YMin
            nRows = oDesc.Height    #rows
            nCols = oDesc.Width     #cols 
            if((flooddsconfig.debugLevel & 1)==1): 
                sMsg = "{} xMin,yMin:[{:.2f},{:.2f}] rows,cols:[{},{}] cellsize:{}".format(inRaster,dXMin,dYMin,nRows,nCols,cellsize)
                arcpy.AddMessage(sMsg)
            
            lDSNames = apwrutils.Utils.getFCNameWkSFDS(inLine2D)
            line2DName = lDSNames[0]
            pWorkspace = lDSNames[1]
            pFD = ""
            if(len(lDSNames)>2): pFD = lDSNames[2]

            arcpy.edit.Densify(inLine2D, 'DISTANCE', cellsize)
            line3DName = os.path.basename(pFCLine3DOut)
            pWorkspaceDS = os.path.dirname(pFCLine3DOut) 
            if(arcpy.Exists(pWorkspaceDS)==False):
                pWorkspaceDS = pWorkspace
                if(pFD!=""): pWorkspaceDS = os.path.join(pWorkspace, pFD) 
                    
                pFCLine3DOut = os.path.join(pWorkspaceDS, line3DName) 
            #line3DName = "{}_{}{}".format(line2DName,"3D",inSmooth)
            #pWorkspaceDS = pWorkspace
            #if(pFD!=""):
            #    pWorkspaceDS = os.path.join(pWorkspace, pFD)
            #    pFCLine3DOut = os.path.join(pWorkspace, pFD, line3DName)
            #else:
            #    pFCLine3DOut = os.path.join(pWorkspaceDS, line3DName)
            #if(arcpy.Exists(pFCLine3DOut)):
            #    arcpy.Delete_management(pFCLine3DOut)

            ds = time.clock()
            lFields = apwrutils.Utils.listFieldNames(inLine2D, 3)
            lFields.insert(0, apwrutils.FN_ShapeAt)             
            if(apwrutils.FN_RIVERORDER in lFields): 
                iROIDField = lFields.index(apwrutils.FN_RIVERORDER)
            else:
                arcpy.AddField_management(inLine2D, apwrutils.FN_RIVERORDER, "LONG")                  
                lFields.append(apwrutils.FN_RIVERORDER)
                iROIDField = lFields.index(apwrutils.FN_RIVERORDER) 
                
            iPassIDField = -1         
            if(self.FN_PASSID in lFields):
                iPassIDField = lFields.index(self.FN_PASSID) 
            else:
                arcpy.AddField_management(inLine2D, self.FN_PASSID, "LONG")  
                lFields.append(self.FN_PASSID) 
                iPassIDField = lFields.index(self.FN_PASSID)

            arcpy.CreateFeatureclass_management(pWorkspaceDS, line3DName, "POLYLINE", inLine2D, "ENABLED", "ENABLED", inLine2D)
            if((flooddsconfig.debugLevel & 1)==1): 
                arcpy.AddMessage("M-Enabled 3D lines: {} is created, dt={}".format(pFCLine3DOut,apwrutils.Utils.GetDSMsg(ds))) 
                ds = time.clock()
            
            #copy features record by record:
            oDesc = arcpy.Describe(inLine2D)
            pSpRef = oDesc.spatialReference
            FN_OID = oDesc.OIDFieldName
            r = arcpy.GetCount_management(inLine2D)

            nCnt = int(r[0])
            iCnt = 0
            nMod = nCnt/100
            if((nMod<1) or (nCnt < 100)): nMod = 1
            iCnt = 0
            #pEditor = arcpy.da.Editor(pWorkspace)
            #pEditor.startEditing(False,False)  
            #typeFilter=0,1,2,4.  0: list all fields, 1: exclude OID, Shape_Length, Shape_Area etc. 2: exclude Shape, 4: exclude NonePrintable fields, e.g., BLOB."""
            #lFields.insert(0, "SHAPE@XY")
            #array = arcpy.da.FeatureClassToNumPyArray(inLine2D, lFields)  
            #arcpy.AddMessage(len(array))
            
            #Populate the dRivers
            iShapeField = lFields.index(apwrutils.FN_ShapeAt)
            iHydroIDField = lFields.index(apwrutils.FN_HYDROID)
            iNextDownIDField = lFields.index(apwrutils.FN_NEXTDOWNID) 
            ds1 = time.clock()
            nCnt = 0
            arcpy.SetProgressor('step', "Collecting {} Lines to create 3DRiver in memory.".format(nCnt), 0, nCnt, nMod) 
            dds1 = time.clock()
            with arcpy.da.SearchCursor(inLine2D, lFields) as rows:
                for i, row in enumerate(rows):
                    if(i % nMod)==0:
                        sMsg = "Process {} of {} features. ddt={} ".format(i+1, nCnt,  apwrutils.Utils.GetDSMsg(dds1))
                        arcpy.SetProgressorLabel(sMsg)
                        #if(self.DebugLevel & 1)==1:  arcpy.AddMessage(sMsg) 
                        arcpy.SetProgressorPosition(i+1)
                        dds1 = time.clock()
                    pApRiver = ApRiver3D(row, iShapeField, iHydroIDField, iNextDownIDField, iROIDField, iPassIDField)
                    lApRivers.append(pApRiver) 
                    nCnt = i + 1
            sMsg = "Adding {} to 3DRiver in memory (lApRivers).  dt={}".format(nCnt, apwrutils.Utils.GetDSMsg(ds1))  
            arcpy.AddMessage("{}{}".format(sp*2,sMsg))  
            ds1 = time.clock()
            nHeadRivers = 0
            for pApRiver in lApRivers:
                hid = pApRiver.HydroID
                lHIDs = [o.HydroID for o in lApRivers if o.NextDownID == hid]
                if(len(lHIDs)==0):
                    pApRiver.IsHead = True 
                    nHeadRivers = nHeadRivers + 1
                pApRiver.UpRiverHIDs = lHIDs

            sMsg = "Updating the UpRiverIDs property to {} Rivers with {} Head rivers found  dt={}".format(nCnt, nHeadRivers, apwrutils.Utils.GetDSMsg(ds1))  
            arcpy.AddMessage("{}{}".format(sp*2,sMsg)) 
            ds1 = time.clock()
            #..Process the first level rivers:
            lDoneHIDs = []
            iPassMax = 5000
            bAllDone = True 
            iAdded = 0
            iPassFinal = 0
            ds1 = time.clock()
            iROIDMax = 0
            with arcpy.da.InsertCursor(pFCLine3DOut,lFields) as inRows:
                for iPass in range(0, iPassMax):
                    dds1 = time.clock()
                    for pApRiver in lApRivers:
                        if(pApRiver.IsDone==False):
                            if (pApRiver.canProcess(lDoneHIDs)==True):
                                pLine3D = pApRiver.construct3DLine(inRaster, lApRivers,cellsize, True, inSmooth, iRiverOrderType = iRiverOrderType)
                                inRow = list(pApRiver.River) 
                                inRow[pApRiver.ShapeField] = pLine3D 
                                pApRiver.River = inRow  
                                pApRiver.IsDone = True 
                                lDoneHIDs.append(pApRiver.HydroID)  
                                pApRiver.River[pApRiver.PASSIDField] = iPass
                                inRows.insertRow(inRow)
                                pApRiver.River[pApRiver.ShapeField] = None 
                                iAdded = iAdded + 1 
                    ts = "%.3f" % apwrutils.Utils.GetDS(dds1)
                    if(len(ts)<6):
                        ts = "[{}],{}".format(ts, sp*(6-len(ts)))
                    else:
                        ts = "[{}], ".format(ts)             
                    sMsg = "{}Pass {}: {} of {} records are processed. dt={}{}".format(sp*2, iPass, iAdded, nCnt, ts, apwrutils.Utils.GetDSMsg(ds1,""))
                    arcpy.AddMessage(sMsg)
                    #arcpy.AddMessage("Pass " + str(iPasss) + ": " + str(iProcessed) + " of " + str(nRows) + " records are processed, with " + str(len(dFeaturesDone)) + " recs having RiverOrder value assigned to 1.")# dt=")#+ & sDDt & " dtTotal=" & sDt)
                    bAllDone = True         
                    for pApRiver in lApRivers:
                        if(pApRiver.IsDone==False):
                            bAllDone = False 
                            break
                    if (bAllDone == True): 
                        iPassFinal = iPass
                        break 
            #..Update the FNZ and TNZ fields.
            dFields = dict()
            dFields.setdefault("FNZ", "DOUBLE")
            dFields.setdefault("TNZ", "DOUBLE")
            apwrutils.Utils.addFields(pFCLine3DOut, dFields)

            codefnz = """def GetFNZ(oShape):\n   return oShape.firstPoint.Z"""
            fnzExp = "GetFNZ(!Shape!)"
            codetnz = """def GetTNZ(oShape):\n   return oShape.lastPoint.Z"""
            tnzExp = "GetTNZ(!Shape!)"
            arcpy.CalculateField_management(pFCLine3DOut, "FNZ", fnzExp, "PYTHON_9.3", codefnz)
            arcpy.CalculateField_management(pFCLine3DOut, "TNZ", tnzExp, "PYTHON_9.3", codetnz)
            
        except arcpy.ExecuteError:
            sOK = "{}, {}".format(arcpy.GetMessages(2), trace())
            arcpy.AddError(sOK)
        except:
            sOK = str(trace())
            arcpy.AddError(sOK)
        finally:   
            pass      
            #if(pEditor!=None):
            #    pEditor.stopEditing(True) 
        if(sOK==self.C_OK):
            tReturn = (sOK, pFCLine3DOut)              
        else: 
            tReturn = (sOK)

        return tReturn
         

if(__name__=='__main__'):
    try:
        inStream = arcpy.GetParameterAsText(0)     #inStream
        inRaster = arcpy.GetParameterAsText(1)  #inDEM
        iSmooth = arcpy.GetParameterAsText(2)
        pFL3DLine = str(arcpy.GetParameterAsText(3))
        #pFL3DLine = None
        try:
            iSmooth = int(iSmooth)
        except:
            iSmooth = 0

        if((flooddsconfig.debugLevel & 1)==1): 
            for i in range(0,len(sys.argv)-2):
                arcpy.AddMessage("arcpy.GetParameterAsText({})=>{}".format(i,arcpy.GetParameterAsText(i))) 
                            
        ddt = time.clock()
        oProcessor = ApMake3DLineSystem()
        lResults = oProcessor.execute(inStream, inRaster, pFL3DLine, pScratchWorkspace=flooddsconfig.pScratchWorkspace, inSmooth=iSmooth, iRiverOrderType = RiverOrderType.PU_Order)
        pFL3DLine = ""
        if(lResults[0]== oProcessor.C_OK) :
            pFC3DLine = lResults[1]  
            pFL3DLine = os.path.basename(pFC3DLine)
            arcpy.MakeFeatureLayer_management(pFC3DLine, pFL3DLine)        
        else:
            arcpy.AddMessage("No Delta H is specified.")
         
    except arcpy.ExecuteError:
        arcpy.AddError(str(arcpy.GetMessages(2)))
    except:
        arcpy.AddError(str(trace()))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    finally:
        if(pFL3DLine!=""):
            arcpy.SetParameterAsText(3, pFL3DLine)
        #del oProcessor
        #dt = datetime.datetime.now()
        #print ( 'Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

