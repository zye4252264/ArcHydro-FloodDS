# D:\10Data\TXDEM\FP.gdb\FloodEventTS D:\10Data\TXDEM\FP.gdb\RatingCurveTableP 'Q to H'

import os
import sys 
import time 
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


def GetZValue(q, dQZRelations):
    z = 0
    i = 0
    bFound = False
    z0 = 0   # qv @ i
    z1 = 0   # qv @ (i-1)
    q0 = 0
    q1 = 0
    try:
        lqv = sorted(dQZRelations.keys())
        Zmin = dQZRelations[lqv[0]]
        Zmax = dQZRelations[lqv[len(lqv)-1]]
        iCnt = len(lqv)
        for i in range(0,iCnt,1):
            qv = lqv[i]
            if(q<qv):
                if(i==0):
                    z0=Zmin
                    q0=0
                    q1=qv
                    z1=dQZRelations[qv]
                    bFound = True
                else:
                    q0 = lqv[i-1]
                    q1 = qv
                    z0=dQZRelations[q0]
                    z1=dQZRelations[q1]
                    
                    bFound = True
                break
        if(bFound==True):
            if(q1!=q0):
                z = z0 + ((z1-z0)/(q1-q0))*(q-q0)
            else:
                z = z1
        else:
            z = Zmax

    except:
        z = Zmin

    return z      

#..inputs: 1. FloodEventTable (FeatureID, Q, H) via FloodEventTable.FeatureID = RatingCurveTable.XID
#  2. RatingCurveTable (XID, H, Q)
          
if(__name__=='__main__'):
    FN_Q = "Q"
    FN_H = "H"
    FN_XID = "XID"
    FN_FID = "FeatureID" 

    tblFloodEvent = arcpy.GetParameterAsText(0)
    tblRatingCurve = arcpy.GetParameterAsText(1) 
    OpMethod = arcpy.GetParameterAsText(2) 
    QFldName = arcpy.GetParameterAsText(3)
    HFldName = arcpy.GetParameterAsText(4)

    if (QFldName == '#' or not QFldName):
        QFldName = FN_Q
    
    FN_Q = QFldName
    if (HFldName == '#' or not HFldName):
        HFldName = FN_H
    
    FN_H = HFldName

    bQ2H = (OpMethod == 'Q to H')
    #..Add H or Q to the FloodEvent
    dQHFields = {FN_H: "DOUBLE", FN_Q: "DOUBLE"}
    apwrutils.Utils.addFields(tblFloodEvent, dQHFields)

    if(bQ2H==True):
        srcFld = FN_Q 
        trgFld = FN_H 
    else:
        srcFld = FN_H 
        trgFld = FN_Q 
    

    nRows = int(arcpy.GetCount_management(tblFloodEvent)[0])
    nMod = 1   #'.. statusbar is stepped per nMod of times in a loop.
    if(int(nRows) > 1000):
        nMod = int(nRows) / 100
    else:
        if(nRows > 100):
            nMod = int(nRows) / 10
        else:
            nMod = 1

    arcpy.SetProgressor("step","Calculating {}->{}".format(srcFld, trgFld), 0, nRows,1)
    dxid2QH = dict()  # dict of dSrc2Trg sorted asc on Src.
    i = 0
    ds1 = time.clock()
    with arcpy.da.UpdateCursor(tblFloodEvent, [FN_FID, srcFld, trgFld]) as upRows:
        for upRow in upRows:
            i = i + 1 
            sMsg = "Process {}->{} on {} of {} recs. dt={}".format(srcFld, trgFld, i, nRows, apwrutils.Utils.GetDSMsg(ds1))
            #apwrutils.Utils.ShowMsg(sMsg)
            if((i % nMod)==0):
                arcpy.SetProgressorLabel(sMsg)
                arcpy.SetProgressorPosition(i)

            xid = upRow[0]
            srcV = upRow[1]
            if((xid in dxid2QH)==False):
                dsrc2trg = dict()                
                sWhere = "{}={}".format(FN_XID, xid)   
                with arcpy.da.SearchCursor(tblRatingCurve, [srcFld, trgFld], sWhere) as rows:
                    for row in rows:
                        ssrcV = row[0]
                        strgV = row[1]
                        try:
                            dsrc2trg.setdefault(ssrcV, strgV)
                        except:
                            pass  
                         
                    try:
                        dxid2QH.setdefault(xid, dsrc2trg)
                    except:
                        pass  
            else:
                dsrc2trg = dxid2QH[xid]
            trgV = GetZValue(srcV, dsrc2trg)
            upRow[2] = trgV
            upRows.updateRow(upRow)
    sMsg = "Process {}->{} on {} recs. dt={}".format(srcFld, trgFld, nRows, apwrutils.Utils.GetDSMsg(ds1))
    arcpy.SetProgressorLabel(sMsg)
    arcpy.AddMessage(sMsg) 
    arcpy.SetParameterAsText(5, tblFloodEvent)


