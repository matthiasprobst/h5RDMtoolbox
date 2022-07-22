#!MC 1410
$!READDATASET  '"-F" "5" "C:\Users\da4323\Documents\programming\git\h5RDMtoolbox\doc\h5wrapper\tec.hdf" "C:\Users\da4323\Documents\programming\git\h5RDMtoolbox\doc\h5wrapper\tec.hdf" "C:\Users\da4323\Documents\programming\git\h5RDMtoolbox\doc\h5wrapper\tec.hdf" "C:\Users\da4323\Documents\programming\git\h5RDMtoolbox\doc\h5wrapper\tec.hdf" "C:\Users\da4323\Documents\programming\git\h5RDMtoolbox\doc\h5wrapper\tec.hdf" "-D" "5" "/Z0/" "/Z1/" "/Z2/" "/Z3/" "/Z4/" "-G" "6" "X" "Y" "Z" "u" "v" "w"  "-K" "1" "1" "1"'
  DATASETREADER = 'HDF5 Loader'
  READDATAOPTION = NEW
  RESETSTYLE = YES
  ASSIGNSTRANDIDS = NO
  INITIALPLOTTYPE = CARTESIAN3D
  INITIALPLOTFIRSTZONEONLY = NO
  ADDZONESTOEXISTINGSTRANDS = NO
  VARLOADMODE = BYNAME
$!THREEDAXIS XDETAIL{VARNUM = 1}
$!THREEDAXIS YDETAIL{VARNUM = 2}
$!THREEDAXIS ZDETAIL{VARNUM = 3}
$!EXTENDEDCOMMAND
   COMMANDPROCESSORID = 'Strand Editor'
COMMAND = 'ZoneSet=1-5;MultiZonesPerTime=TRUE;ZoneGrouping=Time;GroupSize=5;AssignStrands=TRUE;StrandValue=5;AssignSolutionTime=TRUE;TimeValue=0;DeltaValue=1;TimeOption=Automatic;'