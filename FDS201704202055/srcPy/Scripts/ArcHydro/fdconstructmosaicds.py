'''***********************************************************************************************
Tool Name:  fdconstructmosaicds (SourceName=fdconstructmosaicds.py)
Version:  ArcGIS 10.3.1
Author:  zye 2/11/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
    (0) pMosaicDS = arcpy.GetParameterAsText(0)
          
Description: Create a mosaic dataset to add desinated rasters in.
History:  Initial coding -  3/1/2015
Usage:  fdconstructmosaicds.py <Workspace, folders)
***********************************************************************************************'''
import sys
import os
import time 
import datetime
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

""" Create a mosiace dataset and add rasters to it. """
class MosaicDSBuilder:
    #variables:
    def __init__(self):
        self.DebugLevel = 0

    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())
    # Load the configuration xml.
    
    def getWorkspace(self, pFL):
        oDesc = arcpy.Describe(pFL)
        ooDesc = arcpy.Describe(oDesc.path)
        if(ooDesc.dataType=='FeatureDataset'):
            sWorkspace = ooDesc.path
        else:
            sWorkspace = oDesc.path

        return sWorkspace
    
    """ constructmodsaicdataset(self, pParams) """
    def execute(self, pParams):
        sOK = apwrutils.C_OK 
        pMosaicDS = ""
        try:
            (pWorkspace, sMosaicDSName, pRasterFolder) = pParams
            pMosaicDS = os.path.join(pWorkspace, sMosaicDSName)
            arcpy.env.workspace = pRasterFolder
            sRasterName = 'ochandpgrd'
            lRasters = arcpy.ListRasters(sRasterName)  
            pRaster = lRasters[0]
            oDesc = arcpy.Describe(pRaster) 
            pSpRef = oDesc.spatialReference 
            
            if(arcpy.Exists(pMosaicDS)) : arcpy.Delete_management(pMosaicDS) 
            arcpy.CreateMosaicDataset_management(pWorkspace, sMosaicDSName, pSpRef, 1, "8_BIT_UNSIGNED", "False Color Infrared", "#")
            rastype = "Raster Dataset"
            updatecs = "UPDATE_CELL_SIZES"
            updatebnd = "UPDATE_BOUNDARY"
            updateovr = "UPDATE_OVERVIEWS"
            maxlevel = "2"
            maxcs = "#"
            maxdim = "#"
            spatialref = "#"
            subfolder = "NO_SUBFOLDERS"
            duplicate = "EXCLUDE_DUPLICATES"
            buildpy = "BUILD_PYRAMIDS"
            calcstats = "CALCULATE_STATISTICS"
            buildthumb = "NO_THUMBNAILS"
            inputdatafilter = ""
            forcesr = "#"
              
            sDSName = "{}{}".format(sRasterName,1)              
            comments = "Mosaiced dataset for {}".format(sDSName)
            #arcpy.env.workspace = pRasterFolder
            
            for i in range(0,15):
                if(i==0):
                    inpath = os.path.join(pRasterFolder, sRasterName)
                    arcpy.AddMessage(arcpy.Exists(inpath))
                else:
                    inpath = "{};{}".format(inpath, os.path.join(pRasterFolder, sRasterName))     
            #arcpy.AddRastersToMosaicDataset_management(in_mosaic_dataset="MDTest", raster_type="Raster Dataset", input_path="D:\10Data\TXDEM\HandPostP\Layers\ochandpgrd;D:\10Data\TXDEM\HandPostP\Layers\ochandpgrd", update_cellsize_ranges="UPDATE_CELL_SIZES", update_boundary="UPDATE_BOUNDARY", update_overviews="NO_OVERVIEWS", maximum_pyramid_levels="", maximum_cell_size="0", minimum_dimension="1500", spatial_reference="", filter="#", sub_folder="SUBFOLDERS", duplicate_items_action="ALLOW_DUPLICATES", build_pyramids="NO_PYRAMIDS", calculate_statistics="NO_STATISTICS", build_thumbnails="NO_THUMBNAILS", operation_description="#", force_spatial_reference="NO_FORCE_SPATIAL_REFERENCE")
            arcpy.AddMessage(inpath)
            #arcpy.AddRastersToMosaicDataset_management(pMosaicDS, rastype, inpath, updatecs, updatebnd, updateovr,
            #        maxlevel, maxcs, maxdim, spatialref, inputdatafilter,
            #        subfolder, duplicate, buildpy, calcstats, 
            #        buildthumb, comments, forcesr)
            arcpy.AddRastersToMosaicDataset_management(in_mosaic_dataset=pMosaicDS, raster_type="Raster Dataset", input_path=inpath, update_cellsize_ranges="UPDATE_CELL_SIZES", update_boundary="UPDATE_BOUNDARY", update_overviews="NO_OVERVIEWS", maximum_pyramid_levels="", maximum_cell_size="0", minimum_dimension="1500", spatial_reference="", filter="#", sub_folder="SUBFOLDERS", duplicate_items_action="ALLOW_DUPLICATES", build_pyramids="NO_PYRAMIDS", calculate_statistics="NO_STATISTICS", build_thumbnails="NO_THUMBNAILS", operation_description="#", force_spatial_reference="NO_FORCE_SPATIAL_REFERENCE")

        except:
            arcpy.AddError(trace())
            sOK = apwrutils.C_NOTOK

        return (sOK, pMosaicDS) 
            
if __name__ == '__main__':
    #oProcessor = None
    sMsg = apwrutils.Utils.getcmdargs(sys.argv)
    print(sMsg)
    try:
        debugLevel = 0
        pWorkspace = arcpy.GetParameterAsText(0)
        sMosaicDSName = arcpy.GetParameterAsText(1)
        pRasterFolder = arcpy.GetParameterAsText(2) 
          
        oProcessor = MosaicDSBuilder()
        oProcessor.DebugLevel = debugLevel
        pParams = (pWorkspace, sMosaicDSName, pRasterFolder)
        tReturns = oProcessor.execute(pParams)       
        if(tReturns[0] == apwrutils.C_OK): 
            pMosaicDS = tReturns[1]
            arcpy.SetParameterAsText(3, pMosaicDS) 
       
              
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        if(oProcessor!=None):
            del oProcessor
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))