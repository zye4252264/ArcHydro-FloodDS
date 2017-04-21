import sys 
import os 
import datetime
import time
import arcpy 
import arcpy.sa 


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

def GetDSMsg(ds, format="%.3f s."):
        d = time.clock()
        dt = d - ds
        if(format==""):
            format = "%.3f s."
    
        return format % dt

def GetWorkspaceDatasets(sWorkspace, feature_type, fdName, iFCLevel, sNameFilter ="*", bIncludeRaster=False): 
    #fdName="*" - include all,
    #feature_type: default value="All"
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
            listFCs = arcpy.ListFeatureClasses(sNameFilter, feature_type, ds)
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

    if(bIncludeRaster==True):
        if(sWorkspace.lower()=="%scratchworkspace%"):
            sPath = arcpy.env.workspace = arcpy.env.scratchGDB
        else:
            sPath = sWorkspace

        arcpy.env.workspace = sPath       
        listRasters = arcpy.ListRasters()
        for r in listRasters:
            dReturns.setdefault(r, os.path.join(sPath, r))

    return dReturns

if(__name__=='__main__'):
    """List contents in the scratchworkspace"""
    try:
        ds = time.clock()
        pWks = arcpy.GetParameterAsText(0)
        if pWks == '#' or not pWks: pWks = "%scratchworkspace%"
        oDesc = arcpy.Describe(pWks)
        dFCs = GetWorkspaceDatasets(pWks, "All","*", 7, "*", True)
        nCnt = len(dFCs)
        sMsg = "Workspace {} contains {} objects.".format(oDesc.catalogPath, nCnt)
        arcpy.AddMessage(sMsg)
        i = 0
        sMsgLong = sMsg
        for key in dFCs:
            try:
                i = i + 1
                sType = "object"
                try:
                    pObject = dFCs[key]
                    oDesc = arcpy.Describe(pObject)
                    sType = oDesc.dataType
                except:
                    pass
                sMsg = "{}. {} {}={}".format(i,sType,key,dFCs[key])
                arcpy.AddMessage(sMsg)
                sMsgLong = sMsgLong + "\n" + sMsg
            except arcpy.ExecuteError:
                arcpy.AddWarning(str(arcpy.GetMessages(2)) + ": " + dFCs[key])
            except:
                arcpy.AddWarrning(str(trace()))
                arcpy.AddWarrning(str(arcpy.GetMessages(2)))
        arcpy.SetParameterAsText(1, sMsgLong)

    except arcpy.ExecuteError:
        arcpy.AddError(str(arcpy.GetMessages(2)))
    except:
        arcpy.AddError(str(trace()))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    finally:
        dt = datetime.datetime.now()

        arcpy.AddMessage("Finished at {}. dt={}".format(dt.strftime("%Y-%m-%d %H:%M:%S"), GetDSMsg(ds)))