import os
import arcpy
import apwrutils
if(__name__=='__main__'):
    ''' copy features from one featureclass to a newlocation with copied features sorted in the order of the specified field '''
    pFCSrc = arcpy.GetParameterAsText(0)
    sOrderFldName = arcpy.GetParameterAsText(1) 
    bASC = arcpy.GetParameterAsText(2)
    sFlds = arcpy.GetParameterAsText(3)
    pWorkSpace = apwrutils.Utils.getWorkspace(pFCSrc)
    oDesc = arcpy.Describe(pFCSrc)
    
    sName = oDesc.name
    oidName = oDesc.oidFieldName
    if(sOrderFldName==None or sOrderFldName=='#'): sOrderFldName = oidName 
    arcpy.AddMessage(sFlds)
    lFldsToKeep = sFlds.split(";")
    oFldInfo = arcpy.FieldInfo()
    
    lFlds = arcpy.ListFields(pFCSrc)
    for fld in lFlds:
        if(fld.name in lFldsToKeep):
            oFldInfo.addField(fld, fld, "VISIBLE","")
        else:
            oFldInfo.addField(fld, fld, "HIDDEN","")
            arcpy.AddMessage("Hidden:{}".format(fld.name))

    if(bASC=='true'): 
        sORDER = "ASC"
    else:
        sORDER = "DESC"
    arcpy.AddMessage("Order by keyword: {} {}".format(sORDER,bASC))
    pFL = "FL_{}".format(sName) 
    sWhere = "{} < 0".format(oidName)
    #arcpy.MakeFeatureLayer_management(pFCSrc, pFL, sWhere, None)
    arcpy.MakeFeatureLayer_management(pFCSrc, pFL, sWhere, None, oFldInfo)
    llFlds = arcpy.ListFields(pFL) 
    for ooFld in llFlds:
        arcpy.AddMessage("{}".format(ooFld.name))

    sOutName = "{}_Rev".format(sName)

    pFCTrg = os.path.join(pWorkSpace, sOutName)    
    arcpy.CopyFeatures_management(pFL, pFCTrg) 
    lFlds = arcpy.ListFields(pFCSrc)
    lFldNames = []
    for oFld in lFlds:
        if (oFld.name != 'Raster'):
            lFldNames.append(oFld.name)
        if(oFld.name.upper() == "SHAPE"):
            lFldNames.append("{}@".format(oFld.name))
                           
    with arcpy.da.InsertCursor(pFCTrg, lFldNames) as inRows:
        with arcpy.da.SearchCursor(pFCSrc, lFldNames, None, None, False, sql_clause=(None, "Order By {} {}".format(sOrderFldName, sORDER) )) as rows: 
            for row in rows:
                inRows.insertRow((row))
   
    pFLOut = sOutName 
    arcpy.MakeFeatureLayer_management(pFCTrg, pFLOut)
    arcpy.SetParameterAsText(4, pFLOut) 

