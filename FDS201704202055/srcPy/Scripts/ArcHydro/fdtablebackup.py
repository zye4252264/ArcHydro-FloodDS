'''***********************************************************************************************
Tool Name:  fdtablebackup (SourceName=fdtablebackup.py)
Version:  ArcGIS 10.3
Author:  zye 3/28/2017 (Environmental Systems Research Institute Inc.)
ConfigFile: 
Required Arguments:
  0 gdbSource=GDB with 6 tables
  1 gdbTarget=GDB with 6 production tables
  2 gdbBackup=GDB to backup the 6 production tables in the gdbTarget

Description: 
  1. copy 6 tables from gdbTarget->gdbBackup (with datetime stamp of the tbl names)
  2. remove the recs from 6 tables in gdbTarget with where: modelid = 1 or 2.
History:  Initial coding -  3/27/2017
Usage:  fdtablebackup.py gdbSource gdbTarget gdbBackup
#  python fdtablebackup.py C:\10DATA\TXDEM\KisterData\TXStats.gdb C:\10DATA\TXDEM\KisterData\TXTarget.gdb C:\10DATA\TXDEM\KisterData\TXBackup.gdb
***********************************************************************************************'''
import sys
import os
import time 
import datetime
import arcpy
import apwrutils

import flooddsconfig

K_Sep = ","

FN_MaxTSTimeDT = "MAX_TSTimeDT"
FN_MaxTSTime = "Max_TSTime"

""" get dNames={key=basename, value=dbname.sde.basename} """
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

class GDBOp:
    GDB = None 
    dSDETableNames = None
    def __init__(self, gdb):
        self.GDB = gdb 
        oDesc = arcpy.Describe(gdb) 
        self.workspaceType = oDesc.workspaceType 
        if(oDesc.workspaceType=='RemoteDatabase'):
            self.isRemote = True
            self.dSDETableNames = getSDEBaseNameDict(gdb) 
        else:
            self.isRemote = False 

    def getSDETableName(self, sName):
        sReturn = sName
        if(self.dSDETableNames):
            try:
                sReturn = self.dSDETableNames[sName]
            except:
                pass

        return sReturn 

"""define the TSValueStatsOp class"""
class ClassOp:
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

    
    """ execute(self, pParams=(gdbSource, gdbTarget, gdbBackup, lTables) """
    def execute(self, pParams):    
        """ 
        pParams=(gdbSource, gdbTarget, gdbBackup, lTables)
        """
        sMsg = ""
        sOK = apwrutils.C_OK 
        ds = time.clock()
        try:
            (gdbSource, gdbTarget, gdbBackup, lTables) = pParams
            pGDBSource = GDBOp(gdbSource) 
            pGDBBackup = GDBOp(gdbBackup) 
            pGDBTarget = GDBOp(gdbTarget) 

            if((self.DebugLevel & 1)==1):
                sMsg = apwrutils.Utils.getcmdargs(pParams) 
                arcpy.AddMessage(sMsg)   
            #..make sure the target gdb has the tables, if not copy them.
            for i, sTable in enumerate(lTables):
                sTableNameT = pGDBTarget.getSDETableName(sTable) 
                tbTarget = os.path.join(gdbTarget, sTableNameT) 
                if(arcpy.Exists(tbTarget)==False):
                    sTableNameS = pGDBSource.getSDETableName(sTable) 
                    tbSource = os.path.join(gdbSource, sTableNameS) 
                    arcpy.Copy_management(tbSource, os.path.join(gdbTarget, sTable) ) 
                    if (self.DebugLevel & 1) == 1:  arcpy.AddMessage("{}. Copy {} -> {}".format(i, tbSource, tbTarget))

            #..Copy the tables from target to the backup gdb
            hd = "X_{}".format(apwrutils.Utils.GetDateTimeString())
            for i, sTable in enumerate(lTables):
                tbSource = os.path.join(gdbTarget, pGDBTarget.getSDETableName(sTable)) 
                tbTarget = os.path.join(gdbBackup, "{}_{}".format(hd, sTable))
                arcpy.Copy_management(tbSource, tbTarget) 
                if (self.DebugLevel & 1) == 1:  arcpy.AddMessage("{}. Copy {} -> {}".format(i, tbSource, tbTarget))

            for i, sTable in enumerate(lTables):
                sTableS = pGDBSource.getSDETableName(sTable) 
                sTableT = pGDBTarget.getSDETableName(sTable) 
                tbTarget = os.path.join(gdbTarget, sTableT)
                tbSource = os.path.join(gdbSource, sTableS) 
                nCnt = int(arcpy.GetCount_management(tbSource)[0])
                arcpy.DeleteRows_management(tbTarget) 
                arcpy.Append_management(tbSource, tbTarget, "NO_TEST") 
                if(tbTarget.endswith("Max")):
                    #..trying to copy the field of Max_TS...
                    if(len(arcpy.ListFields(tbTarget,FN_MaxTSTimeDT))>0):
                        try:
                            arcpy.CalculateField_management(tbTarget,FN_MaxTSTimeDT,"!{}!".format(flooddsconfig.FN_ForecastTime),"PYTHON_9.3")
                        except:
                            pass
                    if(len(arcpy.ListFields(tbTarget,FN_MaxTSTimeDT))>0):
                        try:
                            arcpy.CalculateField_management(tbTarget,FN_MaxTSTime,"!{}!".format(flooddsconfig.FN_TSTIME),"PYTHON_9.3")
                        except:
                            pass

                if (self.DebugLevel & 1) == 1:  arcpy.AddMessage("{}. Copy {} recs, {} -> {}".format(i, nCnt, tbSource, tbTarget))

        except:
            sMsg = trace()
            arcpy.AddMessage(sMsg)
            sOK = apwrutils.C_NOTOK
        finally:
            pass 
        return (sOK, gdbBackup, sMsg) 
    
            
if __name__ == '__main__':
    #oProcessor = None
    ds = time.clock()
    try:
        debugLevel = 1
        if(len(sys.argv)<2):
            arcpy.AddMessage("Usage: {} {} {}".format(sys.argv[0], "gdbSource gdbTarget gdbBackup"))
            sys.exit()  
        else:
            gdbSource = arcpy.GetParameterAsText(0)  # sys.argv[1]
            gdbTarget = arcpy.GetParameterAsText(1)  #sys.argv[2]
            gdbBackup = arcpy.GetParameterAsText(2)  #sys.argv[3]
                     
            lTables = [flooddsconfig.TB_CountyImpact,flooddsconfig.TB_CountyImpactMax, flooddsconfig.TB_DistIDImpact, flooddsconfig.TB_DistIDImpactMax, flooddsconfig.TB_RegIDImpact, flooddsconfig.TB_RegIDImpactMax]
            pProcessor = ClassOp()
            pProcessor.DebugLevel = debugLevel
            pParams=(gdbSource, gdbTarget, gdbBackup, lTables)
            (sOK, gdbBackup, sMsg) = pProcessor.execute(pParams)   #pQHFile, pOutFile, iValueIndex, iGroupByIndex, iStats) 
            arcpy.AddMessage("Completed, dt={}.".format(apwrutils.Utils.GetDSMsg(ds)))
            del pProcessor  
            arcpy.SetParameterAsText(3, gdbBackup) 

    except arcpy.ExecuteError:
        arcpy.AddError("{} {}".format(arcpy.GetMessages(2),trace()))
    except:
        arcpy.AddWarning("{} {}".format(arcpy.GetMessages(2),trace()))
    finally:
        dt = datetime.datetime.now()
        arcpy.AddMessage('Finished at {}'.format(dt.strftime("%Y-%m-%d %H:%M:%S")))

