import sys
import os
import datetime 
import time 
import requests 
import zipfile
import gzip 
import shutil

import arcpy
import urllib2
#..https://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section.csv.gz
#..http://nwm.kisters.de/nwm/current/short_range/tx/nwm.short_range.channel_rt.forecasts_per_section_vertical.csv.gz
#..https://nwm.kisters.de/nwm/current/medium_range/tx/nwm.medium_range.channel_rt.forecasts_per_section_vertical.csv.gz

#..Executing: ListURLHeaders https://nwm.kisters.de/nwm/current/medium_range/tx/nwm.medium_range.channel_rt.forecasts_per_section_vertical.csv.gz
#Start Time: Wed Feb 15 09:11:05 2017
#Running script ListURLHeaders...
#0. content-length=59157523
#1. accept-ranges=bytes
#2. server=Apache
#3. last-modified=Tue, 07 Feb 2017 13:42:43 GMT
#4. connection=close
#5. cache-control=public,max-age=0,no-cache
#6. date=Wed, 15 Feb 2017 17:11:05 GMT
#7. x-frame-options=SAMEORIGIN, SAMEORIGIN
#8. content-type=application/x-gzip
#Getting just the date element:
#date=Wed, 15 Feb 2017 17:11:05 GMT
#last-modified=Tue, 07 Feb 2017 13:42:43 GMT
#dt=0.783 s.
#2/7/2017 1:42:43 PM
#d1=2017-02-07 13:42:43 d2=2017-02-07 13:57:43 dt=0:15:00
#<type 'datetime.timedelta'>
#utc=2017-02-15 17:11:06.687000 utc-date=703703.687s
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

def str2bool(v):
    b = v.lower() in ("yes", "true", "t", "1")
    return b

def GetDSMsg(ds, format="%.3f s."):
    d = time.clock()
    dt = d - ds
    if(format==""):
        format = "%.3f s."
    
    return format % dt

def makeDateTimeFromString(strDateTime, sFormat='%a, %d %b %Y %H:%M:%S'):
    """sDate = 'Wed, 25 Jan 2017 18:31:26' sFormat='%a, %d %b %Y %H:%M:%S' 
        sDate1 = 'Wed, 25 Jan 2017 18:31:26 GMT', sFormat='%a, %d %b %Y %H:%M:%S %Z'
    """
    if(sFormat==""):
        sFormat = "%Y-%m-%d %H:%M:%S"
    d = None
    try:
        d = datetime.datetime.strptime(sDate, sFormat)
    except:
        pass 

    return d 

# Derive from Request class and override get_method to allow a HEAD request.
class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"

def downloadurlfile(url):
    filename = os.path.basename(url) 
    local_filename = url.split('/')[-1]
    arcpy.AddMessage("filename={} lf={}".format(filename, local_filename))
    # NOTE the stream=True parameter
    r = requests.get(url, verify=False,stream=True)    #requests.get(url)    #requests.get(url, stream=True, verify=True)
    #r.raw.decode_content = True
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
           
    return local_filename


if(__name__=='__main__'):
    ds = time.clock()
    #if(len(sys.argv)>1):
    #    myurl = sys.argv[1]
    myurl = arcpy.GetParameterAsText(0)
    bDownload = arcpy.GetParameterAsText(1)
    try:
        bDownload = str2bool(bDownload)
    except:
        bDownload = False


    request = HeadRequest(myurl)
   
    try:
        response = urllib2.urlopen(request)
        response_headers = response.info()
        d = response_headers.dict
        sDate = ""
        for i, k in enumerate(d):
            arcpy.AddMessage("{}. {}={}".format(i, k, d[k]))
        arcpy.AddWarning("Getting just the date element:")
        arcpy.AddMessage("{}={}".format('date', d['date']))
        arcpy.AddMessage("{}={}".format('last-modified', d['last-modified']))
        arcpy.AddMessage("dt={}".format(GetDSMsg(ds)))
        sDate = d['last-modified']
        sFormat = sFormat='%a, %d %b %Y %H:%M:%S %Z'
        d1 = makeDateTimeFromString(sDate, sFormat) 
        arcpy.AddMessage(d1) 
        arcpy.AddMessage("Testing deltaT computation with deltaT = datetime.timedelta(minutes = 15.0) sent in")
        deltaT = datetime.timedelta(minutes = 15.0)
        d2 = d1 + deltaT 
        arcpy.AddMessage("d1={} d2={} dt={}".format(d1,d2, (d2-d1)))
        d3 = datetime.datetime.utcnow()
        dt3 = d3 - d1 
        arcpy.AddMessage(type(dt3))
        arcpy.AddMessage("utc={} utc-date={}s".format(d3, dt3.total_seconds()))

        #trying to download the file:
        if(bDownload):
            pFile = downloadurlfile(myurl) 
            fileFullPath = os.path.realpath(pFile)
            arcpy.AddMessage("downloaded file is saved to: {}".format(fileFullPath))
            if(fileFullPath.endswith('.zip')):
                zf = zipfile.ZipFile(fileFullPath)
                for info in zf.infolist():
                    arcpy.AddMessage( info.filename)
                    arcpy.AddMessage( '\tComment:\t', info.comment)
                    arcpy.AddMessage( '\tModified:\t', datetime.datetime(*info.date_time))
                    arcpy.AddMessage( '\tSystem:\t\t', info.create_system, '(0 = Windows, 3 = Unix)')
                    arcpy.AddMessage( '\tZIP version:\t', info.create_version)
                    arcpy.AddMessage( '\tCompressed:\t', info.compress_size, 'bytes')
                    arcpy.AddMessage( '\tUncompressed:\t', info.file_size, 'bytes')
            else:
                with gzip.open(fileFullPath, 'rb') as f:
                     file_content = f.read()
                with gzip.open(fileFullPath, 'rb') as f_in, open('file.txt', 'w') as f_out:
                     shutil.copyfileobj(f_in, f_out)
             

    except urllib2.HTTPError, e:
        arcpy.AddError("Error code: {} {}".format(e.code, trace()))