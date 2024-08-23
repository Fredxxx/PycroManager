# class containing some (hopefully all, at some point 20230207`) parameters for image acquisition
import json
import os
import numpy as np


class Mic:
    """generic class to define camera specific properties callable via uManager"""
    def __init__(self, name):
        # general
        self.name = name                                    # name the entity
        self.initFileJ = []                                 # initialisation file as JSON data
        self.initFileP = "files\\initFile.txt"              # initialisation file path
        self.cwd = "C:\\temp"                               # current working directory

        # micromanager
        self.core = []                                      # uManager core
        self.lDev = []                                      # list of loaded devices in uManager
        self.liveImg = False                                # should image be displayed during acquisition
        self.laserList = []                                 # contains all lasers loaded by uManager
        self.laser1Power = "n/a"                            # current laser power of laser 1
        self.laser2Power = "n/a"                            # current laser power of laser 2
        self.laser3Power = "n/a"                            # current laser power of laser 3
        self.laser4Power = "n/a"                            # current laser power of laser 4
        self.AOTF1 = "n/a"                                  # current AOTF transmission of laser  1
        self.AOTF2 = "n/a"                                  # current AOTF transmission of laser 2
        self.AOTF3 = "n/a"                                  # current AOTF transmission of laser 3
        self.AOTF4 = "n/a"                                  # current AOTF transmission of laser 4
        self.zLowLim = float(0) # TODO is this used?
        self.zUppLim = float(0) # TODO is this used?
        self.filePath = "C:\\temp"                          # path to save data
        self.fileName = "scan"                              # file name of save data
        self.LUTstage1 = "files\\MIPOS100PL.txt"            # path of look up table stage 1
        self.LUTstage2 = "files\\MCL.txt"                   # path of look up table stage 2
        self.lutGalvo = np.empty([2, 2])                    # galvo look up table
        self.lut = np.empty([2, 2])                         # look up table of current stage
        self.selfconfig = "MMConfig_demo.cfg"               # uManager config file
        self.umConfig1 = "\\uManager\\Micro-Manager-2.0_20230524\\MMConfig_demo.cfg"      # configuration file 1
        self.umConfig2 = "\\uManager\\Micro-Manager-2.0_20230524\\MMConfig_demo.cfg"      # configuration file 2
        self.umApp = "\\uManager\\Micro-Manager-2.0_20230524"     # directory of uManager
        self.umPort1 = 4827                                 # python - uManager communication port 1
        self.umPort2 = 4847                                 # python - uManager communication port 2
        self.headless = False                               # is 2. cam active

        # niDAQ
        self.task = []                                      # instance of task
        self.triggerTimingMs = float(1) # TODO is this used?
        self.delayMs = float(0) # TODO is this used?

        # camera
        self.expTime = float(100)                    # in ms
        self.addTime = float(12)  # in ms added time to exposure for single acquisition event (eg cam readout,...)
        self.delay = float(0)                        # delay in hardware hook function
        self.expTime2 = float(100) # in ms for second camera

        # time stack
        self.tInt = float(5)                         # time interval
        self.tUnit = 's'                             # time unit for time interval
        self.tSteps = int(0)                         # number of t steps

        # z scan
        self.zRange = float(5)                       # range of z scan in um
        self.numStepsZ = int(15)                     # number of z steps
        self.posStartZ = float(0)                    # z scan start position
        self.posEndZ = float(0)                      # z scan end position
        self.stepSizeZ = float(0)                    # z scan step size
        self.InitialStepV = float(0)                 # pre scan z device position
        self.scanPattern = []                        # scan pattern

        # DAQ signal
        self.uptimeTTL = int(25)                     # TTL uptime in percentage
        self.amplitudeTTL = float(5)                 # voltage amplitude of TTL
        self.digEvent = int(40)     # digits per TTL event (how many points the DAQ is reserving for one TTL pulse)

        # MDA
        self.mdaOrder = 'tz'                         # order of multidimensional acquisition
        self.acqFlag = True                          # acquisition Flag to abort acquisition
        self.acqFlagH = True                         # acquisition Flag helper to close acquisition, when finished
        self.progressEmit = []                       # progress emit signal for reporting progress between threads
        self.progTick = 0                            # progress emit factor (progTick * image number = progress in %)
        self.acq = []                                # acquisition entity
        self.acq2 = []                               # acquisition entity of second camera
        self.acqMode = 'light sheet'                 # define the acquisition mode

        # devices
        self.stageZ = []                             # focus device
        self.stageSeq = []                           # sequencing stage
        self.camera = []                             # camera

        # GUI details
        self.mainGUIgeo = []                        # details about geometry of GUI on screen

        # SLM, screens
        self.slmIm = []                             # hologram of SLM
        self.screen0 = []                           # main screen
        self.screen1 = []                           # second screen (e.g. SLM)

        # scan galvo in light sheet
        self.galvoStart = float(-25)                # galvo start postition
        self.galvoEnd = float(25)                   # galvo end position
        self.galvoPos = float(0)                    # current galvo position
        self.galvoFreq = int(100)                 # scan frequency (only adjustment mode)
        self.galvoReps = int(100)                 # reps of scan

        # SLM
        self.waveCorr1 = []                         # wavefront correction wavelength 1
        self.waveCorr2 = []                         # wavefront correction wavelength 2
        self.maxPhase1 = int(185)                   # number of pixel for 2pi (491nm)
        self.maxPhase2 = int(222)                   # number of pixel for 2pi (590nm)
        self.SLMactive = False                      # SLM mode

        # stage, calibration
        self.aoMod = "Dev1/ao0"                     # analog output channel name
        self.aiMon = "Dev1/ai0"                     # analog input channel name
        self.calibPath = "files\calib.txt"          # path of calibration file
        self.modMin = 0                             # minimum analog voltage
        self.modMax = 10                            # maximum analog voltage
        self.umMin = 0                              # minimum distance in um
        self.umMax = 150                            # maximum distance in um
        self.umAccu = 0.01                          # accuracy of steps
        self.runMeIns = []                          # thread instance for calibration


def initMic(mic, json):
    mic.initFileJ = json
    mic.waveCorr1 = json.get("SLM").get("waverfront correction 1")
    mic.waveCorr2 = json.get("SLM").get("waverfront correction 2")
    mic.maxPhase1 = json.get("SLM").get("maxPhase 1")
    mic.maxPhase2 = json.get("SLM").get("maxPhase 2")


def getMic(name):
    mic = Mic(name)
    return mic


def writeJSON(x, fileP):
    with open(fileP, 'w') as fOut:
        json.dump(x, fOut, ensure_ascii=False, indent=4)


def writeJSONvar(fileP, key, var):
    data = readJSON(fileP)
    data[key] = var
    with open(fileP, 'w') as fOut:
        json.dump(data, fOut, ensure_ascii=False, indent=4)


def readJSON(fileP):
    if os.path.exists(fileP):
        with open(fileP, 'r') as fIn:
            data = json.load(fIn)
    else:
        print("Err: 'parameters/readJSON' -> Could not find path of json file")
        print("No such file:" + fileP)
    return data


def genSysSett():
    x = {
        "stageAO": "files\\MCL.txt",
        "stage2": "files\\MCL.txt",
        "dummyStage": "DStage",
        "save path": "C:\\temp",
        "AOTF": {"Ch1": "488nm", "Ch2": "561nm"}
    }
    return x


def loadLUTstageAO(path):
    if os.path.exists(path):
        with open(path) as f:
            lines = f.readlines()
        out = np.empty([len(lines)-1, 2])
        for i in range(len(lines)-1):
            asList = lines[i+1].split(" ")
            out[i][0] = asList[0]
            out[i][1] = asList[1].replace("\n", "")
    else:
        print("Err: 'parameters/loadLUTstageAO' -> Could not find path of LUT")
        print("No such file:" + path)
        out = []
    return out


def setZstageLimits(s, e):
    global zUppLim
    global zLowLim
    if s == e:
        s = 0
        e = 300
    zLowLim = s
    zUppLim = e
    return zLowLim, zUppLim
