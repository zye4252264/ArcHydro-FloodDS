import os
import sys 
import time 

import shutil
import pyperclip

# zye 2015/08/19 

def GetThisDir():
    import inspect
    return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

def GetDateTimeString(n = None):
        """ format a datetime to string """
        if(n==None):
            s = time.strftime("%Y%m%d%H%M%S", time.localtime())
        else:
            s = time.strftime("%Y%m%d%H%M%S", time.localtime())
            if((isNumeric(n)==True) and ((n>4) and (n<14))):
               s = s[0:n]
            else:
               s = s[0:14]
        return s

def isNumeric(s):
    b = True
    try:  
        i = float(s)
    except:    # not numericelse:    # numeric
        b= False
    return b

if(__name__=='__main__'):
    sFiles = [r'D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\XToolboxes\FloodDS.tbx','apwrutils.py','hydroconfig.py','flooddsconfig.py','make3dline.py','floodds.py','flooddsmain.py', 'floodplainfrom3driverraster.py','convert3dlinetoraster.py','waterlevelonriver.py','constructmosaicds.py','mosaicdataset2polygonfc.py','mosaicdatasetpolygonupdate.py','AddFloodDS.bat','copyfeaturesinorder.py', 'qhexchange.py',r'D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\XToolboxes\QH.tbx', 'ApGetFlow.py','qhexchange.py','listgdb.py','flooddsmainhand.py','floodplainhand.py','floodplainfromhand.py','floodhandbase.py','extractraster.py','flooddsmainR.py','getaddresscountbycomidh.py','make3DLineSystem.py','fdgettsvaluekisterurl.py','GetURLHeader.py','fdgettsvaluekisterurlM.py','fdtsvalueextract.py','kisterFilter.txt','kisterGetTSValuesST.bat','kisterGetTSValuesMT.bat','TxAddress100KFilter.csv','fdgetaddressh.py','fdgetaddresshM.py','fdconstructmosaicds.py','fdtsvaluemax.py','fdtsvaluemaxM.py', 'fdgroupbystats.py','fdgroupbystatsM.py','fdgroupbystatsTS.py', 'kisterMaxTSValues.bat',r'D:\Projects\Branches\10.3_Final\ArcHydroTools\docs\FloodDS0804.docx', 'kisterGetTSValuesMTsde.bat','kisterGetTSValuesSTsde.bat','fdtableupdate.py']
    #sFiles = ['GetSROP.py','GetSRConfig.py', 'work0707.py', 'work0707A.py','containers.py','LASANQuery.py','ReadJson.py','ReadJson0728.py','SANSTAR2JSON.py','upsert_abw.py','upsert_mha.py']
    sDir = GetThisDir()
    sBackup = os.path.join(sDir, "CodeBackup")
    if(os.path.exists(sBackup)==False):
        os.mkdir(sBackup)

    sBackFD = "FDS" + GetDateTimeString(12)

    sBackupFolderP = os.path.join(sBackup, sBackFD)       
    if(os.path.exists(sBackupFolderP)==False):
        os.mkdir(sBackupFolderP)

    sBackupFolder = os.path.join(sBackupFolderP, "srcPy")        
    if(os.path.exists(sBackupFolder)==False):
        os.mkdir(sBackupFolder)

    sBackupFolderDocs = os.path.join(sBackupFolder, "docs") 
    if(os.path.exists(sBackupFolderDocs)==False):
        os.mkdir(sBackupFolderDocs)
    
    sMsg = "Copy {} files.".format(len(sFiles))
    sBackupFoldSrc = os.path.join(sBackupFolder, "Scripts")
    if(os.path.exists(sBackupFoldSrc)==False):
        os.mkdir(sBackupFoldSrc)
    sBackupFoldSrc = os.path.join(sBackupFoldSrc, "ArcHydro")
    sBackupFoldTbx = os.path.join(sBackupFolder, "Toolboxes")
    if(os.path.exists(sBackupFoldSrc)==False):
        os.mkdir(sBackupFoldSrc)
    if(os.path.exists(sBackupFoldTbx)==False):
        os.mkdir(sBackupFoldTbx)

    for sFile in sFiles:
        if(os.path.exists(sFile)==False):
            srcFile = os.path.join(sDir, sFile)
        else:
            srcFile = sFile
        if(sFile.lower().endswith(".py") or sFile.lower().endswith(".bat") or (sFile.lower().endswith(".txt")) or (sFile.lower().endswith(".csv"))):
            shutil.copy2(srcFile, sBackupFoldSrc)
            sMsg = sMsg + "\n" + srcFile + "->" + sBackupFoldSrc
        elif(sFile.lower().endswith(".docx") or sFile.lower().endswith(".pptx")):
            sBaseDocName = os.path.basename(srcFile) 
            sTargetDocName = os.path.join(sBackupFolderDocs, sBaseDocName)
            shutil.copy2(srcFile, sTargetDocName)
        else:
            shutil.copy2(srcFile, sBackupFoldTbx)
            sMsg = sMsg + "\n" + srcFile + "->" + sBackupFoldTbx

    print(sMsg)
    print(sBackupFolder)
    print(sBackup)
    pyperclip.copy(sBackup)
            
    #import subprocess
    #p = subprocess.Popen('D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro\CodeBackup\Copy2Test.bat {} D:\Data10\DataSub\DataSub'.format(sBackupFolderP), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sCmd = r'D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\Scripts\ArcHydro\CodeBackup\Copy2Test.bat {} D:\Data10\DataSub\DataSub'.format(sBackupFolderP)
    os.popen(sCmd)
    os.system(sCmd)

    print(sCmd) 
    #import subprocess
    #p = subprocess.Popen(sCmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)



