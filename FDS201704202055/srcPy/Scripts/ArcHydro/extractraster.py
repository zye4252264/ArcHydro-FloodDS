# D:\Data10\FloodDS\floodds.gdb\Layers\Catchment D:\Data10\FloodDS\Layers\fillgrid10 c:\temp 1 1
# D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro>python extractraster.py D:\Data10\FloodDS\floodds.gdb\Layers\Catchment D:\Data10\FloodDS\Layers\fillgrid10 c:\temp 2 2
import sys
import os
import time 
import datetime
import multiprocessing

import arcpy
import apwrutils


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

''' Extract raster based on polygon (ExtractByMask or ExtractByPolygon) 
    the code is written to test applying multiprocessing module extract gp operation. '''
class ApExtractRaster:
    #variables:
    def __init__(self):
        self.DebugLevel = 0

    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())

    def getWorkspace(self, pFL):
        oDesc = arcpy.Describe(pFL)
        ooDesc = arcpy.Describe(oDesc.path)
        if(ooDesc.dataType=='FeatureDataset'):
            sWorkspace = ooDesc.path
        else:
            sWorkspace = oDesc.path

        return sWorkspace
    
    """ execute(self, pPolyFC, pRaster, pFolder, opType=0:ByMask,1:ByPolygon) """
    def execute(self, pPolyFC, pRaster, pFolder, pScratchWorkspace = None, opType = 0):
        sOK = apwrutils.C_OK 
        arcpy.CheckOutExtension("Spatial")
        arcpy.env.overwriteOutput = True   
        oDesc = arcpy.Describe(pRaster)
        sName = oDesc.name 
        try:
            if(pScratchWorkspace!=None):
                arcpy.env.scratchWorkspace = pScratchWorkspace
                arcpy.AddMessage("pScratchWorkspace={}".format(pScratchWorkspace))
            ds = time.clock()
            iCnt = 0
            with arcpy.da.SearchCursor(pPolyFC, [apwrutils.FN_ShapeAt, apwrutils.FN_HYDROID]) as rows:
                for row in rows:
                    iCnt = iCnt + 1
                    oShp = row[0]
                    idPoly = row[1]
                    oExt = oShp.extent
                    arcpy.env.extent = oExt 
                    sOutName = os.path.join(pFolder, "R{}".format(idPoly))
                    sMsg = "" 
                    try:
                        if(opType==0):
                            idRaster = arcpy.sa.ExtractByMask(pRaster, oShp)
                            idRaster.save(sOutName)
                            sMsg = "{}. {} ExtractByMask({}, pPolygon)->{}".format(iCnt, idPoly, sName, sOutName)
                        else:
                            pnt = arcpy.Point()
                            pntArray = arcpy.Array()                            
                            nParts = oShp.partCount
                            lPoints = []
                            for i in range(0, nParts):
                                pnts = oShp.getPart(i)
                                for pnt in pnts:
                                    lPoints.append(pnt)
                                idRaster = arcpy.sa.ExtractByPolygon(pRaster, lPoints, 'INSIDE')    #, 'INSIDE')   #'OUTSIDE'
                                idRaster.save(sOutName)
                                sMsg = "{}. {} ExtractByPolygon({}, pPolygon(of {} vertices))->{}".format(iCnt, idPoly, sName, len(lPoints), sOutName)

                    except:
                        arcpy.AddMessage("id={} {}".format(idPoly, trace()))

                    arcpy.AddMessage("{}. dt={}".format(sMsg, apwrutils.Utils.GetDSMsg(ds)))
                    ds = time.clock()                    
        except arcpy.ExecuteError:
            sMsg = "{} {}".format(arcpy.GetMessages(2), trace())
            arcpy.AddError(sMsg)
        except:
            arcpy.AddMessage(trace())
            sOK = apwrutils.C_NOTOK

        return sOK, pFolder 
            
if __name__ == '__main__':
    #oProcessor = None
    try:
        debugLevel = 0
        inPolyFC = arcpy.GetParameterAsText(0)
        inRaster = arcpy.GetParameterAsText(1)
        pFolder = arcpy.GetParameterAsText(2)
        opType = arcpy.GetParameterAsText(3)
        nProcessors = arcpy.GetParameterAsText(4)
                
        arcpy.env.overwriteOutput = True
        try:
            opType = int(opType)
        except:
            opType = 0

        lProcesses = []
        try:
            nProcessors = int(nProcessors)
        except:
            nProcessors = 1
        

        arcpy.CheckOutExtension("Spatial")             

        ddt = time.clock()
        oProcessor = ApExtractRaster()
        oProcessor.DebugLevel = debugLevel
        #..makesure HYDROID exists and populated
        oDesc = arcpy.Describe(inPolyFC)
        oidFieldName = oDesc.oidFieldName
        sName = oDesc.name  
        if(apwrutils.Utils.FieldExist(oDesc, apwrutils.FN_HYDROID)==False):
            dFields = {apwrutils.FN_HYDROID :'LONG'}
            apwrutils.Utils.addFields(inPolyFC, dFields)
            srcField = "!{}!".format(oidFieldName)
            arcpy.CalculateField_management(inPolyFC, flooddsconfig.FN_HYDROID, -1, "PYTHON") 

        if(nProcessors==1):
            tReturns = oProcessor.execute(inPolyFC, inRaster, pFolder, None, opType)
            if(tReturns[0] == apwrutils.C_OK): 
                pFolder = tReturns[1]
                arcpy.AddMessage(pFolder)
                arcpy.SetParameterAsText(4, pFolder)
        else:
            pWorkspace = apwrutils.Utils.getWorkspace(inPolyFC) 
            nTotal = int(arcpy.GetCount_management(inPolyFC)[0])
            pStatTable = os.path.join(pWorkspace, "{}_Stats".format(sName))
            nMin = 0
            nMax = nTotal
            arcpy.Statistics_analysis(inPolyFC, pStatTable, [[oidFieldName,"MIN"],[oidFieldName,"MAX"]])
            with arcpy.da.SearchCursor(pStatTable, ["MIN_{}".format(oidFieldName),"MAX_{}".format(oidFieldName)]) as rows:
                for row in rows:
                    nMin = row[0]
                    nMax = row[1]

            #..Construct the whereclause 
            #..Select the Catchments
            #..Use catchment to select the lines,
            #..Use catchment to select the 10-85 points.
            nTotal = int(arcpy.GetCount_management(inPolyFC)[0])
            dCnt = int(nTotal/nProcessors) + 1 
            nLower = 0
            nUpper = 0
            for iProcess in range(nProcessors):
                nLower = 0 + dCnt*iProcess
                nUpper = nLower + dCnt
                sWhere = "{} > {} and {} <= {}".format(oidFieldName, nLower, oidFieldName, nUpper) 
                arcpy.AddMessage("sWhere={}".format(sWhere))
                pFLPoly = "{}{}".format(sName, iProcess) 
                arcpy.MakeFeatureLayer_management(inPolyFC, pFLPoly, sWhere) 
                
                pFolderPS = os.path.join(pFolder, "Proc{}".format(iProcess))
                wksName = "wks{}.gdb".format(iProcess )
                pwks = os.path.join(pFolderPS, wksName) 
                apwrutils.Utils.makeSureDirExists(pFolderPS)
                pwks = os.path.join(pFolderPS, wksName) 
                if(arcpy.Exists(pwks)==False):
                    arcpy.CreateFileGDB_management(pFolderPS, wksName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                    arcpy.AddMessage("FWKS: {} is created.".format(pwks))
                else:
                    arcpy.Delete_management(pwks)
                    arcpy.AddMessage("FWKS: {} is deleted.".format(pwks))  
                    arcpy.CreateFileGDB_management(pFolderPS, wksName)    #arcpy.CreateFileGDB_management(sCurDir, sWKS)
                    arcpy.AddMessage("FWKS: {} is created.".format(pwks))

                pFCPolyProc = os.path.join(pwks, "{}_{}".format(sName,iProcess )) 
                arcpy.CopyFeatures_management(pFLPoly, pFCPolyProc)  
                
                ds1 = time.clock()
                arcpy.AddMessage("running extractraster.execute({} {} {} {})".format(pFCPolyProc, inRaster, pFolder, pwks))
                params = (pFCPolyProc, inRaster, pFolder, pwks, opType) 
                oProcessor.DebugLevel = debugLevel
                p = multiprocessing.Process(target=oProcessor.execute, args=params)
                lProcesses.append(p) 
                p.start()              
            
            
        if(nProcessors>1):               
            for p in lProcesses:
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
             
         
    except arcpy.ExecuteError:
        print (str(arcpy.GetMessages(2)))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    except:
        print (trace())
        arcpy.AddError(str(trace()))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    finally:
        if(oProcessor!=None):
            del oProcessor
        arcpy.AddMessage("Total processing time dt={}".format(apwrutils.Utils.GetDSMsg(ddt)))
        dt = datetime.datetime.now()
        print  ('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))



