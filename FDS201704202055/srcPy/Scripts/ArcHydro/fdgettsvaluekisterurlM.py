'''***********************************************************************************************
Tool Name:  fdgettsvaluekisterurlM (SourceName=fdgettsvaluekisterurlM.py)
Version:  ArcGIS 10.0
Author:  zye 3/1/2015 (Environmental Systems Research Institute Inc.)
ConfigFile: AHPyConfig.xml located in the same place as source .py file. 
Required Arguments:
    (0) url = url to download the data, http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz
          
Description: 1. reads last datetime of download from config
  2. configFile - holds the datetime of last download.
  3. targetFolder - the folder to store the downloaded csv files.

History:  Initial coding -  1/30/2017
Usage:  fdgettsvaluekisterurlM.py url configFile targetFolder (optional)
***********************************************************************************************'''
import sys
import os
import datetime 
import time 

import arcpy
import fdgettsvaluekisterurl

#..download the kister's tsvalues - zye 9:30 PM 1/25/2017
#..http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz  c:\temp
#..https://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section.csv.gz

C_OK = 'OK'
C_NOTOK = 'NOTOK'

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



if(__name__=='__main__'):
    ds = time.clock()
    url = 'https://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section.csv.gz'          #h
    if(len(sys.argv)>1):
        url = arcpy.GetParameterAsText(0)
    else:
        url = 'http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz'  #v
    if(len(sys.argv)>2):
        targetFolder = arcpy.GetParameterAsText(1)
    if(targetFolder==""):
        targetFolder = r"D:\10Data\TXDEM\KisterData"
    
    if(len(sys.argv)>3):
        configFile = arcpy.GetParameterAsText(2)
    if(configFile==""):
        configFile = "kisterConfigST.txt"    #"KisterConfigMT.txt" and "KisterConfigLT.txt"
    print("ConfigFile = {}".format(configFile))

    pDataLoader = fdgettsvaluekisterurl.KisterDataLoader(url)
    (sOK, pDataFile, sMsg) = pDataLoader.execute(url, configFile, targetFolder) 
    if(sOK==C_OK):
        arcpy.SetParameterAsText(3, pDataFile)

    #************************************
    #    return localFileName                     
            ##trying to download the file:
            #pFile = downloadurlfile(url) 
            #fileFullPath = os.path.realpath(pFile)
            #arcpy.AddMessage("downloaded file is saved to: {}".format(fileFullPath))
            #if(fileFullPath.endswith('.zip')):
            #    zf = zipfile.ZipFile(fileFullPath)
            #    for info in zf.infolist():
            #        arcpy.AddMessage( info.filename)
            #        arcpy.AddMessage( '\tComment:\t', info.comment)
            #        arcpy.AddMessage( '\tModified:\t', datetime.datetime(*info.date_time))
            #        arcpy.AddMessage( '\tSystem:\t\t', info.create_system, '(0 = Windows, 3 = Unix)')
            #        arcpy.AddMessage( '\tZIP version:\t', info.create_version)
            #        arcpy.AddMessage( '\tCompressed:\t', info.compress_size, 'bytes')
            #        arcpy.AddMessage( '\tUncompressed:\t', info.file_size, 'bytes')
            #else:
            #    with gzip.open(fileFullPath, 'rb') as f:
            #         file_content = f.read()
            #    with gzip.open(fileFullPath, 'rb') as f_in, open('file.txt', 'w') as f_out:
            #         shutil.copyfileobj(f_in, f_out)
                 




