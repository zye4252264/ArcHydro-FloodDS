'''***********************************************************************************************
Tool Name:  fdgetaddressh (SourceName=fdgetaddressh.py)
Version:  ArcGIS 10.0
Author:  zye 1/30/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
    (0) pAddressFile= [ComID, H, AddressOID]
    (1) pKisterFile =  [COMDID, Date, Q, H] downloaded ts file 
    (2) Outfile  extracted results [Comid, hmin, AddressOID, ForecastTime, S(m)] 


Description: Find the address whose h value < H of the download.
             Processing D:\10Data\TXDEM\CleanAddress.csv of 8604565 addresses on 9485601 TSValues.

History:  Initial coding -  zye 2/8/2017
Usage:  fdgetaddressh.py pAddressFile pKisterFile [OutFile, optional, default=pKisterFile_Out.csv] 
#D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro>
#  python fdgetaddressh.py D:\10Data\TXDEM\CleanAddress.csv D:\10Data\TXDEM\KisterData\MT20170207134243.csv
## debug:
## D:\10Data\TXDEM\KisterData\MT20170207134243.csv TxAddress100KFilter.csv
## C:\10DATA\TXDEM\CleanAddress.csv C:\10DATA\TXDEM\KisterData\KisterDataMT.csv
#  "D:\10Data\TXDEM\KisterData\Address05TotPop.csv" C:\10DATA\TXDEM\KisterData\KisterDataMT.csv
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import re 
import arcpy
import apwrutils

K_Sep = ","
AddressHmin = "HandHM"
AddressHminIndex = 1    #..Address HandM's column index in the Ascii file (Address05TotPopo.csv)

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

def getcmdargs(l):
    """ print out command arguments so that it can be used to run at the command line """
    sMsg = ""
    for i in range(len(l)):
        if(i==0): 
            sMsg=l[0]
        else:
            sMsg = "{} {}".format(sMsg, l[i])
    return sMsg

"""define the fdgetaddresshor class"""
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
    
    """ execute(self, pAddressFile, pKisterFile, pOutFile """
    def execute(self, pParams):      #pAddressFile, pKisterFile, pOutFile, iQHCheck):
        """ pAddressFile= [ComID, H, AddressID,AdrsPop10,CountyID,DistrictID,RegionID]
            pKisterFile =  downloaded ts file [COMDID, Date, Q, H]
            pOutFile = Output file for extracted values ComID,Date, Q, H
        """
        #r"D:\ProjectsUtils\HydroProjects\ApUtilityTools\Scripts\ApUtilityTools\nwm.short_range.channel_rt.forecasts_per_section_vertical.csv"
        (pAddressFile, pKisterFile, pOutFile, iQHCheck) = pParams 
        sMsg = getcmdargs(pParams) 
        arcpy.AddMessage(sMsg) 
        sMsg = ""
        sOK = apwrutils.C_OK 
        ds = time.clock() 
        l = []
        try:
            nTSCnt = 0
            if((self.DebugLevel & 1)==1):
                sMsg = "AddressFile:\t{}\nKisterFile:\t{}\nOutputFile:\t{}\nOnIndex:\t{} [3=Q,4=H]".format(pAddressFile, pKisterFile, pOutFile,iQHCheck)
                arcpy.AddMessage(sMsg)  
                sMsg = "Loading data file {}.".format(pKisterFile)
                arcpy.AddMessage(sMsg)

            with open(pKisterFile, 'r') as f:
                l = f.readlines()
                #for s in f:
                #   nTSCnt += 1
            nTSCnt = len(l) 
            del l 

            dTSValues = dict()
            sKey = ""
            sKeyLast = ""
            if((self.DebugLevel & 1)==1):
                sMsg = "Completed loading {} file of {} records, dt={}.".format(pKisterFile, nTSCnt, apwrutils.Utils.GetDSMsg(ds))
                arcpy.AddMessage(sMsg)

            dds = time.clock()
            with open(pKisterFile, 'r') as f:
                for s in f:
                    try:
                        s = s.replace("\n","")
                        sArr = s.split(",")
                        sArr[iQHCheck] = float(sArr[iQHCheck])
                        sKey = sArr[0]
                        del sArr[3]
                        del sArr[1]
                        if(sKeyLast==""):
                            sKeyLast = sKey
                            lValues = []
                            lValues.append(sArr[1:])
                        else:
                            if(sKeyLast==sKey):
                                lValues.append(sArr[1:])
                            else:
                                dTSValues.setdefault(sKeyLast, lValues) 
                                sKeyLast = sKey
                                del lValues 
                                lValues = []
                                lValues.append(sArr[1:])

                    except:
                        pass
                #l = f.readlines() 

            nComIDs = len(dTSValues)
            if((self.DebugLevel & 1)==1):
                sMsg = "Completed loading {} file of {} records with {} distinct comids.  dt={}".format(pKisterFile, nTSCnt, nComIDs, apwrutils.Utils.GetDSMsg(dds))
                arcpy.AddMessage(sMsg) 
            dds = time.clock()
            nAddresses = 0
            nMod = 1000000
            l = []
            nTotal = 0
            with open(pAddressFile, 'r') as f:
                l = f.readlines()

            #arcpy.AddMessage("Total={}, dt={}".format(nTotal, apwrutils.Utils.GetDSMsg(dds)))
            nTotal = len(l) 
            del l 
            nAdded = 0
            sKeyLast = ""
            lValues = []
            if((self.DebugLevel & 1)==1):
                sMsg = "Processing {} of {} addresses on {} TSValues.".format(pAddressFile, nTotal, nTSCnt)
                arcpy.AddMessage(sMsg) 

            with open(pOutFile, 'w') as fout:
                #fout.write("Comid, hmin, AddressOID, ForecastTime, Sm\n")
                with open(pAddressFile, 'r') as f:
                    for i, sAddress in enumerate(f):
                        if(i==0): 
                            sHeader = sAddress.replace("\n","")
                            sHeader = "{}, TSTime, Sm\n".format(sHeader)
                            fout.write(sHeader) 
                        else: 
                            try:
                                sAddress=sAddress.replace("\n","")
                                sArr = sAddress.split(',')
                                hmin = float(sArr[1])
                                sKey = sArr[0]
                                if(sKey!=""):
                                    lValues = dTSValues[sKey]
                                    #if(sKeyLast!=sKey):
                                    #    lValues = dTSValues[sKey]
                                    #else:
                                    #    sKeyLast = sKey 
                                    for values in lValues:
                                        if(values[1] >= hmin):
                                             s = ",".join(str(o) for o in values)
                                             sAddThis = "{},{}\n".format(sAddress,s)
                                             fout.write("{}".format(sAddThis))
                                             nAdded += 1
                                             #arcpy.AddMessage(sAddThis) 
                                    if((self.DebugLevel & 1)==1):
                                        if((i % nMod)==0): 
                                            sMsg = "  Processing {} of {} addresses on {} TSValues with {} flooded events found. dt={}".format(i,nTotal, nTSCnt, nAdded, apwrutils.Utils.GetDSMsg(dds)) 
                                            arcpy.AddMessage(sMsg)
                                else:
                                    pass

                            except:
                                lValues = []
                                sKeyLast = ""
                                pass                                        
                         
                sMsg = "Completed processing {} of {} addresses on {} TSValues with {} flooded events found. dt={}".format(pAddressFile, nTotal, nTSCnt, nAdded, apwrutils.Utils.GetDSMsg(dds))  
                arcpy.AddMessage(sMsg)                                      
                #lAddress = f.readlines() 

        except:
            sMsg = trace()
            arcpy.AddMessage(sMsg) 
            sOK = apwrutils.C_NOTOK
        finally:
            pass 
        return (sOK, pOutFile, sMsg) 
    
class QHType:
    Q = 3
    H = 4
            
if __name__ == '__main__':
    #oProcessor = None
    ds = time.clock()
    try:
        iQHType = QHType.H    #default to check only the H
        debugLevel = 0
        if(len(sys.argv)<3):
            arcpy.AddMessage("Usage: {} {} {} {} {}".format(sys.argv[0], "ComIDHQFile", "FilterFile" "OutFile (Optional)"))
            sys.exit(0)
        sMsg = ""
        sMsg = apwrutils.Utils.getcmdargs(sys.argv)
        arcpy.AddMessage(sMsg)
        pAddressFile = sys.argv[1]
        pKisterFile = sys.argv[2]
        pOutFile = ""
        if(len(sys.argv)>3):
            pOutFile = sys.argv[3]
        if(pOutFile==""):
            (pOutFile, ext) = os.path.splitext(pKisterFile)
            pOutFile = "{}_AddH{}".format(pOutFile,ext) 
         
        #pParams = (pQHFile, pFilter, pOutFile, iQHType, 0)   
        pProcessor = ClassOp()
        pProcessor.DebugLevel = debugLevel
        pParams = (pAddressFile, pKisterFile, pOutFile, QHType.H ) 
        (sOK, pOutFile, sMsg) = pProcessor.execute(pParams)  #pAddressFile, pKisterFile, pOutFile, QHType.H ) 
        del pProcessor        
    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at {}.  dtTotal={}'.format(dt.strftime("%Y-%m-%d %H:%M:%S"), apwrutils.Utils.GetDSMsg(ds, "")))

