#apwrutils.py hydro.esri.com arcgis arcgis CacheMap
# new version
import os
import sys
import time
import datetime 
import math 
import tempfile
import re

import getpass
import arcpy
import apwrutils

C_OK = 'OK'
C_NOTOK = 'NOTOK'
C_MissingValue = -99999
C_MISSINGVALUE = -99999
C_LYRFILES='lyrfiles'
C_LASTCELLFDIR = -255
C_MapUnitMeter = 'Meter'
C_MapUnitFootUS = 'Foot_US'

FN_NEXTDOWNID = "NextDownID"
FN_HYDROID = "HydroID"
FN_DRAINID = "DrainID"
FN_GRIDID = "GridID"
FN_GridCode = "GridCode"
FN_SINKID = "SinkID"
FN_LINKID = "LinkID"
FN_TONODE = "To_Node"
FN_FROMNODE="From_Node"
FN_FEATUREID = "FeatureID"
FN_VARID = "VARID"

FN_SPLITID = "SplitID"
FN_ISSINK = "IsSink"
FN_OMITUP = "OmitUp"
FN_QCVALUE = "QCValue"
FN_FLOWDIR = "FlowDir"
FN_TSTIME = "TSTime" 
FN_TSVALUE = "TSValue"
FN_LASTID = "LastID"
FN_FILLELEV = "FillElev"
FN_LEVELELEV = "LevelElev"
FN_ShapeAtLength ="SHAPE@LENGTH"
FN_ShapeAt = "SHAPE@"
FN_ShapeAtXY = "SHAPE@XY"
FN_ShapeAtX = "SHAPE@X"
FN_ShapeAtY = "SHAPE@Y"
FN_ShapeAtZ = "SHAPE@Z"
FN_ShapeAtM = "SHAPE@M"
FN_ShapeAtJSON = "SHAPE@JSON"
FN_ShapeAtWKB = "SHAPE@WKB"
FN_ORIGLENGTH = "OrigLength"
FN_HYDROCODE = "HydroCode"
FN_LINEID = "LineID"
FN_NAME = "NAME"

FN_STRUCTTYPE = "StructType"
FNV_ST_AQUEDUCT="Aqueduct"
FNV_ST_Syphon="Syphon"
FNV_ST_Culvert="Culvert"   

FN_ACTIONTYPE = "ActionType"
FN_COMPSTATUS = "CompStatus"
FN_DISTAWAY = "DistAway"

FN_XID="XID"
FN_Z = "Z"
FN_H = "H"
FN_A = "A"
FN_P = "P"
FN_R = "R"
FN_B = "B"
FN_XS = "XS"
FN_Q = "Q"
FN_ManningN = "ManningN"
FN_S0 = "S0"
FN_RiverID = "RiverID"
FN_Zmax = "Zmax"
FN_Zmin = "Zmin"
FN_WSEHD = "WSE"
FN_StatModel = "StatModel"
FN_RIVERORDER = "RIVERORDER"

K_FN_INDEX = "_IDX"

LN_APUNIQUEID = "APUNIQUEID"

lPrintableTypes = ["OID","String","Float","Double","Short", "Long", "Date", "SmallInteger"]
lNonePrintableTypes = ["Geometry", "Blob", "Raster"]


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

class LinearConvertionFactors:
    def __init__(self):
       self.Meter2Feet = 3.281
       self.Meter2Centimeter = 100
       self.Meter2Mile = 3.281/5280.0
    

class RiverOrderType:
    PU_Order = 1
    Shreve  = 2
    Strahler = 4

    dName2Value = {"PU_Order" : 1, "Shreve" : 2, "Strahler" : 4}

#Debug args:  hydro.esri.com arcgissiteadmin arcgissiteadmin.2013 CacheMap
K_GraphicsPointFC = "GrfFCPoint"
K_GraphicsPolylineFC = "GrfFCLine"
K_GraphicsPolygonFC = "GrfFCPoly"

class LogMgr():    
    logFileName = ""
    logFile = None
    polygonFC = ""
    pointFC = ""
    polylineFC = ""
    sWorkspace = ""
    FN_TagMsg = "TagMsg"
    def addPoint(self, pPoint, sMsg):
        if (self.pointFC==""):
            sName = "FCPnt" + apwrutils.Utils.GetDateTimeString(10)
            oDesc = arcpy.Describe(pPoint)
            if (oDesc!=None): pSpRef = oDesc.spatialReference  
            self.createPointFC(self, arcpy.env.scratchGDB, sName, pSpRef)
            
            #self.pointFC = os.path.join(arcpy.env.scratchWorkspace, 
    def createLogPointFC(self, targetGDB = None, fcName="", spRef=None, bClearRecs = False):
        try:
            if(targetGDB==None):
                targetGDB = arcpy.env.scratchGDB
            if(fcName==""): fcName = K_GraphicsPointFC     # + apwrutils.Utils.GetDateTimeString(10)
            self.pointFC = os.path.join(targetGDB, fcName)
            if(arcpy.Exists(self.pointFC)==False):
                arcpy.CreateFeatureclass_management(targetGDB, fcName, "POINT", None, "DISABLED", "DISABLED", spRef)
                arcpy.AddField_management(self.pointFC, self.FN_TagMsg, "STRING", None, None, 255)
            else:
                if(bClearRecs==True):
                    arcpy.DeleteFeatures_management(self.pointFC)
        except arcpy.ExecuteError:
            arcpy.AddError(str(arcpy.GetMessages(2)))
        except:
            arcpy.AddError(str(trace()))
            arcpy.AddError(str(arcpy.GetMessages(2)))
        
    def createLogPolylineFC(self, targetGDB = None, fcName="", spRef=None, bClearRecs = False):
        try:
            #arcpy.AddMessage("Create line function is called")
            if(targetGDB==None):
                targetGDB = arcpy.env.scratchGDB
            if(fcName==""): fcName = K_GraphicsPolylineFC    #+ apwrutils.Utils.GetDateTimeString(10)
            self.polylineFC = os.path.join(targetGDB, fcName)
            if(arcpy.Exists(self.polylineFC)==False):
                arcpy.CreateFeatureclass_management(targetGDB, fcName, "POLYLINE", None, "DISABLED", "DISABLED", spRef)
                arcpy.AddField_management(self.polylineFC, self.FN_TagMsg, "STRING", None, None, 255)
                #arcpy.AddMessage("{} is created.".format(self.polylihneFC))
            else:
                #arcpy.AddMessage("{} already existed..".format(self.polylineFC))
                if(bClearRecs==True):
                    arcpy.DeleteFeatures_management(self.polylineFC)
        except arcpy.ExecuteError:
            arcpy.AddError(str(arcpy.GetMessages(2)))
        except:
            arcpy.AddError(str(trace()))
            arcpy.AddError(str(arcpy.GetMessages(2)))

    def createLogPolygonFC(self, targetGDB = None, fcName="", spRef=None, bClearRecs = False):
        try:
            if(targetGDB==None):
                targetGDB = arcpy.env.scratchGDB
                arcpy.AddMessage("Creating scratchGDB at {}".format(targetGDB))
            if(fcName==""): fcName = K_GraphicsPolygonFC     #+ apwrutils.Utils.GetDateTimeString(10)
            self.polygonFC = os.path.join(targetGDB, fcName)
            if(arcpy.Exists(self.polygonFC)==False):
                arcpy.CreateFeatureclass_management(targetGDB, fcName, "POLYGON", None, "DISABLED", "DISABLED", spRef)
                arcpy.AddField_management(self.polygonFC, self.FN_TagMsg, "STRING", None, None, 255)
            else:
                if bClearRecs:
                    arcpy.DeleteFeatures_management(self.polygonFC)
            arcpy.AddMessage("ScratchFeatureClass Polygon is created: {}".format(self.polygonFC)) 
        except arcpy.ExecuteError:
            arcpy.AddError(str(arcpy.GetMessages(2)))
        except:
            arcpy.AddError(str(trace()))
            arcpy.AddError(str(arcpy.GetMessages(2)))

    def addGraphicPoint(self, pPoint, sMsg):
        try:
            with arcpy.da.InsertCursor(self.pointFC, [apwrutils.FN_ShapeAt, self.FN_TagMsg]) as inRows:
                inRows.insertRow((pPoint, sMsg))

        except:
            pass

    def addGraphicPolyline(self, pPolyline, sMsg):
        try:
            with arcpy.da.InsertCursor(self.polylineFC, [apwrutils.FN_ShapeAt, self.FN_TagMsg]) as inRows:
                inRows.insertRow((pPolyline, sMsg))

        except:
            pass

    def addGraphicPolygon(self, pPolygon, sMsg):
        try:
            pWorkspace = apwrutils.Utils.getWorkspace(self.polygonFC)
            pEditor = arcpy.da.Editor(pWorkspace)
            pEditor.startEditing(False,False)
            try:
                with arcpy.da.InsertCursor(self.polygonFC, [apwrutils.FN_ShapeAt, self.FN_TagMsg]) as inRows:
                    inRows.insertRow((pPolygon, sMsg))

            except:
                arcpy.AddMessage(apwrutils.Utils.trace())
            finally:
                if(pEditor!=None):
                    pEditor.stopEditing(True)
        except:
            pass
                                       
    def openLogFile(self, sLogFileName, bAddDT=True):
        try:
            self.logFileName = sLogFileName
            self.logFile = None
            sMainFile, sExt = os.path.splitext(self.logFileName) 
            if(bAddDT==True):
                sDT = apwrutils.Utils.GetDateTimeString(14)
                sMainFile = sMainFile + sDT
         
            if(sExt==''):                              
                sExt = ".log"
    
            self.logFileName = sMainFile + sExt
            self.file = open(self.logFileName, "w")
            self.file.write("log file opened at " + str(datetime.datetime.now) + "\n" )
        except:
            arcpy.AddMessage("openLogFile: {}".format(trace()))
                               
    def openLogFileAtTempLocation(self, sFileName = None):
        try:
            if(sFileName == None):
                sFileName = "Ap"   #.format(apwrutils.Utils.GetDateTimeString())
            
            tmpDir = tempfile.gettempdir()  # "C:\Temp"
            tmpDir = os.path.dirname(tmpDir) 
            tmpDir = os.path.join(tmpDir, "LogFiles")
            if(os.path.exists(tmpDir)==False):
                apwrutils.Utils.makeSureDirExists(tmpDir) 
            sLogFileName = os.path.join(tmpDir, sFileName)
            arcpy.AddMessage("in openLogFileAtTempLocation, LogFileName={}".format(sLogFileName)) 
            self.openLogFile(sLogFileName, bAddDT=True) 
        except:
            arcpy.AddWarning("openLogFileAtTempLocation: {}".format(trace()))
                  
    #def __init__(self, filename=None):
    
    def logInfo(self, sMsg):
        self.file.write(sMsg + "\n")

    def close(self):
        self.file.close()
#Global Functions

class Utils:
    ## adding a static _pLog so that addgraphicline, polygon, point etc can be easily called, as long as the _pLog got cleanup properly.
    _pLog = None 
    @staticmethod
    def pLog():
        if(Utils._pLog==None):
            Utils._pLog = apwrutils.LogMgr()
        return Utils._pLog 

    @staticmethod
    def GetUserTempDir():
        sTempDir = tempfile.gettempdir()
        sTempDir = sTempDir.lower()
        if(sTempDir.endswith("temp")==False):
            sTempDir = os.path.dirname(sTempDir)
        
        return sTempDir
    
    @staticmethod
    def getcmdargs(l):
        """ print out command arguments so that it can be used to run at the command line 
            zye 8:38 AM 2/8/2017 @zye10 
        """
        sMsg = ""
        for i in range(len(l)):
            if(i==0): 
                sMsg=l[0]
            else:
                sMsg = "{} {}".format(sMsg, l[i])
        return sMsg    
    @staticmethod
    def getFilePathExtName(pFile):
        """ for a given pFile = "c:\temp\aaa.txt" returns (c:\temp, aaa, .txt)  """
        (fName, fExt) = os.path.splitext(pFile) 
        fDir = os.path.dirname(fName) 
        fName = os.path.basename(fName) 

        return (fDir, fName, fExt) 


    @staticmethod
    def GetGDBFolder(pGDB):
        return os.path.dirname(pGDB)

    @staticmethod
    def GetLogDirFolder(parentDir, logFileDir = "log"):
        sLogDir = os.path.join(parentDir, logFileDir)
        try:
            apwrutils.Utils.makeSureDirExists(sLogDir)
        except:
            try:
                sLogDir = r"c:\temp\logFiles"
                apwrutils.Utils.makeSureDirExists(sLogDir)
            except:
                sLogDir = r"c:\temp\log"
        return sLogDir


    @staticmethod
    def GetLogDir(pFL, logFileDir = "log"):
        sLogDir = ""
        try:
            pGDB = apwrutils.Utils.getWorkspace(pFL)
            sDir = os.path.dirname(pGDB)
            sLogDir = os.path.join(sDir, logFileDir)
            apwrutils.Utils.makeSureDirExists(sLogDir)
        except:
            try:
                sLogDir = r"c:\temp\logFiles"
                apwrutils.Utils.makeSureDirExists(sLogDir)
            except:
                sLogDir = r"c:\temp\log"

        return sLogDir
        

    @staticmethod
    def GetFunctionName(func):
        return func.__name__

    @staticmethod
    def GetThisFileName():
        import inspect
        return inspect.getfile(inspect.currentframe())

    @staticmethod
    def GetThisDir():
        import inspect 
        return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))     
    
    @staticmethod
    def trace():
        import traceback, inspect
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        # script name + line number
        line = tbinfo.split(", ")[1]
        filename = inspect.getfile(inspect.currentframe() )
        # Get Python syntax error
        #
        synerror = traceback.format_exc().splitlines()[-1]
        return line, filename, synerror

    @staticmethod
    def ListFieldName(table, wildcard=None, fieldtype=None):
        fields = arcpy.ListFields(table, wildcard, fieldtype)
        nameList = []
        for field in fields:
            nameList.append(field.name)
        return nameList
  
    @staticmethod
    def GetOIDFieldName(inFC):
        sOIDName = arcpy.Describe(inFC).OIDFieldName
        return sOIDName

    @staticmethod
    def CopyFC(sSrc, sTrg, WhereClause=None):
        dt = time.clock()
        oFeatureLayer="MyTmpLayer"
        try:
            if arcpy.Exists(sTrg):
                arcpy.Delete_management(sTrg)
                print ("deleting " + sTrg)
            if arcpy.Exists(oFeatureLayer):
                arcpy.Delete_management(oFeatureLayer)
                ##OIDFLD = PyUtils.Utils.GetOIDField(sSrc)
                ##print OIDFLD
                arcpy.MakeFeatureLayer_management(sSrc, oFeatureLayer, WhereClause)
                arcpy.CopyFeatures_management(oFeatureLayer, sTrg)
        except:
            arcpy.AddMessage(trace())
      
        finally:
          return "see result in " + sTrg + " dt=" + str(time.clock() - dt)
          arcpy.Delete_management(oFeatureLayer)

  ##in_workspace="c:\92data\shapefiles"
  ##out_workspace="c:\temp\"
  ##clipfeatures="c:\92data\shapefiles\Texas.shp"
    @staticmethod
    def ClipFCs(in_workspace, out_workspace, clip_features):
        arcpy.env.workspace = in_workspace
        for fc in arcpy.ListFeatureClasses():
            output = os.path.join(out_workspace, fc)
            # Clip each input feature class in the list
            arcpy.Clip_analysis(fc, clip_features, output, 0.1)
      
    @staticmethod
    def GetShapeFieldName(inFC):
        shapeName = arcpy.Describe(inFC).shapeFieldName
        return shapeName
  
    @staticmethod
    def DescribeObject(sInObject):
        desc = arcpy.Describe(sInObject)
        if hasattr(desc, "name"):
            print ("Name:        " + desc.name)
        if hasattr(desc, "dataType"):
            print ("DataType:    " + desc.dataType)
        if hasattr(desc, "catalogPath"):
            print ("CatalogPath: " + desc.catalogPath)
        for child in desc.children:
            DescribeObject(child)
            ##print "\t%s = %s" % (child.name, child.dataType)

    @staticmethod
    def SpSearch(FC, WhereClause=None, SpatialRef=None, Fields=None, pGeom=None, ReturnShape=None):
        lR = list()
        rows = arcpy.SearchCursor(FC)
        ##OIDName = PyUtils.Utils.GetOIDFieldName(FC)
        ShpName = PyUtils.Utils.GetShapeFieldName(FC)
        for row in rows:
            ##nOID = row.getValue(OIDName)
            oShp = row.getValue(ShpName)
            if pGeom.disjoint(oShp)!= True:
                d = PyUtils.Utils.Row2Dict(FC, row, ReturnShape)
                lR.append(d)
                break
        del row
        del rows
        return lR

    @staticmethod
    def PadSapce(nSpace):
        sR = ''
        try:
            sR = nSpace * ' '

        except:
            sR = ' '

        return sR

    ##cur = arcpy
    @staticmethod
    def Row2Dict(inFC, row, ReturnShape):
        fields = arcpy.ListFields(inFC)
        sName = PyUtils.Utils.GetShapeFieldName(inFC)
        d = dict()
        bCanAdd = True
        for fld in fields:
            bCanAdd=False
            if (ReturnShape==True):
                bCanAdd=True
            else:
                if(fld.name!=sName):
                    bCanAdd = True
            if (bCanAdd==True):                
                d[str(fld.name)] = row.getValue(str(fld.name))
        return d
  
    @staticmethod
    def GetBaseNameSDE(sName):
        sNames = sName.split(".")
        return sNames[len(sNames)-1]

    #for a given c:\Fdir\Name.Ext returns (Name,Ext) 
    @staticmethod
    def GetBaseNameAndExt(sName):
        return os.path.splitext(os.path.basename(sName))

    @staticmethod
    def GetDS(ds):
        d = time.clock()
        dt = d - ds
        return dt
  
    @staticmethod
    def GetDSMsg(ds, format="%.3f seconds."):
        d = time.clock()
        dt = d - ds
        if(format==""):
            format = "%.2f seconds."
    
        return format % dt
    
    @staticmethod
    def ShowMsg(sMsg, ds=-1):
        if(ds>0):
            try:
                if(apwrutils.Utils.isNumeric(ds)):
                    sMsg = sMsg + " dt=" + apwrutils.Utils.GetDSMsg(ds)
            except:
                print ("ds msg err.")
        arcpy.AddMessage(sMsg)
        print (sMsg)

    @staticmethod
    def isNumeric(s):
        b = True
        try:  
            i = float(s)
        except:    # not numericelse:    # numeric
            b= False
        return b

    @staticmethod
    def GetKey(dic, val):
        #return  [k for k, v in dic.iteritems() if v == val][0]
        return  [k for k, v in iter(dic.items()) if v == val][0]

    @staticmethod
    def FieldExist(desc, sFieldName):
        bok = False
        try:
            sFieldName=sFieldName.lower()
            for field in desc.fields:
                sName = field.baseName
                sName = sName.lower()
                if(sName==sFieldName):
                    bok=True
                    break
        except:
            print(Utils.trace())

        return bok
    
    #lFields = [] - a list of field names.
    @staticmethod
    def AllFieldsExist(desc, lFields):
        bok = True
        for fld in lFields:
            sFldName = fld.lower()
            bFldFound = False
            for field in desc.fields:
                if(field.name.lower()==sFldName):   
                    bFldFound = True
                    break

            if(bFldFound==False):
                bok = False
                break
        return bok
         

    @staticmethod
    def FieldExistTB(tblName, sFieldName):
        desc = arcpy.Describe(tblName)
        return Utils.FieldExist(desc, sFieldName)


    @staticmethod
    def GetField(layer, sFieldName):
        oField = None
        try:
            desc = arcpy.Describe(layer.dataSource)
            sFieldName = sFieldName.lower()
            for field in desc.fields:
                if(field.name.lower()==sFieldName):
                    oField=field
                    break
        except:
            print(Utils.trace())
        return oField
    
    @staticmethod
    def GetLayerInMap(mxd, sLayerName):
        oLayer = None
        try:
            layers = arcpy.mapping.ListLayers(mxd)
            sLayerName=sLayerName.lower() 
            for layer in layers:
                if(layer.name.lower()==sLayerName):
                    oLayer=layer
                    break

        except:
            print(Utils.trace())

        return oLayer

    @staticmethod
    def GetWorkspaceFCs(sWorkspace, feature_type, fdName, iFCLevel, sNameFilter ="*", lFullNames = []): 
        #feature_type="All","Arc","Dimension","Polygon","Point","Polyline","Node","Region","Line","Edge","Junction","Line", etc.
        #fdName="*" - include all,
        #iFCLevel = 1 WorkspaceLevel, 2 = fc in FeatureDatasets, 4 = include tbl
        lReturns = []
        if(lFullNames==None): lFullNames = []
        arcpy.env.workspace = sWorkspace
        bCanAdd = True
        # FCLevel=2, get featureclasses in featuredataset
        if((iFCLevel & 2)==2):
            listDSs = arcpy.ListDatasets(fdName, "Feature")
            for ds in listDSs:
                listFCs = arcpy.ListFeatureClasses(sNameFilter,feature_type,ds)
                sDSName = os.path.join(sWorkspace, ds)
                for fc in listFCs:
                    lReturns.append(fc)
                    #lFullNames.append(os.path.join(
                    
        # FCLevel=1, get Workspace level featrue classes
        if((iFCLevel & 1)==1):
            listFCs = arcpy.ListFeatureClasses(sNameFilter, feature_type)
            for fc in listFCs:
                lReturns.append(fc)
        # FCLevel=4, get table type
        if((iFCLevel & 4)==4):
            listTbls = arcpy.ListTables(sNameFilter)
            for tbl in listTbls:
                lReturns.append(tbl)

        return lReturns

    @staticmethod
    def GetWorkspaceDatasets(sWorkspace, feature_type, fdName, iFCLevel, sNameFilter ="*"): 
        #fdName="*" - include all,
        #iFCLevel = 1 WorkspaceLevel, 2 = fc in FeatureDatasets, 4 = include tbl
        # return dictionary keyed on FcName
        dReturns = {}

        arcpy.env.workspace = sWorkspace
        bCanAdd = True
        # FCLevel=2, get featureclasses in featuredataset
        sPath = sWorkspace
        if((iFCLevel & 2)==2):
            listDSs = arcpy.ListDatasets(fdName, "Feature")
            for ds in listDSs:
                sPath = sWorkspace + "\\" + ds + "\\"
                listFCs = arcpy.ListFeatureClasses(sNameFilter,feature_type,ds)
                for fc in listFCs:
                    dReturns.setdefault(fc, sPath + fc)
                    #lReturns.append(fc)
        # FCLevel=1, get Workspace level featrue classes
        if((iFCLevel & 1)==1):
            listFCs = arcpy.ListFeatureClasses(sNameFilter, feature_type)
            sPath = sWorkspace + "\\"
            for fc in listFCs:
                dReturns.setdefault(fc,sPath + fc)
                #lReturns.append(fc)
        # FCLevel=4, get table type
        if((iFCLevel & 4)==4):
            listTbls = arcpy.ListTables(sNameFilter)
            sPath = sWorkspace + "\\"
            for tbl in listTbls:
                dReturns.setdefault(tbl, sPath + tbl)
                #lReturns.append(tbl)

        return dReturns

    @staticmethod
    def AddFieldToFCsOfFullPath(lFCs, field_name, field_type="TEXT", field_precision=None, field_scale=None, field_length=None, field_alias="", field_is_nullable=True, field_is_required=False, field_domain = None ):
        dReturn = dict()
        for fc in lFCs:
            try:
                if(arcpy.Exists(fc)):
                    desc = arcpy.Describe(fc)
                    if(Utils.FieldExist(desc,field_name)==False) :
                        arcpy.AddField_management(fc, field_name, field_type, field_precision, field_scale, field_length, field_alias, field_is_nullable, field_is_required, field_domain)
                        dReturn.setdefault(fc,1)
                    else:
                        dReturn.setdefault(fc,0)
            except arcpy.ExecuteError:
                dReturn.setdefault(fc,-1)
                arcpy.AddError(str(arcpy.GetMessages(2)))
        return dReturn    

    @staticmethod
    def AddFieldToFCs(sWorkspace, lFCs, field_name, field_type="TEXT", field_precision=None, field_scale=None, field_length=None, field_alias="", field_is_nullable=True, field_is_required=False, field_domain = None ):
        arcpy.env.workspace = sWorkspace
        dReturn = dict()
        for fc in lFCs:
            try:
                if(arcpy.Exists(fc)):
                    desc = arcpy.Describe(fc)
                    if(Utils.FieldExist(desc,field_name)==False) :
                        arcpy.AddField_management(fc, field_name, field_type, field_precision, field_scale, field_length, field_alias, field_is_nullable, field_is_required, field_domain)
                        dReturn.setdefault(fc,1)
                    else:
                        dReturn.setdefault(fc,0)
            except arcpy.ExecuteError:
                dReturn.setdefault(fc,-1)
                arcpy.AddError(str(arcpy.GetMessages(2)))
        return dReturn    
    
    @staticmethod
    def AddApUniqueIDTable(sWorkspace, bAddDefault):
        b=True
        try:
            arcpy.CreateTable_management(sWorkspace, "APUNIQUEID")
            arcpy.AddField_management("APUNIQUEID", "IDNAME", "TEXT","","",30) 
            arcpy.AddField_management("APUNIQUEID","LASTID","LONG")
            if(bAddDefault==True):
                try:
                    rows = arcpy.InsertCursor("APUNIQUEID")
                    row = rows.newRow()
                    row.setValue("IDNAME", "HYDROID")
                    row.setValue("LASTID", 0)
                    rows.insertRow(row)
                except:
                    pass
                finally:
                    if(rows!=None):
                        del rows 
                    if(row!=None):
                        del row
        except:
            b=False

        return b

    @staticmethod
    def TableExist(sWorkspace, TableName, lFields):
        """ check if a given table with specified fields (lFields) exists """
        bok = True;
        sWorkspaceOrg = arcpy.env.workspace
        try:
            if(sWorkspaceOrg!=sWorkspace):
                arcpy.env.workspace = sWorkspace

            if(arcpy.Exists(TableName)!=True):
                bok=False
            else:
                if((lFields!=None) and (len(lFields)>0)):
                    desc = arcpy.Describe(TableName)
                    bok = apwrutils.Utils.AllFieldsExist(desc,lFields)
        except:
            print (trace())
            arcpy.AddError(str(trace()))
            arcpy.AddError(str(arcpy.GetMessages(2)))      
            bok = False
        finally:
            if(sWorkspaceOrg!=sWorkspace):
                arcpy.env.workspace = sWorkspaceOrg

        return bok
    
    @staticmethod
    def GetLastID(sWorkspace, sUniqueIDTable = 'ApUniqueID', sWhere='IDNAME=\'HYDROID\''):
        """ Get the LASTID value of the ApUniqueID table """
        iHydroID = -1
        # workspace - Get the SDE's HydroID.
        row = None
        rows = None
        try:
            rows = arcpy.SearchCursor(sWorkspace + "\\" + sUniqueIDTable, sWhere)            
            for row in rows:
                iHydroID = int(row.getValue("LASTID"))
                break
             
            if(row!=None):
                del row
            if(rows!=None):
                del rows  
        except: 
            pass
                                    
        return iHydroID

    @staticmethod
    def query_yes_no(question, default="yes"):
        """Ask a yes/no question via raw_input() and return their answer.

        "question" is a string that is presented to the user.
        "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

        The "answer" return value is one of "yes" or "no".
        """
        valid = {"yes":True,   "y":True,  "ye":True,
                 "no":False,     "n":False}
        if default == None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("invalid default answer: '%s'" % default)

        while True:
            sys.stdout.write(question + prompt)
            choice = raw_input().lower()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' "\
                                 "(or 'y' or 'n').\n")


    @staticmethod 
    def GetDateTimeString(n = None):
        """ format a datetime to string """
        if(n==None):
            s = time.strftime("%Y%m%d%H%M%S", time.localtime())
        else:
            s = time.strftime("%Y%m%d%H%M%S", time.localtime())
            if((apwrutils.Utils.isNumeric(n)==True) and ((n>4) and (n<14))):
               s = s[0:n]
            else:
               s = s[0:14]
                
        return s

    @staticmethod 
    def GetDateTimeString2(d):
        """ format a datetime to string """
        return (d.strftime("%Y%m%d%H%M%S"))

    @staticmethod
    def GetDistance(p1,p2):
        """ get the distance between two points """
        return  math.sqrt((p1.X-p2.X)*(p1.X-p2.X)+(p1.Y-p2.Y)*(p1.Y-p2.Y))

    @staticmethod
    def GetPointIJ(xMin, yMax, pPoint, cellsize):
        """ get i,j index of the cell containing the pPoint """
        i = int((pPoint.X - xMin)/cellsize)
        j = int((yMax - pPoint.Y)/cellsize)
        p = arcpy.Point(i,j)
        return p
            
    @staticmethod
    def DescribeRaster(SnapRaster):
        """ describe a raster dataset """
        print ("Band Count:       %d" % desc.bandCount)
        print ("Compression Type: %s" % desc.compressionType)
        print ("Raster Format:    %s" % desc.format)
        STD = arcpy.GetRasterProperties_management(SnapRaster, "STD")
        elevSTD = STD.getOutput(0)
        print(elevSTD)
        MEAN = arcpy.GetRasterProperties_management(SnapRaster, "MEAN")
        elevMEAN = MEAN.getOutput(0)
        print("Mean=" + str(elevMEAN))
        CELLSIZE = arcpy.GetRasterProperties_management(SnapRaster, "CELLSIZEX")
        elevCELLSIZE = CELLSIZE.getOutput(0)
        print("CellSize=" + str(elevCELLSIZE))
        LEFT = arcpy.GetRasterProperties_management(SnapRaster, "LEFT")
        elevLEFT = LEFT.getOutput(0)
        print("LEFT="+ str(elevLEFT))
        BOTTOM = arcpy.GetRasterProperties_management(SnapRaster, "BOTTOM")
        elevBOTTOM = BOTTOM.getOutput(0)
        print("BOTTOM="+ str(elevBOTTOM))
        RIGHT = arcpy.GetRasterProperties_management(SnapRaster, "RIGHT")
        elevRIGHT = RIGHT.getOutput(0)
        print("RIGHT="+ str(elevRIGHT))
        TOP = arcpy.GetRasterProperties_management(SnapRaster, "TOP")
        elevTOP = TOP.getOutput(0)
        print("TOP="+ str(elevTOP))

    #A function that checks that the input JSON object
    #  is not an error object.    
    @staticmethod
    def assertJsonSuccess(data):
        obj = json.loads(data)
        if 'status' in obj and obj['status'] == "error":
            print ("Error: JSON object returns an error. " + str(obj))
            return False
        else:
            return True

    @staticmethod
    def makeSureDirExists(sPath):
        """ make sure a specified directory exists, if not create it. """
        bExists = False
        if not os.path.exists(sPath):
            os.makedirs(sPath)
        else:
            bExists = True

        return bExists

    @staticmethod
    def rmdir(sPath):
        """ remove a directory/folder """
        import shutil
        shutil.rmtree(sPath)

    @staticmethod
    def getFCNameWkSFDS(fc):
        """ given a fc, return a list[0]=Fc.aliasName, [1]=workspace, [2]=featureDataset 
            Note: the fc has to exist already.
        """
        l = []
        oDesc = arcpy.Describe(fc)
        sPath = oDesc.path
        sName = oDesc.name
        oDesc2 = arcpy.Describe(sPath)
        l.append(sName)
        if(oDesc2.dataType=="FeatureDataset"):
            sDS = oDesc2.name
            sWKS = oDesc2.path
            l.append(sWKS)
            l.append(sDS)
        else:
            sWKS = sPath
            l.append(sWKS)

        return l

    @staticmethod
    def getFCNameWkSFDS2(fc):
        """ given a fc, return a list[0]=Fc.aliasName, [1]=workspace, [2]=featureDataset 
            Note, fc does not have to exist but workspace, featureDataset etc has to exist.
        """
        l = []
        fds = None
        pWorkspace = os.path.dirname(fc)
        sName = os.path.basename(fc)  
        l.append(sName)
        try:
            oDesc = arcpy.Describe(pWorkspace) 
            if(oDesc.dataType=="FeatureDataset"):
                fds = os.path.basename(pWorkspace) 
                pWorkspace = os.path.dirname(pWorkspace)
            l.append(pWorkspace)
            l.append(fds) 
        except:
            arcpy.AddMessage(trace())
        return l

    
    @staticmethod
    def functionTimer(nCalls, func, *args):
        """ clock a function's running time """
        start = time.clock()
        if(nCalls<=0) : nCalls = 10000
        for i in range(nCalls):
            func(*args)
            return "running function " + func.__name__  + str(args) +" "  + str(nCalls) +  " times, dt=" + str(time.clock() - start)
         
    @staticmethod
    def getWorkspace(pFL):
        """ get a FeatureLayer's workspace """
        oDesc = arcpy.Describe(pFL)
        ooDesc = arcpy.Describe(oDesc.path)
        if(ooDesc.dataType=='FeatureDataset'):
            sWorkspace = ooDesc.path
        else:
            sWorkspace = oDesc.path

        return sWorkspace

    @staticmethod
    def getLayerFullName(pFL):
        try:
            sWorkspace = Utils.getWorkspace(pFL)
            sFullName=os.path.join(sWorkspace, os.path.basename(pFL))
        except:
            sFullName = pFL

        return sFullName


    @staticmethod
    def str2Bool(s):
        """ convert a string presentation to boolean (True or False) """
        return s.lower() in ("yes", "true", "t", "1")

    @staticmethod
    def setTargetLocation(targetpath,spref, targetFD = 'Layers'):

        sOK = apwrutils.C_OK
        try:
            #Check whether output path is valid
            isdb = False
            gdbpath=""

            if targetpath=="":
              arcpy.AddWarning("Targetpath is not set.")
              sOK = apwrutils.C_NOTOK
              return (sOK)
            
            if arcpy.Exists(targetpath)==False:
                arcpy.AddMessage(str(targetpath) + " does not exist.")
                #Check whether the path points to a database or a feature dataset
                for ext in ('.gdb', '.mdb', '.sde'):
                    if targetpath.lower().endswith(ext):
                        isdb=True
                        gdbpath = targetpath
                        #Check whether parent directory exists
                        parentpath = os.path.dirname(gdbpath)
                        if os.path.exists(parentpath ):
                            arcpy.AddWarning("Path " + str(parentpath ) + " does not exist.")
                            sOK = apwrutils.C_NOTOK
                            return (sOK)
                        else:
                            #Create geodatabase
                            arcpy.AddWarning("Creating output geodatabase " + str(gdbpath) + ".")
                            if targetpath.lower().endswith('.gdb'):
                                 arcpy.management.CreateFileGDB(parentpath, os.path.basename(gdbpath))
                            elif targetpath.lower().endswith('.mdb'):
                                 arcpy.management.CreatePersonalGDB(parentpath, os.path.basename(gdbpath))
                            else:
                                 sOK = apwrutils.C_NOTOK
                                 return (sOK)

                                           
                #Check whether this is a feature dataset
                if isdb ==False:
                    gdbpath=os.path.dirname(targetpath)
                    for ext in ('.gdb', '.mdb', '.sde'):
                        if gdbpath.lower().endswith(ext):
                            #Check whether the file exist
                            if arcpy.Exists(gdbpath):
                                arcpy.AddMessage("Feature Dataset " + str(targetpath) + " does not exist in database " + str(gdbpath) + ".")
                                #Create feature dataset
                                targetFD = os.path.basename(targetpath)
                                if((targetFD==None) or (targetFD=='')) : targetFD = "Layers"
                                arcpy.AddMessage("Creating feature dataset " + str(targetFD))
                                arcpy.management.CreateFeatureDataset(gdbpath,targetFD,spref)
                            else:
                                parentpath = os.path.dirname(gdbpath)
                                #Check whether the parent folder exist
                                if os.path.exists(parentpath)==False:
                                        arcpy.AddWarning("Path " + str(parentpath ) + " does not exist.")
                                        sOK = apwrutils.C_NOTOK
                                        return (sOK)
                                else:
                                    #Create geodatabase
                                    arcpy.AddMessage("Creating output geodatabase " + str(gdbpath) + ".")
                                    if gdbpath.lower().endswith('.gdb'):
                                        arcpy.management.CreateFileGDB(parentpath, os.path.basename(gdbpath))
                                    elif gdbpath.lower().endswith('.mdb'):
                                        arcpy.management.CreatePersonalGDB(parentpath, os.path.basename(gdbpath))
                                    else:
                                        sOK = apwrutils.C_NOTOK
                                        return (sOK)
                                    #Create feature dataset
                                    targetFD = os.path.basename(targetpath)
                                    if((targetFD==None) or (targetFD=='')) : targetFD = "Layers"
                                    arcpy.AddMessage("Creating feature dataset " + str(targetFD))
                                    arcpy.management.CreateFeatureDataset(gdbpath,targetFD,spref)

        except:
             sOK = apwrutils.C_NOTOK
        return sOK

    @staticmethod
    def getDefaultWorkspaces():

        targetpath = ""
        dbpath=""
        rasterpath=""

        try:

            #Set workspace using mxd is defined
            try:
                mxd=arcpy.mapping.MapDocument('CURRENT')
            except:
                mxd = None
            if mxd:
                #Get mxd path
                targetpath = mxd.filePath.lower()
                if targetpath!="":
                    targetpath = targetpath.replace(".mxd",".gdb")
                else:
                    workspace = arcpy.env.workspace  
                    targetpath = workspace                                 
                df = mxd.activeDataFrame
                dfname = df.name.strip()
                dbpath = targetpath
                filename,fileext = os.path.splitext(targetpath)
                if (fileext.lower() in ('.gdb', '.mdb', '.sde'))==False:
                    #Add AHDefault.gdb
                    targetpath = os.path.join(targetpath,'AHDefault.gdb')
                for ext in ('.gdb', '.mdb', '.sde'):
                    if targetpath.lower().endswith(ext):
                        targetpath = os.path.join(targetpath,dfname)
                        rasterpath =  os.path.join(os.path.dirname(dbpath),dfname)
            else:
                #no mxd - use default workspace
                #Get default workspace + Layers
                workspace = arcpy.env.workspace
                if workspace:
                    rasterpath = workspace
                    targetpath = workspace
                    dbpath = workspace
                    filename,fileext = os.path.splitext(targetpath)
                    if (fileext.lower() in ('.gdb', '.mdb', '.sde'))==False:
                        #Add AHDefault.gdb
                        targetpath = os.path.join(targetpath,'AHDefault.gdb')
                    for ext in ('.gdb', '.mdb', '.sde'):
                            if targetpath.lower().endswith(ext):
                                dfname = 'Layers'
                                targetpath = os.path.join(targetpath,dfname)
                                rasterpath = os.path.join(os.path.dirname(dbpath),dfname)
        except:
            pass

        return (targetpath,dbpath,rasterpath)

    @staticmethod
    def setRasterTargetLocation(outputfullpath):
         sOK = apwrutils.C_NOTOK
         try:
            #Check valid outworkspace and create if it does not exist
            outpath = os.path.dirname(outputfullpath)
            if arcpy.Exists(outpath)==False:
                filename,fileext = os.path.splitext(outpath)
                if (fileext.lower() in ('.gdb', '.mdb', '.sde'))==False:
                    parentpath =  os.path.dirname(outpath)
                    if arcpy.Exists(parentpath):
                        arcpy.AddMessage("Creating output directory " + outpath + ".")
                        os.makedirs(outpath)
                        sOK = apwrutils.C_OK
                else:
                    arcpy.AddWarning("Output location " + outpath + " does not exist.")
                    sOK = apwrutils.C_OK
            else:
                #Valid output raster path
                sOK = apwrutils.C_OK
         except:
             sOK = apwrutils.C_NOTOK
         return sOK


    @staticmethod
    def getTimeDifference(sDT1, sDT2):
        """ given two string date, sDT1, sDT2, returns deltaTime """
        if(":" in sDT1): 
            sFormat = "%Y-%m-%dT%H:%M:%S.%f"
        else:
            sFormat = "%Y-%m-%d"
        
        pDT1 = datetime.datetime.strptime(sDT1, sFormat)

        if(":" in sDT2): 
            sFormat = "%Y-%m-%dT%H:%M:%S.%f"
        else:
            sFormat = "%Y-%m-%d"
        
        pDT2 = datetime.datetime.strptime(sDT2, sFormat)

        oDelta = pDT1 - pDT2

        return oDelta

    @staticmethod
    def isInMaxSpan (oDate1, oDate2, nDays):
        """ check if oDate1 and oDate2 is within nDays """
        bIsIn = True
        try:
            oDelta = oDate1 - oDate2
            dDays = oDelta.days   #  math.fabs(oDelta.days);
            if(dDays > nDays):
                bIsIn = False
            else:
                bIsIn = True
        except:
            bIsIn = True

        return bIsIn

    @staticmethod
    def makeDateTimeFromString(strDateTime, sFormat='%a, %d %b %Y %H:%M:%S'):
        """sDate = 'Wed, 25 Jan 2017 18:31:26' sFormat='%a, %d %b %Y %H:%M:%S' 
           sDate1 = 'Wed, 25 Jan 2017 18:31:26 GMT', sFormat='%a, %d %b %Y %H:%M:%S %Z'
        """
        if(sFormat==""):
            sFormat = "%Y-%m-%d %H:%M:%S"
        d = datetime.datetime.now() 
        try:
            d = datetime.datetime.strptime(sDate, sFormat)
        except:
            pass 

        return d 


    #@staticmethod
    #def addFields(pTableFullPath, dFields):
    #    for sField in dFields:
    #        oDesc = arcpy.Describe(pTableFullPath)
    #        if (apwrutils.Utils.FieldExist(oDesc, sField)==False):
    #            arcpy.AddField_management(pTableFullPath, sField, dFields[sField])


    @staticmethod
    def listFieldNames(pTable, typeFilter=0):
        """List a table's field names."""
        """typeFilter=0,1,2,4.  0: list all fields, 1: exclude OID, Shape_Length, Shape_Area etc. 2: exclude Shape, 4: exclude NonePrintable fields, e.g., BLOB."""
        if(typeFilter==0):
            lFieldNames = [f.name for f in arcpy.ListFields(pTable)]
        else:
            lFieldNames = []
            for f in arcpy.ListFields(pTable):
                bCanAdd=True
                if((typeFilter & 1)==1):
                    sName = f.name.lower()
                    if((f.type=="OID") or (sName=="shape_length") or (sName=="shape_area")): 
                        bCanAdd=False
                if((typeFilter & 2)==2):
                    if(f.type=="Geometry"): 
                        bCanAdd = False
                if((typeFilter & 4)==4): 
                    if(f.type=="BLOB"): 
                        bCanAdd = False
                if(bCanAdd):
                    lFieldNames.append(f.name)
        return lFieldNames

    @staticmethod
    def addFieldsFromlFields(pTargetTbl, lFields):
        for pField in lFields:
            try:
                if((pField.type not in ["Geometry","OID"]) and (pField.name.lower() not in ["shape_length", "shape_area"])):
                    arcpy.AddField_management(pTargetTbl, pField.baseName, pField.type, pField.precision, pField.scale, pField.length, pField.aliasName, pField.isNullable, pField.required, pField.domain)
                    #fld.name,fld.baseName,fld.type,fld.length, fld.precision, fld.scale, fld.required, fld.isNullable, fld.editable, fld.domain,fld.required 
            except:
                pass

    @staticmethod
    def isFeatureLayerType(sLayer):
        """Check if sLayer is pointing to a FeatureClass(e.g., 'c:\temp\mydb.gdb\layers\aaa') or FeatureLayer (e.g., 'aaa') """
        return os.path.basename(sLayer) == sLayer
    @staticmethod
    def allFieldsOK(oDesc, lFieldNames):
        """ check if all the fields in lFieldNames [], exist. returns C_OK, or a string listing the fieldnames that does not exist."""
        sMsg = apwrutils.C_OK
        for fld in lFieldNames:
            if(apwrutils.Utils.FieldExist(oDesc, fld)==False):
                if(sMsg==apwrutils.C_OK):
                    sMsg = fld
                else:
                    sMsg = sMsg + "," + fld
        return sMsg

    @staticmethod
    def allFieldsOKTbl(oTbl, lFieldNames):
        """ check if all the fields in lFieldNames [], exist. returns C_OK, or a string listing the fieldnames that does not exist."""
        oDesc = arcpy.Describe(oTbl)
        sMsg = apwrutils.Utils.allFieldsOK(oDesc, lFieldNames)
        return sMsg

    @staticmethod
    def addFields(pTableFullPath, dFields, lFieldOrder=None):
        """ Given an FC, add fields defined in dFields 
            dFields (key:Name,value:type), lFieldOrder: order in which fields will be added.
            e.g., 
            dFields = dict()
            dFields.setdefault("FEATUREID", "LONG")
            dFields.setdefault("TSValue", "DOUBLE")
            dFields.setdefault("TSTIME", "DATE")
            dFields.setdefault("TSDESC", "TEXT")
            ..ye, @6/16/2015 11:06:56 AM on ZYE1  """
        if(isinstance(lFieldOrder,list)==False):
            lFieldOrder = dFields.keys()
        else:
            try:
                n = len(lFieldOrder)
                if(n!=len(dFields.keys())):
                    lFieldOrder.extend(dFields.keys())
            except:
                lFieldOrder = dFields.keys()    
        i = 0
        for sField in lFieldOrder:
            try:
                oDesc = arcpy.Describe(pTableFullPath)
                if (apwrutils.Utils.FieldExist(oDesc, sField)==False):
                    if(sField in dFields):
                        arcpy.AddField_management(pTableFullPath, sField, dFields[sField])
                        i = i + 1
            except:
                arcpy.AddMessage(trace())

        return i

    @staticmethod
    def GetLayerFilePath(scriptDir,layertag):
        try:
            lyrfilespath = os.path.join(scriptDir,'lyrfiles')
            lyrfilepath = os.path.join(lyrfilespath,layertag + '.lyr')
            if arcpy.Exists(lyrfilepath):
                return lyrfilepath
            else:
                return ''
        except:
            pass
            return ''
    @staticmethod
    def GetLinearUnitName(inLayer):
        """Given a dataset or layer, return its linearUnitName"""
        sName = ''
        try:
            oDesc = arcpy.Describe(inLayer)
            oSpRef = oDesc.spatialReference
            sName = oSpRef.linearUnitName

        except:
            sName = 'Unknown'

        return sName

    @staticmethod
    def GetMeasureUnitFromLinearUnitName(sUnitName):
        sUnitName = sUnitName.upper()
        """ given a linearunit name returns measure name to be used in specifing snap distance, search distance etc. e.g., US_FOOT->feet  """
        s="Feet"
        if(sUnitName=="FOOT" or sUnitName=="FOOT_US"):
            s = "feet"
        elif(sUnitName=="MILE"):
            s = "miles"
        elif(sUnitName=="INCH"):
            s = "inches"
        elif(sUnitName=="METER"):
            s = "meters"
        elif(sUnitName=="KILOMETER"):
            s = "kilometers"
        elif(sUnitName=="CENTIMETER"):
            s = "centimeters"
        else:
            s = "Unknown"
        return s 


    @staticmethod
    def LinearUnitToMeter(sLinearUnit):
        sLinearUnit = sLinearUnit.upper()
        r = 1.0
        if(sLinearUnit=="FOOT"):
            r = 1.0/3.281
        elif(sLinearUnit=="FOOT_US"):
            r = 1.0/3.281
        elif(sLinearUnit=="INCH"):
            r = 1.0/(3.281*12.0)
        elif(sLinearUnit=="METER"):
            r = 1.0
        elif(sLinearUnit=="MILE"):
            r = 1609.34
        elif(sLinearUnit=="KILOMETER"):
            r = 1000.0
        elif(sLinearUnit=="CENTIMETER"):
            r = 1.0/100.0
        elif(sLinearUnit=="MINIMETER"):
            r = 1.0/1000.0
        return r

    @staticmethod
    def getcwd():
        """Get current folder, current folder hosting mxd or project"""
        cwd = ""
        try:
            lVersion = sys.version_info
            if(lVersion[0]==2):
                oMxd = arcpy.mapping.MapDocument("CURRENT")
                cwd = os.path.dirname(oMxd.filePath)
                #arcpy.AddMessage("oMxd.filePath={}".format(oMxd.filePath))
            elif(lVersion[0]==3):
                p = arcpy.mp.ArcGISProject("CURRENT")
                cwd = os.path.dirname(p.filePath)
            else:
                cwd = os.getcwd()
        except:
            #arcpy.AddMessage("except:")
            cwd = os.getcwd()

        return cwd

    @staticmethod
    def polygonToPolyline(pPolygon):
        pPolyline = pPolygon 
        try:
             pnt = arcpy.Point()
             pntArray = arcpy.Array()
             nParts = pPolygon.partCount
             arrArrays = arcpy.Array()
             for i in range(0,nParts):
                 pnts = pPolygon.getPart(i)
                 for pnt in pnts:
                     pntArray.append(pnt)

                 arrArrays.append(pntArray)

             pPolyline = arcpy.Polyline(arrArrays, pPolygon.spatialReference)
        except:
            pass
         
        return pPolyline
    @staticmethod
    def flipPolyline(pPolyline):
        pnt = arcpy.Point()
        pntArray = arcpy.Array()
        arrArrays = arcpy.Array()
        try:
            nParts = pPolyline.partCount
            for i in range(0, nParts):
                ir = (nParts-1)-i
                pnts = pPolyline.getPart(ir)
                for pnt in reversed(pnts):
                    pntArray.append(pnt)

                arrArrays.append(pntArray)

        except:
            arcpy.AddMessage("{}, {}".format(arcpy.GetMessages(2), trace()))

        pPolylineReturn = arcpy.Polyline(arrArrays, pPolyline.spatialReference)
        return pPolylineReturn 

    @staticmethod
    def GetVertexCount(oShape):
        """ given a shape, returns its total vertex count  """
        nTotal = 0
        try:
            nParts = oShape.partCount
            for i in range(0,nParts):
                nTotal = nTotal + len(oShape.getPart(i))
        except:
            pass
        return nTotal

    @staticmethod
    def isLicensedSpatial():
        """Set whether tool is licensed to execute."""
        if arcpy.CheckExtension("Spatial") == "Available":
            return True
        else:
            return False

    @staticmethod
    def extentAsString(oExt):
        sExt = "{} {} {} {}".format(oExt.XMin, oExt.YMin, oExt.XMax, oExt.YMax)
        return sExt

    @staticmethod
    def createTimeSeriesTable(pWorkspace, tableName, dFieldsAdd=None):
        """Create TimeSeries table, adding default FeatureID,VarID, TSTime, TSValue and optionally add the fields specified in the dFieldsAdd.
          pWorkspace = workspace, tableName=TStable name, 
          returns pTBTimeSeries = os.path.join(pWorkspace, sTBName)
        """
        pTBTimeSeries = os.path.join(pWorkspace, tableName)            
        try:
            if(arcpy.Exists(pTBTimeSeries)==False): 
                arcpy.CreateTable_management(pWorkspace, tableName)            
            dFields = dict()
            dFields.setdefault(apwrutils.FN_FEATUREID, "LONG")
            dFields.setdefault(apwrutils.FN_VARID, "LONG")
            dFields.setdefault(apwrutils.FN_TSTIME, "DATE")
            dFields.setdefault(apwrutils.FN_TSVALUE, "DOUBLE")
            dFields.setdefault(apwrutils.FN_VARID, "LONG")
            if(dFieldsAdd!=None) and (len(dFieldsAdd)>0):
                for k in dFieldsAdd:
                    if(k in dFields)==False:
                        dFields.setdefault(k, dFieldsAdd[k])

            apwrutils.Utils.addFields(pTBTimeSeries, dFields)
        except:
            arcpy.AddWarning("createTimeSeriesTable:{}".format(trace()))

        return pTBTimeSeries

    @staticmethod
    def getZFactorUnit(in_raster):
        sUnit = "Unknown"
        try:
             # Default z-factor value.
            zUnitFactor=1
            sr = arcpy.Describe(in_raster).spatialReference
            if sr.name == 'Unknown':
                zUnitFactor = 1
            else:
                m = re.findall("VERTCS(.*?;)", sr.exportToString())
                if m:
                    u = re.findall("UNIT(.*?]])", m[0])
                    if u:
                        zf = re.findall(",([0-9.]*)", u[0])
                        if zf:
                            zUnitFactor = float(zf[0])
                        try:
                            l = u[0].split(",")
                            sUnit1 = l[0].replace("[","")
                            sUnit = sUnit1
                        except:
                            pass

            #arcpy.AddMessage("Using zUnitFactor= " + str(zUnitFactor))
        except:
            arcpy.AddWarning(trace())
            zUnitFactor=1
        finally:
            return (zUnitFactor, sUnit)

    #Computes new coordinates x3,y3 at a specified distance
    #along the prolongation of the line from x1,y1 to x2,y2
    @staticmethod
    def extattonood(coords, dist):
        if(dist==0):
            dist=1.0
        (x1,y1),(x2,y2) = coords
        dx = x2 - x1
        dy = y2 - y1
        linelen = math.hypot(dx, dy)

        x3 = x2 + dx/linelen * dist
        y3 = y2 + dy/linelen * dist    

        return x3, y3

    #Compute a new coord x0,y0, extended in the direction of {x2,y2}->{x1,y1} (at the from node)
    @staticmethod
    def extatfromnood(coords, dist):
        if(dist==0):
            dist=1.0
        (x1,y1),(x2,y2) = coords
        dx = x2 - x1
        dy = y2 - y1
        linelen = math.hypot(dx, dy)

        x0 = x1 - dx/linelen * dist
        y0 = y1 - dy/linelen * dist    
        return (x0, y0)

    @staticmethod 
    def extAtFromNodePt(p1, p2, dist):
        """ given p1, p2, return a point at p1<-p2 direction by dist """
        pt = arcpy.Point(0,0)
        try:
            if(dist==0):
                dist=1.0
            (x1,y1),(x2,y2) = ((p1.X, p1.Y), (p2.X, p2.Y))
            dx = x2 - x1
            dy = y2 - y1
            linelen = math.hypot(dx, dy)

            x0 = x1 - dx/linelen * dist
            y0 = y1 - dy/linelen * dist    

            pt = arcpy.Point(x0, y0)

        except:
            pass
        return pt
    @staticmethod
    def getDistance(p1, p2):
        """ given p1, p2, return the distance between them """
        (x1,y1),(x2,y2) = ((p1.X, p1.Y), (p2.X, p2.Y))
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        return dist 

    @staticmethod
    def merge2Lines(pLine1, pLine2):
        """ merge pLine1 with pLine2, keeping the order, i.e., have pLine2 appended onto pLine1 """
        arrArrays = arcpy.Array()
        pLineMerge = None 
        try:
            nParts = pLine1.partCount 
            for ip in range(0, nParts):
                pnts = pLine1.getPart(ip) 
                arrArrays.append(pnts) 
            nParts = pLine2.partCount
            for ip in range(0, nParts):
                pnts = pLine2.getPart(ip)
                arrArrays.append(pnts) 
            pLineMerge = arcpy.Polyline(arrArrays, pLine1.spatialReference)

        except:
            pLineMerge = pLine1.union(pLine2)

        return pLineMerge

    @staticmethod
    def extAtToNodePt(p1, p2, dist):
        """ given p1, p2, return a point at p1->p2 direction by dist """
        pt = arcpy.Point(0,0)
        try:
            if(dist==0):
                dist=1.0
            (x1,y1),(x2,y2) = ((p1.X, p1.Y), (p2.X, p2.Y))
            dx = x2 - x1
            dy = y2 - y1
            linelen = math.hypot(dx, dy)

            x3 = x2 + dx/linelen * dist
            y3 = y2 + dy/linelen * dist    

            pt = arcpy.Point(x3,y3) 

        except:
            pass
        return pt

    @staticmethod
    def showShapeXY(pFL, sMsg=""):
        try:
            with arcpy.da.SearchCursor(pFL, [apwrutils.FN_ShapeAtXY], explode_to_points=True) as rows:
                for i,row in enumerate(rows):
                    arcpy.AddMessage("{}: {}. {}".format(sMsg, i,row[0]))

        except:
            pass


    """ get dNames={key=basename, value=dbname.sde.basename} """
    @staticmethod
    def getSDEBaseNameDict(sdeCon, KeyOnBaseName=True):
        """
           returns a dict = 
           {key=basename:value=dbname.sde.basename} if KeyOnBaseName=True
           {key=dbname.sde.basename, key=basename}, if KeyOnBaseName=False
        """
        sWorkspace = arcpy.env.workspace 
        try:
            arcpy.env.workspace = sdeCon
            lTables = arcpy.ListTables('*') 
            lNames = [x.split('.')[len(x.split('.'))-1] for x in lTables]
            dTables = dict(zip(lNames, lTables)) 
            lFCs = arcpy.ListFeatureClasses('*')
            lNames = [x.split('.')[len(x.split('.'))-1] for x in lFCs]
            dFCs = dict(zip(lNames, lFCs)) 
            dTables.update(dFCs)
            if(KeyOnBaseName==False):
                inv_dTables = {v: k for k, v in dTables.iteritems()}
                dTables = inv_dTables 

            return dTables 
        except:
            pass
        finally:
            arcpy.env.workspace = sWorkspace

class ApFields:
    Fields = dict()
    def GetApFieldByName(self, name):
        nameUp = name.upper()
        oField = ApField()
        for skey in self.Fields.keys:
            if(skey.upper()==nameUp):
              oField = self.Fields.item(skey)
        return oField   

    
class ApField:
    Name = ""
    TagName = ""
    Type = "DOUBLE"  #   "TEXT,FLOAT,DOUBLE,SHORT,LONG,DATE,BLOB,RASTER,GUID
    Precision = ""
    Scale=""
    Length="50"
    Exists=False
    value = 0.0


#..ye, @11/12/2015 9:02:02 AM on ZYE1
""" Configurations for Nebraska project
    apFieldsQG is a dict(key=FieldName, value=FieldDefinition 
        value can be used to create/append a field if needed.
        key = Q2,Q5,Q10 etc, in [2,5,10,25,50,100,101,200,500], can be used to loop througth the fields
        added so that they can be used to append the general Q fields to the XLine to host the Q values currently used for the WSE computation.
        i.e., Q2,Q5,Q10,Q25.. etc for the compuation of WSE2,WSE5,WSE10,WSE25.. etc. 
"""

class ApConfigNebraska:
    lModels = []
    lRPs = []
    apFieldsQ = apwrutils.ApFields()    # Q foe;ds with ModelName_

    def __init__(self):
        self.lModels = ["B","C","HP","So","St"]
        self.lRPs = [2,5,10,25,50,100,101,200,500]
        self.apFieldsQ = apwrutils.ApFields()
        #arcpy.AddMessage("Here in __init__")
        for md in self.lModels:
            for rp in self.lRPs:
                sName = "{}_Q{}".format(md, str(rp))   #md + "_Q" + str(rp)
                apField = apwrutils.ApField()
                apField.Name = sName
                apField.Type = "DOUBLE"
                self.apFieldsQ.Fields.setdefault(sName, apField)
        

    def getZField(self, sNameQ):
        sNameZ = ""
        for rp in self.lRPs:
            sQ = "_Q" + str(rp)
            if(sNameQ.endswith(sQ)==True):
                sNameZ = sNameQ.replace(sQ,"_Z" + str(rp))
                break
        return sNameZ
         
    def getHField(self, sNameQ):
        sNameH = ""
        for rp in self.lRPs:
            sQ = "_Q" + str(rp)
            if(sNameQ.endswith(sQ)==True):
                sNameH = sNameQ.replace(sQ,"_H" + str(rp))
                break
        return sNameH



#..ye, @5/12/2015 9:09:04 AM on ZYE1 
""" Configuration values for TRU project """
class ApConfigTRU:
    C_OK = 'OK'
    C_NOTOK = 'NOTOK'    

    FN_WaterMLURI = "ServiceURI"   #"WaterMLURILatest"
    FN_LID = "lid"
    TB_TimeSeries = "TimeSeries"
    TB_VariableDefinition = "VariableDefinition"
    FN_FeatureID = "FEATUREID"
    FN_VARID = "VARID"
    FN_TSTIME = "TSTIME"
    FN_TSVALUE = "TSVALUE"
    FN_UTCOFFSET = "UTCOFFSET"
    FN_HYDROID = apwrutils.FN_HYDROID
    FN_SITECODE = "HydroCode"
    FN_VARCODE = "VarCode"
    FN_STARTTIME = "StartTime"
    FN_ENDTIME= "EndTime"
    FN_SiteLat = "SiteLat"
    FN_SiteLong = "SiteLong"
    FN_beginPosition = "beginPosition"
    FN_endPosition = "endPosition"
    FN_OccurRank = "OccurRank"
    FN_OccurMeth = "OccurMeth"   #[AnnualThreshold, Threshold, AnnualCount, Count]
    FN_OccurLevel = "OccurLevel" 
    FN_IsDone = "ISDONE"
    FN_SubHydroID="SubHydroID"

    FN_FromFeatID = "FromFeatID"
    FN_ToFeatID = "ToFeatID"
    FN_NDID = apwrutils.FN_NEXTDOWNID
    FN_DRAINID = apwrutils.FN_DRAINID
    FN_NDJTTMin = "NDJTTMIN"
    FN_FCNT = "FromIndCnt"    #Count of peaks of current station.
    FN_TCNT = "ToIndCnt"    #Count of peaks of downstream station.
    FN_MCNT = "MatchCount"    #Count of peaks that matches (within the timespan specified in the NDJTTMIN
    FN_NAME = "Name"

    FN_MINVAL = "MIN_VAL"
    FN_MAXVAL = "MAX_VAL"
    FN_TSCNT = "TSCNT"
    FN_INDEPTime = "INDEPTIME"
      
class ApFlowSplitMgr:
    def __init__(self,pFlowSplitTable):
        try:
            self.__dFlowSplits = dict() # #Private m_dFlowSplits As Dictionary(Of Integer, List(Of Integer))  
            self.m_lAllDownStreamIDs = [] #Private m_lAllDownStreamIDs As List(Of Integer)     '..list of all the hydroid of the downstream line in the flow split table.
            self.lNextDownIDs = []
            if (pFlowSplitTable!=None) and (pFlowSplitTable) and arcpy.Exists(pFlowSplitTable):
            #Look for fields
            #iFldFeatureID = pFlowSplitTable.Fields.FindField(ApConfig.FN_FEATUREID
            #iFldNextDownID = pFlowSplitTable.Fields.FindField(ApConfig.FN_NEXTDOWNID)
                with arcpy.da.SearchCursor(pFlowSplitTable,[apwrutils.FN_FEATUREID,apwrutils.FN_NEXTDOWNID]) as cursor:
                    for row in cursor:
                        try:
                            iFeatureID = row[0]
                            iNextDownID = row[1]
                            if (iNextDownID in self.m_lAllDownStreamIDs) == False:
                                self.m_lAllDownStreamIDs.append(iNextDownID)
                            if (iFeatureID in self.dFlowSplits):                           
                                self.lNextDownIDs = self.dFlowSplits[iFeatureID]
                                self.lNextDownIDs.append(iNextDownID)
                            else:
                                self.lNextDownIDs = []
                                self.lNextDownIDs.append(iNextDownID)
                                #arcpy.AddMessage("add iFeatureID " +  str(iFeatureID))
                                self.dFlowSplits.setdefault(iFeatureID, self.lNextDownIDs)
                        except:
                            arcpy.AddError("error1")
                            pass            
        except:
             arcpy.AddError("error2")
             arcpy.AddError(apwrutils.Utils.trace())
             pass

    #  '..returns downstream flow split dictionary, keyed on upstream hydroid (FEATUREID in the split table)
    # Public Property FlowSplits As Dictionary(Of Integer, List(Of Integer))
    @property
    def dFlowSplits(self):
        if self.__dFlowSplits is None:
            self.__dFlowSplits = dict() 
        return self.__dFlowSplits   
   

#..returns all the NEXTDOWNIDs in the flowsplit table, this way for any given river line's hydroid, we can check if that river is placed in the flowsplit table.
    def AllDownStreamLineIDs(self):
        return self.m_lAllDownStreamIDs
        
#  ''' <summary>
#  ''' Given an UpstreamHydroID, returns a list of downstream hydroids.
#  ''' if returns nothing, then this upstream river does not have a downstream river split
#  ''' else, 
#  ''' it has.
#  ''' </summary>
#  ''' <param name="UpStreamHID"></param>
#  ''' <returns>List(of HID), or nothing if there is not downstream line.</returns>
#  ''' <remarks></remarks>
    def GetDownstreamSplits(self,UpStreamHID):
        lIDs=[]
        try:
            if UpStreamHID in self.dFlowSplits:
               lIDs = self.dFlowSplits[UpStreamHID]
        except:
            lIDs = []
        return lIDs


#  '..As the number of splits is usually small, use this method for now.  if the number of split is big, need to use different method.
    def GetUpstreamIDs(self,DownStreamHID):
        lIDs =[]
        try:
            lv = []
            for iKey in self.dFlowSplits:
                lv = self.dFlowSplits[iKey]
                if DownStreamHID in lv:
                    lIDs.append(iKey)
                    #arcpy.AddMessage(str(DownStreamHID) + " down from " + str(iKey))
        except:
            lIDs = []
            arcpy.AddMessage("error")
        return lIDs

#  '..chk if there is an upstream river for a given downstream id
    def HasUpStreamLine(self,DownStreamHID):
        return DownStreamHID in self.m_lAllDownStreamIDs

class SplitP:
    def __init__(self, hydroid, count=0, riverorder=0):
        self.HYDROID = hydroid
        self.Count = count
        self.RiverOrder = riverorder

class MFeature:
      #'Structure SplitP
      #'  Dim HYDROID As Integer  'Splitriver's immediate upstream river's hydroid = the featureid in the splittable 
      #'  Dim Count As Integer
      #'  Dim RiverOrder As Integer
      #'End Structure
     def __init__(self, HydroID): 
          self.HYDROID = HydroID
          self.NEXTDOWNID=0
          self.GRIDID = 0           #'..Polygon GridID
          self.TRACEHYDROID = 0        #'..Tracing River's HYDROID or Polygon's HydroID if Polygon's nextdownid is used to trace. 
          self.Polygon = None       #'AdjCat=MergedUpstreamShapes, not including this shape.  AccumulateShape=MergedUpstreamShapes, including this shape.
          self.IsDone = 0
          self.Order = 0                    #'..RiverOrder
          self.OID = 0             #'..OID of the feature in the Polygon FC.
          self.sHead = 0          #'..0 is not head, 1 is head 
          self.Area = 0
          self.SplitIDs = []       # List(Of SplitP) = New List(Of SplitP)
          self.OmitUp=0            #    'OmitUp = 0 or NULL, continue to go up, = 1, AccumulateShap restart at this location, i.e., MFeature.Polygon = thisFeature.Shape. 
          self.UpStreamIDs = []    #New List(Of Integer)    '..Hold a list of immediate upstream trace features (river's) oid.
          self.DownStreamIDs = []    #New List(Of Integer)    '..Hold a list of immediate downstream trace features (river's) oid.

     def GetShape(self,wkb,spref):
        return arcpy.FromWKB(wkb,spref)
      
     def Clear(self):
         del self.SplitIDs[:]
         del self.UpStreamIDs[:]
         del self.DownStreamIDs[:]
         self.Polygon = None


if __name__ == '__main__':
    print(Utils.GetThisFileName() + " finished at: " + time.strftime("%Y/%m/%d %H:%M:%S"))
