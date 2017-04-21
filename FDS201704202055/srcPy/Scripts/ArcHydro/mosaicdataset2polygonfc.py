import sys 
import os 
import time 
import datetime
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

class MosaicDS2PolygonFC:
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
    def execute(self, mdsRaster):
        sOK = apwrutils.C_OK
        pEditor = None
        sCurDir = apwrutils.Utils.getcwd()  # os.getcwd()
        pFLPoly = ""
        try:
            oDesc = arcpy.Describe(mdsRaster) 
            pWorkspace = oDesc.path
            #pWorkspace = os.path.dirname(pWorkspace) 
            arcpy.AddMessage(pWorkspace) 
            sName = oDesc.name 
            sFCPolyName = "{}_Poly".format(sName)
            pFLPoly = sFCPolyName
            sFCPolyPath = os.path.join(pWorkspace, sFCPolyName) 
            sSrc = os.path.join(mdsRaster, "Footprint")
            arcpy.CopyFeatures_management(sSrc, sFCPolyPath)
            arcpy.MakeFeatureLayer_management(sFCPolyPath, sFCPolyName)
            
            if(self.DebugLevel>0): arcpy.AddMessage("Name={}, dataType={}".format(oDesc.Name, oDesc.dataType))
            spRef = oDesc.spatialReference
            
            if(self.DebugLevel>0):
                arcpy.AddMessage("spRef.name={}".format(spRef.name))
                lFields = arcpy.ListFields(mdsRaster)
                arcpy.AddMessage("{} has {} fields:".format(oDesc.Name, len(lFields)))
                i = 0
                for oFld in lFields:
                    arcpy.AddMessage("{}. {}".format(i, oFld.name))
                    i+=1 
                           
            #with arcpy.da.UpdateCursor(
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
            tReturn = (sOK, pFLPoly)
        else:
            tReturn = (sOK)

        return tReturn
         

if(__name__=='__main__'):
    try:
        inRasterDs = arcpy.GetParameterAsText(0) 
        outFLPolygon = arcpy.GetParameterAsText(1)
       
        if((flooddsconfig.debugLevel & 1)==1):
            for i in range(0,len(sys.argv)-2):
                arcpy.AddMessage("arg: {}: {}".format(i, arcpy.GetParameterAsText(i)))
        oProcessor = MosaicDS2PolygonFC()
        oProcessor.DebugLevel = flooddsconfig.debugLevel
        (sOK, pFLPoly) = oProcessor.execute(inRasterDs)             
        ddt = time.clock()
        if(sOK==apwrutils.C_OK):
            arcpy.SetParameterAsText(1, pFLPoly)
             
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
        arcpy.AddMessage('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

