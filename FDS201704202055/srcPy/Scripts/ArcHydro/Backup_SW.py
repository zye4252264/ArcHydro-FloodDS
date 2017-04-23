import os
import sys 
import time 
import pyperclip

import shutil
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
    sFiles = [r'D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\XToolboxes\ICPR.tbx',r'D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\XToolboxes\ICPR3LinkAdjustment.tbx','apwrutils.py','accumulateflowsonoverlappinglines.py', 'drainagepointprocessingR.py',r'D:\Projects\Branches\10.3_Final\ArcHydroTools\docs\ParallelProcessing.docx','constructdepressionhierarchy.py','assignhydroid.py', 'apnextid.py','hydroconfig.py','apwrutils.py','apiddepressionhierarchy.py','apextractsink.py','characterizecontourpolygons.py','definecontourlines.py','definecontourpolygons.py',r'D:\Projects\Branches\10.3_Final\ArcHydroTools\srcPy\AHMain\XToolboxes\ContourTreeTools.tbx']
    sDir = GetThisDir()
    sBackup = os.path.join(sDir, "CodeBackup")
    if(os.path.exists(sBackup)==False):
        os.mkdir(sBackup)
    sBackFD = "SWF" + GetDateTimeString(12)

    sBackupFolder = os.path.join(sBackup, sBackFD)       
    if(os.path.exists(sBackupFolder)==False):
        os.mkdir(sBackupFolder)

    sBackupFolder = os.path.join(sBackupFolder, "srcPy")     
    if(os.path.exists(sBackupFolder)==False):
        os.mkdir(sBackupFolder)


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
        if(sFile.lower().endswith(".py") or (sFile.lower().endswith(".bat"))):
            shutil.copy2(srcFile, sBackupFoldSrc)
            sMsg = sMsg + "\n" + srcFile + "->" + sBackupFoldSrc
        else:
            shutil.copy2(srcFile, sBackupFoldTbx)
            sMsg = sMsg + "\n" + srcFile + "->" + sBackupFoldTbx
            
    print(sMsg)
    print(sBackupFolder)
    print(sBackup)
    pyperclip.copy(sBackup)

    #sDir = GetThisDir()
    #sBackup = os.path.join(sDir, "CodeBackup")
    #if(os.path.exists(sBackup)==False):
    #    os.mkdir(sBackup)
    #sBackFD = "SWF" + GetDateTimeString(12)
    #sBackupFolder = os.path.join(sBackup, sBackFD)
    #if(os.path.exists(sBackupFolder)==False):
    #    os.mkdir(sBackupFolder)
    #sMsg = "Copy {} files.".format(len(sFiles))
    #sBackupFoldSrc = os.path.join(sBackupFolder, "Scripts")
    #if(os.path.exists(sBackupFoldSrc)==False):
    #    os.mkdir(sBackupFoldSrc)
    #sBackupFoldSrc = os.path.join(sBackupFoldSrc, "ArcHydro")
    #sBackupFoldTbx = os.path.join(sBackupFolder, "Toolboxes")
    #if(os.path.exists(sBackupFoldSrc)==False):
    #    os.mkdir(sBackupFoldSrc)
    #if(os.path.exists(sBackupFoldTbx)==False):
    #    os.mkdir(sBackupFoldTbx)

    #for sFile in sFiles:
    #    if(os.path.exists(sFile)==False):
    #        srcFile = os.path.join(sDir, sFile)
    #    else:
    #        srcFile = sFile
    #    if(sFile.lower().endswith(".py")):
    #        shutil.copy2(srcFile, sBackupFoldSrc)
    #        sMsg = sMsg + "\n" + srcFile + "->" + sBackupFoldSrc
    #    else:
    #        shutil.copy2(srcFile, sBackupFoldTbx)
    #        sMsg = sMsg + "\n" + srcFile + "->" + sBackupFoldTbx
            
    #print(sMsg)
    #print(sBackupFolder)
