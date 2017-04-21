'''***********************************************************************************************
Tool Name:  fdtsvalueextract (SourceName=fdtsvalueextract.py)
Version:  ArcGIS 10.0
Author:  zye 1/30/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
    (0) QHFile [Comid Index ForecastTime Q(m3/s) S(m)]
    (1) ComidHFile     [Comid S(m)]
    (2) Outfile  extracted results [Comid Index ForecastTime Q(m3/s) S(m)] 
Description: extract downloadedQHFile based on a set of comid and Hs specified in the comidHFile.
History:  Initial coding -  1/30/2017
Usage:  fdtsvalueextract.py QHFile ComidFile OutFile
#  D:\10Data\TXDEM\KisterData\DT20170130203131.csv D:\10Data\TXDEM\Trigger_QH_Header.csv 
#  D:\ProjectsUtils\HydroProjects\ApUtilityTools\Scripts\ApUtilityTools\nwm.short_range.channel_rt.forecasts_per_section_vertical.csv D:\10Data\TXDEM\AOIID_H120904.csv 
#  D:\10Data\TXDEM\KisterData\KisterSTVertical.csv D:\10Data\TXDEM\Trigger_H_2DP.CSV D:\10Data\TXDEM\KisterData\KisterExtracted.txt

#D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro>
#  python fdtsvalueextract.py D:\10Data\TXDEM\KisterData\nwm.short_range.channel_rt.forecasts_per_section_vertical.csv  D:\10Data\TXDEM\Trigger_H_2DP.CSV
## debug:
## D:\10Data\TXDEM\KisterData\MT20170207134243.csv TxAddress100KFilter.csv
## D:\10Data\TXDEM\KisterData\ST20170207233137.csv D:\10Data\TXDEM\CleanAddress.csv
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import re 
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

"""define the FDTSValueExtractor class"""
class FDTSValueExtractor:
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
    def execute(self, pQHFile, pFilter, pOutFile, iQHCheck, bHasAddress=False):
        """ pQHFile=downloaded ts file [COMDID, Date, Q, H]
            pFilter = filter file [ComID, Q or H]
            pOutFile = Output file for extracted values ComID,Date, Q, H
            iQHCheck = 3, 4
            bHasAddress = True, has address, needs to export AddressOID as well, bHasAddress indicates if the filter has address in it.
            if HasAddress=True, then pFilter = [ComID, Q or H, AddressOID] 
        """
        #r"D:\ProjectsUtils\HydroProjects\ApUtilityTools\Scripts\ApUtilityTools\nwm.short_range.channel_rt.forecasts_per_section_vertical.csv"
        sMsg = ""
        sOK = apwrutils.C_OK 
        ds = time.clock() 
        try:
            sMsg = "InputFile:\t{}\nFilterFile:\t{}\nOutputFile:\t{}\nOnIndex:\t{} [3=Q,4=H]".format(pQHFile, pFilter, pOutFile,iQHCheck)
            print(sMsg)   
            #(pQHFile, pComidFile, pOutFile, iQHCheck) = pParams   #iQHCheck=3 (check Q, or 4 check H, 7 check both).    bWith0 = True, bWith0 0 in the filter, else exclude.
            l = []
            with open(pQHFile, 'r') as f:
                l = f.readlines() 
            del l[0] 
            dds = time.clock()
            lHucs = []
            dHucs = dict()
            with open(pFilter, 'r') as f:
                lHucs = f.readlines()

            for i,s in enumerate(lHucs):
                s = s.replace('\n','')
                ls = s.split(',') 
                try:
                    ls[1] = float(ls[1])
                    if(bHasAddress==False):
                        dHucs.setdefault(ls[0], ls[1])
                    else:
                        lls = ls[1:]
                        if(ls[0] in dHucs)==False:
                            dHucs.setdefault(ls[0], lls)
                        else:
                            pass

                except:
                    pass
                    #ls[1] = 50.0

            print("Reading {} hucs from {}. dt={}".format(len(dHucs), pFilter, apwrutils.Utils.GetDSMsg(dds)))
            nCnt = len(l)
            if(nCnt<10): 
                nMod =1
            else:
                nMod = nCnt/10

            dds = time.clock()
            ll = []   
            iAdded = 0
            sMsg = "Extracting {} recs on {} filter values.".format(len(l), len(dHucs))
            print(sMsg)
            for i,s in enumerate(l):
                try:
                    c = s.split(',')
                    if((c[0] in dHucs)):
                        sv = c[iQHCheck].replace("\n","")
                        #s=re.sub("[^0-9]","",c[iQHCheck])
                        v = 0.0
                        try:
                            v = float(sv)
                            c[iQHCheck] = v                      
                            if(bHasAddress==False):
                                #..Filter on iQHCheck's value on pFilter.
                                if(v>=dHucs[c[0]]):
                                    iAdded = iAdded + 1 
                                    ll.append(c)
                            else:
                                lVals = dHucs[c[0]]
                                if(v>=lVals[0]):
                                    iAdded = iAdded + 1 
                                    c.extend(lVals)
                                    ll.append(c) 
                        except:
                            pass 
                            v = sv

                    
                except:
                    s = trace()
                    print(s)
                finally:
                    if((i % nMod)==0): 
                        sMsg = "  Processing {} of {} recs with {} recs added.  dt={}".format(i, nCnt, iAdded, apwrutils.Utils.GetDSMsg(dds))
                        print(sMsg)
            sMsg = "Completed extracting {} from {} on {} filter values.  dt={}".format(len(ll), len(l), len(dHucs), apwrutils.Utils.GetDSMsg(dds))
            print(sMsg)   
            dds = time.clock()
            #..Writing the extracted values to pOutFile.
            with open(pOutFile, 'w') as fout:
                fout.write("Comid,Index,ForecastTime,Q(m3/s),S(m)\n")
                for arr in ll:
                    s = ",".join(str(o) for o in arr)
                    fout.write("{}\n".format(s)) 
            sMsg = "Writing {} to {}. dt={}".format(len(ll), pOutFile, apwrutils.Utils.GetDSMsg(dds))
            print(sMsg) 
            print("dtTotal={}".format(apwrutils.Utils.GetDSMsg(ds)))    

        except:
            arcpy.AddError(trace())
            sOK = apwrutils.C_NOTOK
        finally:
            pass 
        return (sOK, pOutFile, sMsg) 
    
class QHType:
    Q = 3
    H = 4
            
if __name__ == '__main__':
    #oProcessor = None
    try:
        iQHType = QHType.H    #default to check only the H
        debugLevel = 0
        if(len(sys.argv)<3):
            print("Usage: {} {} {} {} {}".format(sys.argv[0], "ComIDHQFile", "FilterFile" "OutFile (Optional)"))
            sys.exit(0)
        pQHFile = sys.argv[1]
        pFilter = sys.argv[2]
        pOutFile = ""
        if(len(sys.argv)>3):
            pOutFile = sys.argv[3]
        if(pOutFile==""):
            (pOutFile, ext) = os.path.splitext(pQHFile)
            pOutFile = "{}_out{}".format(pOutFile,ext) 
         
        #pParams = (pQHFile, pFilter, pOutFile, iQHType, 0)   
        pProcessor = FDTSValueExtractor()
        pProcessor.DebugLevel = debugLevel
        (sOK, pOutFile, sMsg) = pProcessor.execute(pQHFile, pFilter, pOutFile, iQHType, True) 
        del pProcessor        
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

