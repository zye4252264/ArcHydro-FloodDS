'''***********************************************************************************************
Tool Name:  fdtsvaluemax (SourceName=fdtsvaluemax.py)
Version:  ArcGIS 10.3
Author:  zye 2/22/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
    (0) QHFile [Comid Index ForecastTime Q(m3/s) S(m)]
    (1) Outfile  extracted results [Comid Index ForecastTime Q(m3/s) S(m)] 
Description: For each comid, find dt where max h (or q) happens.
History:  Initial coding -  2/22/2017
Usage:  fdtsvaluemax.py QHFile OutFile
#  "C:\10DATA\TXDEM\KisterData\MT20170222134202.csv"
#  python fdtsvaluemax.py C:\10DATA\TXDEM\KisterData\MT20170222134202.csv 
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import re 
import arcpy
import apwrutils

import flooddsconfig

K_Sep = ","

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

"""define the fdtsvaluemaxor class"""
class ClassOp:
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
    
    """ execute(self, pParams=(QHFile ComidFile OutFile) """
    def execute(self, pQHFile, pOutFile, iQHCheck):
        """ pQHFile=downloaded ts file [COMDID, Date, Q, H]
            pOutFile = Output file for extracted values ComID,Date, Q, H
            iQHCheck = 3, 4
        """
        #r"D:\ProjectsUtils\HydroProjects\ApUtilityTools\Scripts\ApUtilityTools\nwm.short_range.channel_rt.forecasts_per_section_vertical.csv"
        sMsg = ""
        sOK = apwrutils.C_OK 
        ds = time.clock() 
        try:
            if(self.DebugLevel & 1 == 1):
                sMsg = "InputFile:\t{}\nOutputFile:\t{}\nOnFieldIndex:\t{} [3=Q,4=H]".format(pQHFile, pOutFile,iQHCheck)
                arcpy.AddMessage(sMsg)   
            #(pQHFile, pOutFile, iQHCheck) = pParams   #iQHCheck=3 (check Q, or 4 check H, 7 check both).    bWith0 = True, bWith0 0 in the filter, else exclude.
            l = []
            ComIDLast = ""
            valueMax = -999999.0
            lValuesMax = []
            dds = time.clock()
            with open(pQHFile, 'r') as f:
                l = f.readlines()

            nCnt = len(l)
            nMod = nCnt/20
            if(nMod<1):
                nMod=1 
            dds = time.clock()
            iAdded = 0
            with open(pOutFile,'w') as fout:
                fout.write("Comid,Index,TSTime,Q(m3/s),s(m)\n")
                for i, sLine in enumerate(l):
                    try:
                        s = sLine.replace('\n','')
                        ls = s.split(K_Sep)
                        ComID = ls[0]
                        value = float(ls[iQHCheck])
                        if(ComIDLast == ""):
                            ComIDLast = ComID 
                        if(ComIDLast==ComID):
                            if(value>valueMax):
                                valueMax = value
                                lValuesMax = ls[:]
                        else:
                            sout = ",".join(str(o) for o in lValuesMax)
                            fout.write("{}\n".format(sout))
                            iAdded  = iAdded + 1 
                            lValuesMax = ls[:]
                            valueMax = value 
                            ComIDLast = ComID 
                    except:
                        pass
                    finally:
                        if((self.DebugLevel & 1)==1):
                            if((i % nMod)==0): 
                                sMsg = "  Processing {} recs of {} with {} max values added.  dt={}".format(i, nCnt, iAdded, apwrutils.Utils.GetDSMsg(dds))
                                arcpy.AddMessage(sMsg)

                #..writeout the last line:
                sout = ",".join(str(o) for o in lValuesMax)
                fout.write(sout)                              

                sMsg = "Completed processing {} recs with {} max values saved.  dt={}".format(nCnt, iAdded, apwrutils.Utils.GetDSMsg(dds))
                arcpy.AddMessage(sMsg)   

        except:
            ss = trace()
            arcpy.AddMessage(ss)
            sOK = apwrutils.C_NOTOK
        finally:
            pass 
        return (sOK, pOutFile, sMsg) 
    
            
if __name__ == '__main__':
    #oProcessor = None
    try:
        iQHType = flooddsconfig.QHType.H    #default to check only the H
        debugLevel = 0
        if(len(sys.argv)<2):
            arcpy.AddMessage("Usage: {} {} {}".format(sys.argv[0], "ComIDHQFile" "OutFile (Optional)"))
            sys.exit(0)
        pQHFile = sys.argv[1]
        pOutFile = ""
        if(len(sys.argv)>2):
            pOutFile = sys.argv[2]
        if(pOutFile==""):
            (pOutFile, ext) = os.path.splitext(pQHFile)
            pOutFile = "{}_max{}".format(pOutFile,ext) 
         
        #pParams = (pQHFile, pFilter, pOutFile, iQHType, 0)   
        pProcessor = ClassOp()
        pProcessor.DebugLevel = debugLevel
        (sOK, pOutFile, sMsg) = pProcessor.execute(pQHFile, pOutFile, iQHType) 
        del pProcessor        
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at {}'.format(dt.strftime("%Y-%m-%d %H:%M:%S")))

