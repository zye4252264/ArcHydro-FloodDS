import sys 
import os 
import time 
import datetime
import math
import numpy
import re 

import arcpy
import apwrutils
import flooddsconfig

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



class ApPointJ:
    def __init__(self, nodeID, lineID, uplineid=apwrutils.C_MissingValue, downlineid=apwrutils.C_MissingValue):
        self.lUpLineIDs = []
        self.lDownLineIDs = []
        self.NodeID = nodeID
        self.LineID = lineID
        if(uplineid!=apwrutils.C_MissingValue): self.lUpLineIDs.append(uplineid)
        if(downlineid!=apwrutils.C_MissingValue): self.lDownLineIDs.append(downlineid)

    def processJPointsWaterLevel(self, dApLines):
        pass


class ApPoint:
    def __init__(self, pPoint, oid, lineid, z, position=apwrutils.C_MissingValue, name=""):
        self.Point = pPoint
        self.OID = oid
        self.LineID = lineid   # HYDROID of the river (line) this point resides.
        self.Position = position 
        self.Name = name
        self.Z = z
        self.Depth = apwrutils.C_MissingValue
        self.PositionDistance = 0.0
        self.BaseZ = apwrutils.C_MissingValue 
        try:
            if((self.Position==apwrutils.C_MissingValue) and ("PNT" in self.Name)):
                r = re.search('[0-9]+', name)
                f = float(r.group(0))
                f = 1.0 - (f/100.0)
                self.Position = f
        except:
            pass 

    def __del__(self):
        if((flooddsconfig.debugLevel & 4)==4):  arcpy.AddMessage("ApPoint.__del__ is called")

    def __exit__(self, type, value, traceback):
        arcpy.AddMessage("ApPoint.__exit__ is called")


class ApLine:
    ''' class to host a river line, its associated points and providd methods for estimating the waterlevel'''
    def __init__(self, pLine, oid, hid, nextdownid):
        self.Line = pLine
        self.OID = oid
        self.HydroID = hid
        self.NextdownID = nextdownid
        self.lPoints = []     # holds assoicated points, from upstream to downstream, index goes from 0 to n.
        self.IsDone = False 
        self.lUpLines = []    # holds upstream lines' HydroID
        self.lDownLines = []  # holds downstream lines' HydroID
        self.nInitPoints = 0  # holds the count of the original associated points.  For the lines that do not have initPoints, waterlevels at from/tonode points will be added from its downstream/upstream river to be used to evaluate this lines waterlevel.
        self.FromPoint = 0.0      # holds fromPoint, FromPoint.Z, (waterlevel) of the line's fromnode = self.Line.getPart(0)[0].Z
        self.ToPoint = 0.0        # holds toPoint, ToPoint.Z, (waterlevel) of the line's tonode = self.Line.getPart(len(Line.getPart)-1))
        self.FromBaseZ = apwrutils.C_MissingValue
        self.ToBaseZ = apwrutils.C_MissingValue
        self.Depth = apwrutils.C_MissingValue

    def __del__(self):
        if((flooddsconfig.debugLevel & 4)==4): arcpy.AddMessage("ApLine.__del__ is called")

    def __exit__(self, type, value, traceback):
        arcpy.AddMessage("ApLine.__exit__ is called")


    def findRelatedRiverPoints(self, dApPoints, sOpType=flooddsconfig.WLOpType.pInterpolate):
        """ for a given river, find its control points and put them in the pLine.lPointsIDs collection """
        try:
            nHID = self.HydroID
            dLeng = self.Line.getLength()

            lPoints = [p for p in dApPoints.values() if p.LineID == nHID]
            lPoints.sort(key=lambda x: x.Position, reverse=False)
            for pApPoint in lPoints:
                pApPoint.PositionDistance = pApPoint.Position * dLeng
            if(sOpType==flooddsconfig.WLOpType.pDeltaH): lPoints = lPoints[0:1]
            self.lPoints = lPoints
            self.nInitPoints = len(lPoints)
            
        except:
            pass

    def findUpDownLines(self, dApLines):
        """find upstream/downstream lines of this line from the dApLines, and save the results in self.UpLines=[], and self.DownLines=[] """
        try:
            # upstream lines
            self.lUpLines = [l.HydroID for l in dApLines.values() if l.NextdownID == self.HydroID]
            self.lDownLines =  [l.HydroID for l in dApLines.values() if l.HydroID == self.NextdownID]
        except:
            arcpy.AddWarning(trace())
             
    def computeWaterLevels(self, dApLines):
        """interpolate waterlevels and put the values onto the pLine.Z property"""
        if(self.IsDone == False):
            nPoints = len(self.lPoints) 
            if(nPoints==1):
                pApPoint = self.lPoints[0]
                dh = self.getPointDepth(pApPoint)
                pPolyline = self.addWaterDepth(dh)
                self.IsDone = True
            elif(nPoints>1):
                pPolyline = self.interpolateWaterLevels(self.lPoints)    #passing the lPoints so that the interpolateWaterLevels function can be reused later when lPoints comes from the fromNode/tonode of downstream/upstream rivers.
                self.IsDone = True
            #elif(nPoints==0):
                #..check to see if its upstream/downstream is done, if they are, add to/from waterlevel point(s) to this current line, to perform the computation.
        return pPolyline
                        
    def interpolateWaterLevels(self, lApPoints):
        """interpolate water levels based on the waterlevels on the associated ApPoints"""
        pPolylineR = None
        pPolyline = self.Line
        pSpRef = pPolyline.spatialReference
        arrPoints = arcpy.Array()
        nLeng = pPolyline.getLength()
        part = pPolyline.getPart(0)
        i1 = 0
        i2 = 1
        nPoints = len(lApPoints)
        if(nPoints>1):
            bFirstSegment = True
            bLastSegment = False
            pApPoint1 = lApPoints[i1]
            pApPoint2 = lApPoints[i2]
            slp = (pApPoint2.Z - pApPoint1.Z)/(pApPoint2.PositionDistance-pApPoint1.PositionDistance)
            for i, p in enumerate(part):    # the value p==part[i]
                pPoint = arcpy.Point() 
                try:
                    if(bFirstSegment==True):
                        dx = pApPoint1.PositionDistance - p.M
                        if(dx >=0):
                            #p.Z = pApPoint1.Z - dx*slp
                            pPoint.X = p.X
                            pPoint.Y = p.Y
                            pPoint.Z = pApPoint1.Z - dx*slp
                            pPoint.M = p.M
                            pPoint.ID = p.ID
                        else:
                            dx = p.M - pApPoint1.PositionDistance
                            bFirstSegment = False
                            #p.Z = pApPoint1.Z + dx*slp
                            pPoint.X = p.X
                            pPoint.Y = p.Y
                            pPoint.Z = pApPoint1.Z + dx*slp
                            pPoint.M = p.M
                            pPoint.ID = p.ID
                    elif((bFirstSegment==False) and (bLastSegment==False)):
                        if(p.M < pApPoint2.PositionDistance):
                            dx = p.M - pApPoint1.PositionDistance
                            #p.Z = pApPoint1.Z + dx*slp
                            pPoint.X = p.X
                            pPoint.Y = p.Y
                            pPoint.Z = pApPoint1.Z + dx*slp
                            pPoint.M = p.M
                            pPoint.ID = p.ID
                        else:
                            i1 = i1 + 1
                            i2 = i2 + 1
                            if(i2<nPoints):
                                pApPoint1 = lApPoints[i1]
                                pApPoint2 = lApPoints[i2]
                            else:
                                bLastSegment=True
                                dx = p.M - pApPoint1.PositionDistance 
                                #p.Z = pApPoint1.Z + dx*slp
                                pPoint.X = p.X
                                pPoint.Y = p.Y
                                pPoint.Z = pApPoint1.Z + dx*slp
                                pPoint.M = p.M
                                pPoint.ID = p.ID
                    elif(bLastSegment==True):
                        dx = p.M - pApPoint1.PositionDistance 
                        #p.Z = pApPoint1.Z + dx*slp
                        pPoint.X = p.X
                        pPoint.Y = p.Y
                        pPoint.Z = pApPoint1.Z + dx*slp
                        pPoint.M = p.M
                        pPoint.ID = p.ID
                except:
                    pass

                arrPoints.add(pPoint)
    
            pPolylineR = arcpy.Polyline(arrPoints,pSpRef,True,True)
            
        return pPolylineR
    
    def adjustingZValue(self, ZValue, bFirst):
        '''Adjusting the Z value of the vertices, if nInitPoints>1, i.e., all the lPoints are originally there on the line, with the observed values
           bFirst=True: adjust water levels between p0->1stWaterPoints(lPoints[0]), ZValue is p0.Z
           bFirst=False: adjust water levels between lastWaterPoints(lPoints[n])->pn, ZValue is pn.Z
        '''
        if(self.nInitPoints>1):
            if(bFirst==True):
                pApPoint = self.lPoints[0]
                dMax = pApPoint.PositionDistance
                pPolyline = self.Line
                pSpRef = pPolyline.spatialReference
                part = pPolyline.getPart(0)
                p0 = part[0]
                dm = dMax - p0.M 
                if(dm>0):
                    slp = (pApPoint.Z - ZValue)/dm
                    for i, p in enumerate(part):
                        ddx = p.M - p0.M
                        if (ddx < dm):
                            p.Z = ZValue + (slp)*(p.M - p0.M)
                        else:
                            break

                    pLineNew = arcpy.Polyline(part, pSpRef, True, True)
                    self.Line = pLineNew
            else:
                pApPoint = self.lPoints[len(self.lPoints)-1]
                dMin = pApPoint.PositionDistance
                pPolyline = self.Line
                pSpRef = pPolyline.spatialReference
                part = pPolyline.getPart(0)
                pn = part[len(part)-1]
                dm = pn.M - dMin
                if(dm>0):
                    slp = (ZValue-pApPoint.Z)/dm
                    for i, p in enumerate(part):
                        if(p.M > dMin):
                            ddx = p.M - dMin
                            p.Z = pApPoint.Z + (slp)*ddx
                    
                    pLineNew = arcpy.Polyline(part, pSpRef, True, True)
                    self.Line = pLineNew
                    
    def getPointDepth(self, pApPoint):
        """ for a given associated point (pApPoint), find waterdepth at that location of the line, i.e., pApPoint.Depth """
        """ 1. find the linesegment containing the point,
            2. via interpolation to get the line's z value at the position of pApPoint
            3. Depth = pApPoint.Z - z
        """
        if(pApPoint.Depth==apwrutils.C_MissingValue):
            pPolyline = self.Line
            dLeng = pPolyline.getLength()
            dPosition = pApPoint.PositionDistance
            part = pPolyline.getPart(0)
            dZ1 = apwrutils.C_MissingValue
            dZ2 = apwrutils.C_MissingValue
            ds = 0.1
            z = 0.0
            for i, p in enumerate(part):    # the value p==part[i] 
                try:
                    if(i==0): 
                        dLengLast = 0.0
                        dLeng = 0.0
                        dZ1 = p.Z
                        dZ2 = p.Z
                        ds = 0.1
                    else:
                        dLengLast = dLeng 
                        ds = math.sqrt((part[i].X-part[i-1].X)*(part[i].X-part[i-1].X)+(part[i].Y-part[i-1].Y)*(part[i].Y-part[i-1].Y))
                        dLeng = dLeng + ds
                        dZ1 = dZ2
                        dZ2 = p.Z

                    if(i>0):
                        if((dPosition >= dLengLast) and (dPosition <= dLeng)):
                            z = dZ1 + ((dZ2 - dZ1)/ds) * (dPosition-dLengLast)
                            pApPoint.Depth = pApPoint.Z - z       #.. pApPoint.Z=WaterSurfaceElevation.
                            break
                except:
                    ss = trace()
                    arcpy.AddMessage(ss)

        return pApPoint.Depth

    def addWaterDepth(self, depth):
        ''' for a given depth, add it to all vertices on the line's p.Z, i.e., p.Z = p.Z + depth''' 
        pPolyline = self.Line
        pSpRef = pPolyline.spatialReference
        arrPoints = arcpy.Array()
        part = pPolyline.getPart(0)
        for i, p in enumerate(part):    # the value p==part[i] 
            try:
                pPoint = arcpy.Point()
                pPoint.X = p.X
                pPoint.Y = p.Y
                pPoint.Z = p.Z + depth
                pPoint.M = p.M
                pPoint.ID = p.ID
                #p.Z = p.Z + depth
                arrPoints.add(pPoint)
            except:
                ss = trace()
                arcpy.AddMessage(ss)
        pPolylineR = arcpy.Polyline(arrPoints, pSpRef, True, True)

        return pPolylineR

#Main class for WaterLevel estimates.
class ApWaterLevelOnRiver:
    #variables:
    C_OK = 'OK'
    C_NOTOK = 'NOTOK'
    C_WLFld = 'WL_'
    FN_Elev = "Elev"

    def __init__(self):
        self.DebugLevel = 0
   
    def __exit__(self, type, value, traceback):
        if((self.DebugLevel & 2) ==2):
            apwrutils.Utils.ShowMsg(self.thisFileName() + " completed at " + time.ctime()) 
             
    def thisFileName(self):
        import inspect
        return inspect.getfile(inspect.currentframe())
    # Load the configuration xml.
    def LoadConfigXML(self, sFileName):
        if(sFileName.find(os.sep) < 0):
            sXmlFile = sys.path[0] + os.sep + sFileName
        doc = xml.dom.minidom.parse(sXmlFile) 
        try:
            oNode = doc.getElementsByTagName("DebugLevel")[0]
            if(oNode!=None):
                self.DebugLevel=int(oNode.firstChild.nodeValue)
        except:
            self.DebugLevel=0

        del doc
    
    #def execute(self, parameters, messages):
    def execute(self, inStream, inPoints, inZField, sConfMatch=None, sOpType=flooddsconfig.WLOpType.pInterpolate, pScratchWorkspace=None):
    #def computeWaterLevelOnRiver(self, inStream, inPoints, inZField, sConfMatch=None, sOpType=flooddsconfig.WLOpType.pInterpolate):
        ''' main function computes water levels '..ye, @1/19/2016 3:47:22 PM on ZYE1 '''
        sOK = self.C_OK
        if((flooddsconfig.debugLevel & 2)==2): arcpy.AddMessage("in waterlevelonriver: os.environ['TMP']={}, os.environ['TEMP']={}".format(os.environ['TMP'], os.environ['TEMP']))
        #arcpy.AddMessage("Here in computeWaterLevel")
        #pEditor = None
        if(pScratchWorkspace!=None):
            arcpy.env.scratchWorkspace = pScratchWorkspace

        lRslt = apwrutils.Utils.getFCNameWkSFDS(inStream)
        sWKS = lRslt[1]
        if(len(lRslt)>2):
            sWKS = os.path.join(sWKS, lRslt[2])
        
        sOut3DName = os.path.basename(inStream)
        sOut3DName = sOut3DName + flooddsconfig.C_UL + inZField
        
        sOut3DFullName = os.path.join(sWKS, sOut3DName) 
        ds = time.clock()
        if arcpy.Exists(sOut3DFullName): arcpy.Delete_management(sOut3DFullName)
        arcpy.CopyFeatures_management(inStream, sOut3DFullName)
        if((flooddsconfig.debugLevel & 1)==1): 
            arcpy.AddMessage("Create output feature class {} from input {}.  dt={}".format(inStream, sOut3DFullName, apwrutils.Utils.GetDSMsg(ds)))

        cellsize = arcpy.env.cellSize
        ds = time.clock()
        dApPoints = dict()    #..Holding the WaterLevelPoints, key=p.OID, value=p, p.Point, p.OID, p.LineID, p.Z (water level), p.Position (DistFromPoint0/LengthOfLine), 
        dApLines = dict()     #..Holding the river lines, key=l.HydroID(=p.LineID), value=l (Line), l.HydroID, l.Shape  
        dApPointsJ = dict()
        line3DName = os.path.basename(sOut3DFullName)
        
        try:
            pWorkspace = apwrutils.Utils.getWorkspace(sOut3DFullName)
            ds = time.clock()
            #copy features record by record:
            oDesc = arcpy.Describe(sOut3DFullName)
            pSpRef = oDesc.spatialReference
            FN_OID = oDesc.OIDFieldName
            r = arcpy.GetCount_management(inPoints)
            nCnt = int(r[0])
            iCnt = 0
            #nMod = nCnt/100
            #if((nMod<1) or (nCnt < 100)): nMod = 1
            #arcpy.SetProgressor('step', "Collecting {} control points.".format(nCnt), 0, nCnt, nMod) 
            iCnt = 0
            oDescPoints = arcpy.Describe(inPoints)
            FN_OIDPnt = oDescPoints.OIDFieldName 

            lRivFields = [apwrutils.FN_ShapeAt, FN_OID, apwrutils.FN_HYDROID, apwrutils.FN_NEXTDOWNID]
            lPntFields = [apwrutils.FN_ShapeAt, FN_OIDPnt, apwrutils.FN_LINEID, inZField]
            bHasName = apwrutils.Utils.FieldExist(oDescPoints, apwrutils.FN_NAME)
            if(bHasName) : lPntFields.append(apwrutils.FN_NAME) 
            bHasFNode = apwrutils.Utils.FieldExist(oDesc, apwrutils.FN_FROMNODE)
            if(bHasFNode): lRivFields.append(apwrutils.FN_FROMNODE)
            bHasTNode = apwrutils.Utils.FieldExist(oDesc, apwrutils.FN_TONODE)
            if(bHasTNode): lRivFields.append(apwrutils.FN_TONODE)

            #1. Collecting points
            with arcpy.da.SearchCursor(inPoints, lPntFields) as rows:
                for row in rows:
                    iCnt = iCnt+1
                    if(bHasName):
                        #   ApPoint(pPoint,Pnt.OID,RiverOID, inZvalue(WaterLevel), Position, Name)
                        p = ApPoint(row[0],row[1], row[2], row[3], apwrutils.C_MissingValue, row[4])
                    else:
                        p = ApPoint(row[0],row[1], row[2], row[3], apwrutils.C_MissingValue)
                    dApPoints.setdefault(row[1], p)
                      
            if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage("{} points added to dApPoints. dt={}".format(len(dApPoints),apwrutils.Utils.GetDSMsg(ds)))
            #2. Collecting lines.
            nCntLine = int(arcpy.GetCount_management(sOut3DFullName)[0])
            #nModLine = nCntLine/100
            #if((nModLine<1) or (nCntLine < 100)): nModLine = 1
            #arcpy.SetProgressor('step', "Collecting {} river lines.".format(nCntLine), 0, nCntLine, nModLine) 
            iCntLine = 0
            with arcpy.da.SearchCursor(sOut3DFullName, lRivFields) as rows:
                for row in rows:
                    #if((iCntLine % nModLine)==0):
                    #    sMsg = "Processing: " + str(iCntLine+1) + " of " + str(nCntLine) + " recs. dt=" + apwrutils.Utils.GetDSMsg(ds)
                    #    arcpy.SetProgressorLabel(sMsg)
                    #    arcpy.SetProgressorPosition(iCntLine+1)
                    #    ds = time.clock()
                    iCntLine = iCntLine+1
                    pLine = ApLine(row[0], row[1], row[2], row[3])
                    pLine.findRelatedRiverPoints(dApPoints, sOpType)
                    dApLines.setdefault(pLine.HydroID, pLine)

            #3. Collecting the junction points. 
            if(bHasFNode and bHasTNode):
                with arcpy.da.SearchCursor(sOut3DFullName, lRivFields) as rows:
                    for row in rows:
                        try:
                            nRID = int(row[lRivFields.index(apwrutils.FN_HYDROID)])
                            nFNID = int(row[lRivFields.index(apwrutils.FN_FROMNODE)])
                            if((nFNID in dApPointsJ)==False):
                                #__init__(self, nodeID, lineID, uplineid=apwrutils.C_MissingValue, downlineid=apwrutils.C_MissingValue):
                                pApPointJ = ApPointJ(nFNID, nRID, apwrutils.C_MissingValue, nRID)
                                dApPointsJ.setdefault(nFNID, pApPointJ) 
                            else:
                                pApPointJ = dApPointsJ[nFNID]
                                pApPointJ.lDownLineIDs.append(nRID)
                                
                            nTNID = int(row[lRivFields.index(apwrutils.FN_TONODE)])
                            if((nTNID in dApPointsJ)==False):
                                pApPointJ = ApPointJ(nTNID, nRID, nRID, apwrutils.C_MissingValue)
                                dApPointsJ.setdefault(nTNID, pApPointJ) 
                            else:
                                pApPointJ = dApPointsJ[nTNID]
                                pApPointJ.lUpLineIDs.append(nRID)  
                        except:
                            pass
                
                    
            if((flooddsconfig.debugLevel & 2)==2):
                for pApPointJ in dApPointsJ.values():
                    arcpy.AddMessage("NodeID:{} RiverID:{} UpStreams:{} DownStreams:{}".format(pApPointJ.NodeID, pApPointJ.LineID, pApPointJ.lUpLineIDs, pApPointJ.lDownLineIDs))
                                       
            
            # list all the lines
            if((flooddsconfig.debugLevel & 2)==2):
                for k, l in iter(dApLines.items()):
                    arcpy.AddMessage("dApLines'Key:{}. l.HydroID={} .OID={} .NextdownID={} .nInitPoints={} nPoints={}".format(k, l.HydroID, l.OID, l.NextdownID, l.nInitPoints, len(l.lPoints) ))
            # list all the points - the reason it is listed and not when they are created is that p.PositionDistance is not populated until the pLine.findRelatedRiverPoints is called.
            if((flooddsconfig.debugLevel & 2)==2):
                for k, p in iter(dApPoints.items()):
                    arcpy.AddMessage("{}. {} {} {} {} {} {}".format(k, p.OID, p.LineID, p.Position, p.PositionDistance, p.Name, p.Point))
                    
                    
            #4. Finding the relationships between the lines:
            for l in dApLines.values():
                l.findUpDownLines(dApLines)
                if((flooddsconfig.debugLevel & 2)==2):
                    arcpy.AddMessage("{} .lUpLines={} .lDownLines={}".format(l.HydroID, l.lUpLines, l.lDownLines))
                     
            #5. Computing waterlevels - set it to the Z property on the pApLine
            #  .1 loop through the dApLines to compute the water levels for all the lines with len(pApLine.lPoints) > 0
            #  .2 loop through all the dApLines with len(pApLine.lPoints)==0, and use the upstream/or downstream's tonode/fromnode's waterlevel to estemate the waterlevel, untill all the rivers are computed.
            #  .3 if sConfMatch!=None, perform confluence water match operation.
            for ii in range(100):
                #4.1. Computing all the dApLines with associated points, either the original ones or the ones comming from up/downstream of computed lines.
                for pLine in dApLines.values():
                    if ((pLine.IsDone == False) and (len(pLine.lPoints)>0)):
                        pPolyline0 = pLine.Line   #holds the original point to get their original Z.                 
                        parts0 = pPolyline0.getPart(0)
                        pLine.FromBaseZ = parts0[0].Z
                        pLine.ToBaseZ = parts0[len(parts0)-1].Z
                        # pLine.computeWaterLevels returns a polyline with updated .Z value, 
                        pPolyline = pLine.computeWaterLevels(dApLines)   #..pass dApLines because it can be used find upstream/downstream lines of the pLine for waterlevel computation.
                        pLine.Line = pPolyline
                        parts = pPolyline.getPart(0)  
                        pLine.FromPoint = parts[0]
                        pLine.ToPoint = parts[len(parts)-1]

                if((flooddsconfig.debugLevel & 4)==4):
                    lLines = [pLine for pLine in dApLines.values() if (pLine.IsDone == True)]
                    nDone = len(lLines)
                    nNotDone = len(dApLines) - nDone
                    sMsg = "Pass {},  Done={}, NotDone={}".format(ii, nDone, nNotDone)
                    arcpy.AddMessage(sMsg) 
                bAllDone = True
                for pLine in dApLines.values():
                    if(pLine.IsDone == False):
                        bAllDone = False
                        if(len(pLine.lUpLines)>0):
                            pLineUp = dApLines[pLine.lUpLines[0]]
                            if(pLineUp.IsDone==True):
                                #   ApPoint(pPoint,Pnt.OID,RiverOID, inZvalue(WaterLevel), Position, Name)
                                pApPointUp = ApPoint(pLineUp.ToPoint,apwrutils.C_MissingValue, pLine.HydroID, pLineUp.ToPoint.Z,0.0)
                                pApPointUp.PositionDistance = 0.0
                                pApPointUp.BaseZ = pLineUp.ToBaseZ
                                pApPointUp.Depth = pApPointUp.Z - pApPointUp.BaseZ         #..Depth is used if this is only a single point on the pLine.                            
                                pLine.lPoints.append(pApPointUp)
                        if(len(pLine.lDownLines)>0):
                            pLineDown = dApLines[pLine.lDownLines[0]]
                            if(pLineDown.IsDone==True):   #..Adding Z of fromnode of the downstream line to make this line's waterlevelpoint, at the end of this line (pLine) 
                                pApPointDown = ApPoint(pLineDown.FromPoint, apwrutils.C_MissingValue, pLine.HydroID, pLineDown.FromPoint.Z, 1)
                                pApPointDown.PositionDistance = pLine.Line.getLength()
                                pApPointDown.BaseZ = pLineDown.FromBaseZ
                                pApPointDown.Depth = pApPointDown.Z - pApPointDown.BaseZ   #..Depth is used if this is only a single point on the pLine.                            
                                pLine.lPoints.append(pApPointDown)

                if(bAllDone==True):
                    if((flooddsconfig.debugLevel & 1)==1): arcpy.AddMessage("All {} lines' waterlevels are estimated.".format(len(dApLines))) 
                    break;                                

            
            #6. Recalculate confluence points elevations.
            try:
                if((bHasFNode and bHasTNode) and (sConfMatch!=flooddsconfig.ConfMatch.pNone)):
                    ZValue = apwrutils.C_MissingValue
                    for pApPointJ in dApPointsJ.values():
                        lUpLines = pApPointJ.lUpLineIDs
                        lDownLines = pApPointJ.lDownLineIDs
                        #..Collecting the junction points:
                        lPointsJ = []   # points to collect Z values of the connected line's Z at this junction pApPointJ.
                        for id in lUpLines:
                            try:
                                pUpLine = dApLines[id]
                                part = pUpLine.Line.getPart(0)
                                pn = part[len(part)-1]
                                p = arcpy.Point() 
                                p.X = pn.X
                                p.Y = pn.Y
                                p.M = pn.M
                                p.Z = pn.Z 
                                lPointsJ.append(p)
                            except:
                                pass

                        for id in lDownLines:
                            try:
                                pDownLine = dApLines[id]
                                part = pDownLine.Line.getPart(0)
                                p0 = part[0]
                                p = arcpy.Point() 
                                p.X = p0.X
                                p.Y = p0.Y
                                p.M = p0.M
                                p.Z = p0.Z 
                                lPointsJ.append(p)
                            except:
                                pass
                        #..Recompute the Z value only if junction has nPoints (number of lines connecting to the point)>1
                        nPoints = len(lPointsJ)
                        if(nPoints>1):
                            ZValue = apwrutils.C_MissingValue
                            for p in lPointsJ:
                                if(sConfMatch==flooddsconfig.ConfMatch.pAvg):
                                    if(ZValue==apwrutils.C_MissingValue):
                                        ZValue = p.Z 
                                    else:
                                        ZValue = ZValue + p.Z
                                elif(sConfMatch==flooddsconfig.ConfMatch.pMax):
                                    if(ZValue==apwrutils.C_MissingValue):
                                        ZValue = p.Z 
                                    else:
                                        if(ZValue<p.Z):
                                            ZValue = p.Z
                                elif(sConfigMatch==flooddsconfig.ConfMatch.pMin):
                                    if(ZValue==apwrutils.C_MissingValue):
                                        ZValue = p.Z 
                                    else:
                                        if(ZValue>p.Z):
                                            ZValue = p.Z
                            # end of for p in lPointsJ:
                            if(sConfMatch==flooddsconfig.ConfMatch.pAvg):
                                ZValue = ZValue/nPoints
                            #..make sure the ZValue is properly set before updating the ZValues.  
                            if(ZValue!=apwrutils.C_MissingValue):
                                #..Update the Z values on the Junction points (UpstreamLines on the last point, DownstreamLines on the first point):
                                for id in lUpLines:
                                    try:
                                        pApLine = dApLines[id]
                                        pSpRef = pApLine.Line.spatialReference
                                        part = pApLine.Line.getPart(0)
                                        part[len(part)-1].Z = ZValue
                                        pNewLine = arcpy.Polyline(part, pSpRef, True, True)
                                        pApLine.Line = pNewLine
                                        if(pApLine.nInitPoints>1):
                                            pApLine.adjustingZValue(ZValue,False)

                                    except:
                                        pass

                                for id in lDownLines:
                                    try:
                                        pApLine = dApLines[id]
                                        pSpRef = pApLine.Line.spatialReference
                                        part = pApLine.Line.getPart(0)
                                        part[0].Z = ZValue 
                                        pNewLine = arcpy.Polyline(part, pSpRef, True, True)
                                        pApLine.Line = pNewLine
                                        if(pApLine.nInitPoints>1):
                                            pApLine.adjustingZValue(ZValue,True)            
                                    except:
                                        pass

            except:     # ON THIS BLOCK: if((bHasFNode and bHasTNode) and (sConfMatch!=flooddsconfig.ConfMatch.pNone)):
                pass                  
              
            #7. update river's pPolyline
            #arcpy.SetProgressor('step', "Updating waterlevel on {} river lines.".format(nCntLine), 0, nCntLine, nModLine) 
            iCntLine = 0
            #pEditor = arcpy.da.Editor(pWorkspace)
            #pEditor.startEditing (False, True)
            with arcpy.da.UpdateCursor(sOut3DFullName, [apwrutils.FN_ShapeAt, apwrutils.FN_HYDROID]) as upRows:
                for upRow in upRows:
                    #if(((flooddsconfig.debugLevel & 1)==1) and ((iCntLine % nModLine)==0)):
                    #    sMsg = "Updating: " + str(iCntLine+1) + " of " + str(nCntLine) + " recs. dt=" + apwrutils.Utils.GetDSMsg(ds)
                    #    arcpy.SetProgressorLabel(sMsg)
                    #    arcpy.SetProgressorPosition(iCntLine+1)
                    #    ds = time.clock()
                    iCntLine = iCntLine+1
                    hid = upRow[1]
                    pApLine = dApLines[hid]
                    pPolyline = pApLine.Line
                    upRow[0] = pPolyline
                    upRows.updateRow(upRow)
                    if((flooddsconfig.debugLevel & 1)==1):
                        sMsg = "Updating: " + str(iCntLine) + " of " + str(nCntLine) + " recs. dt=" + apwrutils.Utils.GetDSMsg(ds)
                        arcpy.AddMessage(sMsg)
                        
            # update river's pPolyline   
        except arcpy.ExecuteError:
            sOK = str(arcpy.GetMessages(2))
            arcpy.AddError(sOK)
        except:
            sOK = str(trace())
            arcpy.AddError(sOK)
        finally:        
            #if(pEditor!=None):
            #    pEditor.stopEditing(True)
            del dApLines
            del dApPoints

        if(sOK==apwrutils.C_OK):
            tReturn = (sOK, sOut3DFullName)
        else:
            tReturn = (sOK)
         
        return tReturn


if(__name__=='__main__'):
    #..ye, @1/05/2016 3:29:46 PM on ZYE1
    pFLOut = ''
    try:
        inStream = arcpy.GetParameterAsText(0)     #inStream
        inPoints = arcpy.GetParameterAsText(1)     #10/85 points, 10%-85% measured from downstream.
        inZField = arcpy.GetParameterAsText(2)
        inConfMatch = arcpy.GetParameterAsText(3) 
        inOpType = arcpy.GetParameterAsText(4)
        if(flooddsconfig.debugLevel): arcpy.AddMessage("flooddsconfig.debugLevel={}".format(flooddsconfig.debugLevel))
        if((flooddsconfig.debugLevel & 1)==1): 
            for i in range(0,len(sys.argv)-2):
                arcpy.AddMessage("arcpy.GetParameterAsText({})=>{}".format(i,arcpy.GetParameterAsText(i))) 

        oProcessor = ApWaterLevelOnRiver()
        lResults = oProcessor.execute(inStream,inPoints,inZField,inConfMatch,inOpType)
        if(lResults[0]==apwrutils.C_OK):
            pFCOut = lResults[1]
            line3DName = os.path.basename(pFCOut)
            pFLOut = arcpy.management.MakeFeatureLayer(pFCOut, line3DName)
         
    except arcpy.ExecuteError:
        arcpy.AddError(str(arcpy.GetMessages(2)))
    except:
        arcpy.AddError(str(trace()))
        arcpy.AddError(str(arcpy.GetMessages(2)))
    finally:
        if(pFLOut!=''):
            arcpy.SetParameterAsText(5, pFLOut)
        #del oProcessor
        dt = datetime.datetime.now()
        print ( 'Finished at ' + dt.strftime("%Y-%m-%d %H:%M:%S"))

