'''------------------------------------------------------------------------------------------------------------------------------
 Tool Name:   Convert3DLinetoRasterPy
 Source Name: Convert3DLinetoRasterPy.py
 Version:     ArcGIS 10.1
 Author:      D.Djokic (Environmental Systems Research Institute Inc.)
     
 Required Arguments:
              (0) Input Reference grid.
              (1) Input 3D line.
              (2) Output 3D line grid.
 Optional Arguments:
              None
 Description: Converts 3D line into grid using line Z values.  Line is densified to insure elevation interpolation.
			  This function exists in .net version.

 History:     Initial coding - 5/2014 (python version).
 Usage:     Convert3DLinetoRasterPy <Input_RefGrid> <Input_3DLine> <Output_3DLineGrid>
---------------------------------------------------------------------------------------------------------------------------------'''
import os
import time
import arcpy
import apwrutils                               # import Arc Hydro Tools module
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

class ApConvert3DLinetoRasterPy:
    #variables:
    def __init__(self):
        self.DebugLevel = 0

    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())

    #def execute(self, parameters, messages):
    def execute(self, inRefGrid, in3DFC, out3DGrid, pScratchWorkspace = None):
    #def Convert3DLinetoRasterPy(self, inRefGrid, in3DFC, out3DGrid):
        sOK = apwrutils.C_OK
        try:
            # use scratchworkspace to hold intermediate datasets. ..ye, @1/2/2016 9:35:45 AM on ZYE1
            if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("in conver3dlinetoraster: os.environ['TMP']={}, os.environ['TEMP']={}".format(os.environ['TMP'], os.environ['TEMP']))
            if(pScratchWorkspace!=None):
                pScratchWKS = pScratchWorkspace
                arcpy.env.scratchWorkspace = pScratchWorkspace
            else:
                pScratchWKS =  flooddsconfig.pScratchWorkspace   # "%scratchworkspace%"   # "in_memory"   # 
            # Set current environment state
            envInitSnapRaster = arcpy.env.snapRaster    # snap raster
            envInitCellSize = arcpy.env.cellSize        # cell size
            envInitEnvExtent = arcpy.env.extent         # analysis environment

            # Set raster processing environment to input DEM grid
            arcpy.env.snapRaster = inRefGrid
            outCellSize = float(str(arcpy.GetRasterProperties_management(inRefGrid, "CELLSIZEX")))
            arcpy.env.cellSize = outCellSize
            arcpy.env.extent = inRefGrid

            # Setting workspace to input fc for the temporary FC copy
            fullPath = arcpy.Describe(in3DFC).path
            arcpy.env.workspace = fullPath
            tmpLineFC = os.path.join(pScratchWKS, "xTmpLine")
            tmpPntFC = os.path.join(pScratchWKS, "xTmpPnt")
            if(arcpy.Exists(tmpLineFC)): arcpy.Delete_management(tmpLineFC)
            if(arcpy.Exists(tmpPntFC)): arcpy.Delete_management(tmpPntFC)
            #tmpLineFC = fullPath + "\\xxxTmpLine"                                                           # temporary 3D line FC
            #tmpPntFC = fullPath + "\\xxxTmpPnt"                                                             # temporary 3D point FC
            # Start processing
            # ----------------
            dt = time.clock()
            # Create temporary 3D line FC and densify it (densify).
            if((self.DebugLevel & 1)==1):  arcpy.AddMessage("  Densifying input 3D line feature class...")
            arcpy.CopyFeatures_management(in3DFC, tmpLineFC)
            denDistance = outCellSize * 0.1                              # set densification distance to be 1/2 of the cell size
#            arcpy.Densify_edit(tmpLineFC, "DISTANCE", "10 Feet")       # need to adjust the densification as function of cell size
            arcpy.Densify_edit(tmpLineFC, "DISTANCE", denDistance)       # need to adjust the densification as function of cell size

            dt2 = time.clock()
            if((self.DebugLevel & 1)==1):  arcpy.AddMessage("      Densifying input 3D line feature class completed in " + str("%.2f" % (dt2 - dt)) + " seconds.")

            # Create temporary point FC (feature vertices to points).
            if((self.DebugLevel & 1)==1):  arcpy.AddMessage("  Converting densified 3D line into points...")
            arcpy.FeatureVerticesToPoints_management(tmpLineFC, tmpPntFC, "ALL")

            dt3 = time.clock()
            if((self.DebugLevel & 1)==1):  arcpy.AddMessage("      Converting densified 3D line into points completed in " + str("%.2f" % (dt3 - dt2)) + " seconds.")

            # Create 3D stream grid from points.
            if((self.DebugLevel & 1)==1):   arcpy.AddMessage("  Generating 3D line raster...")
            arcpy.PointToRaster_conversion(tmpPntFC,  "Shape.Z", out3DGrid)
            #arcpy.PointToRaster_conversion(tmpPntFC,  apwrutils.FN_ShapeAtZ, out3DGrid)

            dt4 = time.clock()
            if((self.DebugLevel & 1)==1):  arcpy.AddMessage("      Generating 3D line raster completed in " + str("%.2f" % (dt4 - dt3)) + " seconds.")
            # Clean up - delete temporary grids and FCs
            if((self.DebugLevel & 1)==1): arcpy.AddMessage("  Cleaning up...")
            try:
                arcpy.Delete_management(tmpLineFC, "")
                arcpy.Delete_management(tmpPntFC, "")
            except arcpy.ExecuteError:
                arcpy.AddWarning(str(arcpy.GetMessages(2)))
            except:
                arcpy.AddWarning(str(trace()))

                        
        except arcpy.ExecuteError:
            sMsg = str(arcpy.GetMessages(2))
            arcpy.AddError(sMsg)
        except:
            sMsg = str(trace())
            arcpy.AddWarning(sMsg)
            #arcpy.AddError(str(arcpy.GetMessages(2)))
        finally:
            # Setting output variables - needed for outputs for proper chaining
            arcpy.SetParameterAsText(2,out3DGrid)      # output = 3D line grid
            print ('Function Convert3DLinetoRasterPy finished')

        if(sOK==apwrutils.C_OK):
            tResults = (apwrutils.C_OK, out3DGrid)
        else:
            tResults = (sOK)

        return tResults


if __name__ == '__main__':
    try:
        # collect the input data and execute the function
        inRefGrid = arcpy.GetParameterAsText(0)            # input reference grid
        in3DFC = arcpy.GetParameterAsText(1)               # input 3D line feature class
        out3DGrid = arcpy.GetParameterAsText(2)            # output 3D line grid

        oProcessor = ApConvert3DLinetoRasterPy()
        oProcessor.DebugLevel = flooddsconfig.debugLevel
        tReturns = oProcessor.execute(inRefGrid, in3DFC, out3DGrid)

    except arcpy.ExecuteError:
        print str(arcpy.GetMessages(2))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    except:
        print trace()
        arcpy.AddError(str(trace()))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    finally:
        dt = datetime.datetime.now()
        print('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

