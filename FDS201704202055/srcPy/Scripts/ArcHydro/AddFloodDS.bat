SET mypath=%~dp0
echo %mypath%
echo %mypath:~0,-1% >> C:\Python27\ArcGIS10.3\Lib\site-packages\floodds.pth
echo %mypath:~0,-1% >> C:\Python27\ArcGISx6410.3\Lib\site-packages\floodds.pth

pause