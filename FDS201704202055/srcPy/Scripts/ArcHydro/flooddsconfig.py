import arcpy 
from hydroconfig import * 
import hydroconfig

debugLevel = 0
C_UL = "_"
# folder name for depth, wse, and uwse rasters, with tiff ext.

FDN_Depth = "Depth"
FDN_DepthC = "DepthC"
FDN_WSE = "WSE"
FDN_UWSE = "UWSE"
FND_G_Depth = "G_Depth"
FND_G_PFZone = "G_PFZ"
FND_G_RWL = "G_WRL"


# the headers for the file names
HD_Depth = "d"
HD_WSE = "wse"
HD_UWSE = "uwse"

HD_G_Depth = "d"
HD_G_PFZone = "fpzone"
HD_G_RWL = "rwl"

HD_River = "r"
HD_WL = "WL"

# the raster ext (.tiff, or blank for raster)
Ext_R = ".tif"
GDB_NAME = "FP"
bConnectedPolyOnly = True 

LN_FP_RIVER = "FPRiver"
LN_FP_CATCHMENT = "FPCatchment"
LN_FP_WATERPOINT = "FPWaterPoint"

LN_FPZoneRiver = "FPZoneRiver"
LN_FPZone = "FPZone"

FN_FLDESC = "FPDH"     #FloodPlainDesc
FN_STEP = "FPSTEP"     #FloodPlainStep (index)
FN_GridCode = "GridCode"
FN_DateCreated = "DateCreated"
FN_StreamID = "StreamID"  # holds the hydroid of its related stream/river.

TB_HTable = "HTable"
FN_HIndex = "HIndex"
FN_HValue = "HValue"
FN_ISDONE = "ISDONE"
FN_HCode = "HCode"
FN_DH = "DH"

FN_ModeID = "ModelID"
FN_ModelName = "ModelName"
FN_AddressCount="AddressCount"
FN_TotPop10 = "TOTPOP10"
FN_TOTHU10 = "TOTHU10"
FN_ComID = "ComID"
FN_CountyID = "CountyID"
FN_DistrictID ="DistrictID"
FN_RegionID = "RegionID"
FN_ForecastTime = "ForecastTime"

FN_ForecastTimeStr = "ForecastTimeStr"
FN_StartForDT = "StartForDT"
FN_EndForDT = "EndForDT"
FN_TimeStep = "TimeStep"
FN_TimeUnits = "TimeUnits"
FN_IsRegular = "IsRegular"

TB_LogTable = "LogTable"
FN_ParamName = "ParamName"
FN_ParamDesc = "ParamDesc"

#..Impact analysis tables (6 tables).
TB_ComIDImpact = "ComIDImpactTS"
TB_ComIDImpactMax = "ComIDImpactTSMax"        
TB_CountyImpact = "CountyImpactTS"
TB_CountyImpactMax = "CountyImpactTSMax"
TB_DistIDImpact = "DistrictImpactTS"
TB_DistIDImpactMax = "DistrictImpactTSMax"
TB_RegIDImpact = "RegionImpactTS"
TB_RegIDImpactMax = "RegionImpactTSMax"
TB_ForecastModel = "ForecastModel"
pScratchWorkspace = arcpy.env.scratchGDB    # "in_memory"     #"%scratchworkspace%"    #"in_memory"    #arcpy.env.scratchGDB         #"%scratchworkspace%"
pScratchFolder =  arcpy.env.scratchFolder   #"%scratchfolder%"  "%scratchfolder%"      #

DTShort = 15
DTMid = 240 

class ConfMatch:
    pNone = "None"
    pAvg = "Avg"
    pMax = "Max"
    pMin = "Min"

class WLOpType:
    pInterpolate = "Interpolate"
    pDeltaH = "AddDeltaH"

class QHType:
    Q = 3
    H = 4

class StatsType:
    Count = 1
    Avg = 2
    Max = 4
    Min = 8
    Sum = 16
    Std = 32


class OpField:
    """ FromColumnIndex = index of inputcolumn
        ToFieldName = name of to Field, in outTB
    """
    FromColumnIndex = 0
    ToFieldName = ""
    def __init__(self, fromIndex, toFieldName):
        FromColumnIndex = fromIndex 
        ToFieldName = toFieldName 


class StatsOpFile:
    ValueIndex = -1   #Index of the ValueColumn
    GroupByIndex = -1   #Index of the GroupByColumn
    TSIndex = -1       #Index of the TSTimeColumn
    Stats = 0
    OutFile = ""       #OutputFileName (fullPath)
    OutTB = ""
    # 
    def __init__(self, iValueIndex, iGroupByIndex, iTSIndex, iStats, pIDs, outFile, outTB, workspace):
        self.DebugLevel = 0
        self.ValueIndex = iValueIndex 
        self.GroupByIndex = iGroupByIndex
        self.TSIndex = iTSIndex 
        self.Stats = iStats
        self.ParentIDs = pIDs        # [Index of parentIDs to be maintained (copied)]
        self.OutFile = outFile 
        self.OutTB = outTB
        self.Workspace = workspace 

    def __exit__(self, type, value, traceback):
        pass
    
    def __del__(self):
        pass
       

