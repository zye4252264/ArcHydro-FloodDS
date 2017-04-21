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


class ApMake3DLine:
    #variables:
    C_OK = 'OK'
    C_NOTOK = 'NOTOK'
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
    def execute(self, inLine2D, inRaster, pScratchWorkspace = None, inSmooth = 0):
    #def make3DLine(self, inLine2D, inRaster):
        """Create a 3D line named as [inLine2D]_3D with M=length, Z=inRaster.Value"""
        sOK = self.C_OK
        if(pScratchWorkspace!=None): arcpy.env.scratchWorkspace = pScratchWorkspace
                   
        pEditor = None
        outLine3D = None
        cellsize = arcpy.env.cellSize
        ds = time.clock()
        line3DName = "Line3D"
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
            pWorkspace = apwrutils.Utils.getWorkspace(inLine2D)
            arcpy.edit.Densify(inLine2D, 'DISTANCE', cellsize)
            line2DName = os.path.basename(inLine2D)
            line3DName = line2DName+"_3D"
            outLine3D = os.path.join(pWorkspace, line3DName)
            if(arcpy.Exists(outLine3D)):
                arcpy.Delete_management(outLine3D)
            ds = time.clock()
            arcpy.CreateFeatureclass_management(pWorkspace, line3DName, "POLYLINE", inLine2D, "ENABLED", "ENABLED", inLine2D)
            if((flooddsconfig.debugLevel & 1)==1): 
                arcpy.AddMessage("M-Enabled 3D lines: {} is created, dt={}".format(outLine3D,apwrutils.Utils.GetDSMsg(ds))) 
                ds = time.clock()
            
            #copy features record by record:
            oDesc = arcpy.Describe(outLine3D)
            pSpRef = oDesc.spatialReference
            FN_OID = oDesc.OIDFieldName
            r = arcpy.GetCount_management(inLine2D)

            nCnt = int(r[0])
            iCnt = 0
            nMod = nCnt/100
            if((nMod<1) or (nCnt < 100)): nMod = 1
            arcpy.SetProgressor('step', "Creating 3D Lines {}->{} with {} features".format(inLine2D, line3DName,nCnt), 0, nCnt, nMod) 
            iCnt = 0

            #pEditor = arcpy.da.Editor(pWorkspace)
            #pEditor.startEditing(False,False)  
            #typeFilter=0,1,2,4.  0: list all fields, 1: exclude OID, Shape_Length, Shape_Area etc. 2: exclude Shape, 4: exclude NonePrintable fields, e.g., BLOB."""
            lFields = apwrutils.Utils.listFieldNames(inLine2D, 3)
            lFields.insert(0,apwrutils.FN_ShapeAt)            
            #lFields = [apwrutils.FN_ShapeAt, apwrutils.FN_HYDROID, apwrutils.FN_NEXTDOWNID, apwrutils.FN_DRAINID, apwrutils.FN_FROMNODE, apwrutils.FN_TONODE]
            with arcpy.da.InsertCursor(outLine3D,lFields) as inRows:
                with arcpy.da.SearchCursor(inLine2D, lFields) as rows:
                    for row in rows:
                        if((iCnt % nMod)==0):
                            sMsg = "Processing: {} of {} recs in {}. dt={}".format(str(iCnt+1) , nCnt, inLine2D, apwrutils.Utils.GetDSMsg(ds))
                            arcpy.SetProgressorLabel(sMsg)
                            arcpy.SetProgressorPosition(iCnt+1)
                            ds = time.clock()
                        iCnt = iCnt+1
                        pPoint = arcpy.Point()
                        arrPoints = arcpy.Array()
                        pPointLast = None  
                        if(row[0]!=None):
                            #..Construct a line: pLine(x,y): x=math.sqrt(x*x+y*y),y=z
                            pLine = row[0]
                            pExt = pLine.extent
                            (xMin,yMin,xMax,yMax) = (pExt.XMin,pExt.YMin,pExt.XMax,pExt.YMax)
                            xMin = xMin - cellsize
                            yMin = yMin - cellsize
                            xMax = xMax + cellsize
                            yMax = yMax + cellsize
                            nCols = int((xMax - xMin)/cellsize)
                            nRows = int((yMax - yMin)/cellsize) 
                            arrRaster = Raster2NumpyArrayByExt(inRaster,xMin,yMin,nRows,nCols)
                            if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("{} dt={}".format(arrRaster.shape, apwrutils.Utils.GetDSMsg(ds)))
                            part = row[0].getPart(0)
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
                                        except:
                                            pass 
                                pPoint.M = dLeng
                                if(inSmooth==1):
                                    if(pPointLast==None):
                                        pPointLast = arcpy.Point()
                                        pPointLast.clone(pPoint) 
                                    else:
                                        if(pPoint.Z >= pPointLast.Z): pPoint.Z = pPointLast.Z 
                                        pPointLast.clone(pPoint)                                        
                                arrPoints.add(pPoint)
                                try:
                                    if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("OID:{} idx:{} PointIJ=[{},{}] Point:x y z m=[{:.2f} {:.2f} {:.2f} {:.2f}]".format(row[1],i,ii,jj,pPoint.X,pPoint.Y,pPoint.Z, pPoint.M))
                                except:
                                    pass

                        pLine = arcpy.Polyline(arrPoints,pSpRef,True,True)
                        inrow = list(row)
                        inrow[0] = pLine
                        inRows.insertRow(inrow)
            sMsg = "Processing: {} of {} recs in {}. dt={}".format(nCnt, nCnt, inLine2D, apwrutils.Utils.GetDSMsg(ds))
            arcpy.SetProgressorLabel(sMsg)
            arcpy.SetProgressorPosition(nCnt)
            if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage(sMsg)
            if((flooddsconfig.debugLevel & 1)==1): 
                arcpy.AddMessage("{} features added to {}, dt={}".format(iCnt, outLine3D, apwrutils.Utils.GetDSMsg(ds))) 
                ds = time.clock()

            if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage("Appending {} recs from {} to {}.  dt={}".format(iCnt, inLine2D, line3DName, apwrutils.Utils.GetDSMsg(ds)))
            ds = time.clock()
            #arcpy.edit.Densify(outLine3D, 'DISTANCE', cellsize)
            #if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage("Densifying {}.  dt={}".format(line3DName, apwrutils.Utils.GetDSMsg(ds)))
            #out3DName = line3DName
            #if(arcpy.Exists(out3DName)):
            #    arcpy.Delete_management(out3DName)
            
        except arcpy.ExecuteError:
            sOK = str(arcpy.GetMessages(2))
            arcpy.AddError(sOK)
        except:
            sOK = str(trace())
            arcpy.AddError(sOK)
        finally:   
            pass      
            #if(pEditor!=None):
            #    pEditor.stopEditing(True) 
        if(sOK==self.C_OK):
            tReturn = (sOK, outLine3D)
              
        else: 
            tReturn = (sOK)

        return tReturn
         

if(__name__=='__main__'):
    try:
        inStream = arcpy.GetParameterAsText(0)     #inStream
        inRaster = arcpy.GetParameterAsText(1)  #inDEM
        iSmooth = arcpy.GetParameterAsText(2)
        pFL3DLine = None
        try:
            iSmooth = int(iSmooth)
        except:
            iSmooth = 0

        if((flooddsconfig.debugLevel & 1)==1): 
            for i in range(0,len(sys.argv)-2):
                arcpy.AddMessage("arcpy.GetParameterAsText({})=>{}".format(i,arcpy.GetParameterAsText(i))) 
                            
        ddt = time.clock()
        oProcessor = ApMake3DLine()
        lResults = oProcessor.execute(inStream,inRaster, inSmooth=iSmooth)
        if(lResults[0]== oProcessor.C_OK) :
            pFL3DLine = lResults[1]  
            #pFL3DLine = arcpy.management.MakeFeatureLayer(pFC3DLine, line3DName)        
        else:
            arcpy.AddMessage("No Delta H is specified.")
         
    except arcpy.ExecuteError:
        arcpy.AddError(str(arcpy.GetMessages(2)))
    except:
        arcpy.AddError(str(trace()))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    finally:
        if(pFL3DLine!=''):
            arcpy.SetParameterAsText(3, pFL3DLine)
        #del oProcessor
        dt = datetime.datetime.now()
        print ( 'Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

