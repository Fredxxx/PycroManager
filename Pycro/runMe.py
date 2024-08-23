# main class to run GUI
import sys
import os
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt
from softwareHelpers import uManagerInt as um
from hardware import niDAQ as ni
from hardware import stages as xyz
from hardware import hologram as holo
from hardware import camera as cam
from softwareHelpers import jsonReadWrite as js
import microscopy as micro

mic = [] # microscopy instance used to save all project variables


class WorkerAcq(QObject):
    """ worker class used for separate thread to do acquisition """
    finished = pyqtSignal()                     # connects finish signal
    progress = pyqtSignal(int)                  # connects progress signal (progress.emit())

    @pyqtSlot()
    def run(self):
        um.startAcq(self.progress)              # do the important stuff
        self.finished.emit()                    # runs the finish tagged function


class WorkerCalib(QObject):
    """ worker class used for separate thread to do calibration and more """
    finished = pyqtSignal()                     # connects finish signal
    progress = pyqtSignal(int)                  # connects progress signal (progress.emit())

    @pyqtSlot()
    def run(self):
        xyz.startCalib(self.progress)              # do the important stuff
        self.finished.emit()                    # runs the finish tagged function


class Ui(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        uic.loadUi('mainGUI.ui', self)  # loads GUI
        # os.system(os.system("\"" + para.readJSON(self.le_initFilePath.text()).get("uManager") + "\"")) TODO
        self.app = QtWidgets.QApplication.instance()

        # initialise major mic instance, initFile and GUI parameters
        self.setMic(micro.getMic('mainMicInstance'))
        self.initFile()
        self.initialiseGUIpara()

        # set default values
        self.setWindowTitle('Acquisition Engine')
        self.slmGUI = None  # for slm gui
        self.slmWin = None  # for slm window
        self.progressBar.setValue(0)

        # start button, interrupt checkBox, mode comboBox (event listener)
        self.pb_start.clicked.connect(self.startAcqQThread)
        # self.pb_snapShot.clicked.connect(um.snapshot)
        self.cb_interrupt.stateChanged.connect(self.interruptAcq)
        self.cb_liveImg.stateChanged.connect(lambda: self.sic('liveImg', self.cb_liveImg.isChecked()))
        self.cb_SLM.stateChanged.connect(self.setSLMgui)
        self.cb_secCam.stateChanged.connect(self.start2cam)
        self.cBox_triggMode.currentIndexChanged.connect(lambda: self.sic('acqMode', self.cBox_triggMode.currentText()))

        # path select (event listener)
        self.btn_changePath.clicked.connect(self.getfiles)
        self.le_filePath.textChanged.connect(lambda: self.sic('filePath', self.le_filePath.text()))
        self.le_fileName.textChanged.connect(lambda: self.sic('fileName', self.le_fileName.text()))

        # tab "general" (event listener)
        self.dsb_expTime.valueChanged.connect(self.setExp)
        self.dsb_extDelay.valueChanged.connect(lambda: self.sic('addTime', self.dsb_extDelay.value()))
        self.dsb_del.valueChanged.connect(lambda: self.sic('delay', self.dsb_del.value()))
        self.dsb_zRange.valueChanged.connect(lambda: self.sic('zRange', self.dsb_zRange.value()))
        self.sb_zSteps.valueChanged.connect(lambda: self.sic('numStepsZ', self.sb_zSteps.value()))
        self.dsb_tInterval.valueChanged.connect(lambda: self.sic('tInt', self.dsb_tInterval.value()))
        self.sb_tSteps.valueChanged.connect(lambda: self.sic('tSteps', self.sb_tSteps.value()))
        self.cBox_tInterval.currentIndexChanged.connect(lambda: self.sic('tUnit', self.cBox_tInterval.currentText()))
        self.cBox_mdaOrder.currentIndexChanged.connect(lambda: self.sic('mdaOrder', self.cBox_mdaOrder.currentText()))

        # tab "advanced" (event listener)
        self.sb_TTLuptime.valueChanged.connect(lambda: self.sic('uptimeTTL', self.sb_TTLuptime.value()))
        self.pb_reloadInitFile.clicked.connect(self.initFile)

        # tab "advanced" -> calibration (event listener)
        self.le_aoMod.textChanged.connect(lambda: self.sic('aoMod', self.le_aoMod.text()))
        self.le_aiMon.textChanged.connect(lambda: self.sic('aiMod', self.le_aiMon.text()))
        self.le_saveCalibPath.textChanged.connect(lambda: self.sic('calibPath', self.le_saveCalibPath.text()))
        self.dsb_modMin.valueChanged.connect(lambda: self.sic('modMin', self.dsb_modMin.value()))
        self.dsb_modMax.valueChanged.connect(lambda: self.sic('modMax', self.dsb_modMax.value()))
        self.dsb_umMin.valueChanged.connect(lambda: self.sic('umMin', self.dsb_umMin.value()))
        self.dsb_umMax.valueChanged.connect(lambda: self.sic('umMax', self.dsb_umMax.value()))
        self.dsb_umAccu.valueChanged.connect(lambda: self.sic('umAccu', self.dsb_umAccu.value()))
        self.pb_calib.clicked.connect(self.startCalibThread)

        # tab "light sheet" -> calibration (event listener)
        self.dsb_galvoPos.valueChanged.connect(self.changeGalvoPos)
        self.hs_galvoPos.valueChanged.connect(self.changeGalvoHS)
        self.dsb_galvoStart.valueChanged.connect(lambda: self.sic('galvoStart', self.dsb_galvoStart.value()))
        self.dsb_galvoEnd.valueChanged.connect(lambda: self.sic('galvoEnd', self.dsb_galvoEnd.value()))
        self.sb_galvoFreq.valueChanged.connect(lambda: self.sic('galvoFreq', self.sb_galvoFreq.value()))
        self.sb_galvoReps.valueChanged.connect(lambda: self.sic('galvoReps', self.sb_galvoReps.value()))
        self.pb_move.clicked.connect(self.startGalvo)

        # lasers (event listener)
        self.hs_laser1.valueChanged.connect(self.changeLaserIntHS)
        self.hs_laser2.valueChanged.connect(self.changeLaserIntHS)
        self.hs_laser3.valueChanged.connect(self.changeLaserIntHS)
        self.hs_laser4.valueChanged.connect(self.changeLaserIntHS)
        self.sb_laserPow2.valueChanged.connect(self.changeLaserIntPow)
        self.sb_laserPow1.valueChanged.connect(self.changeLaserIntPow)
        self.sb_laserPow3.valueChanged.connect(self.changeLaserIntPow)
        self.sb_laserPow4.valueChanged.connect(self.changeLaserIntPow)
        self.rb_laser1.toggled.connect(self.changeLaserState)
        self.rb_laser2.toggled.connect(self.changeLaserState)
        self.rb_laser3.toggled.connect(self.changeLaserState)
        self.rb_laser4.toggled.connect(self.changeLaserState)
        self.cb_mode_laser.currentIndexChanged.connect(self.changeLaserMode)

        # AOTFs (event listener)
        self.hs_AOTF1.valueChanged.connect(self.changeAOTFIntHS)
        self.hs_AOTF2.valueChanged.connect(self.changeAOTFIntHS)
        self.hs_AOTF3.valueChanged.connect(self.changeAOTFIntHS)
        self.hs_AOTF4.valueChanged.connect(self.changeAOTFIntHS)
        self.sb_AOTF1.valueChanged.connect(self.changeAOTFIntPow)
        self.sb_AOTF2.valueChanged.connect(self.changeAOTFIntPow)
        self.sb_AOTF3.valueChanged.connect(self.changeAOTFIntPow)
        self.sb_AOTF4.valueChanged.connect(self.changeAOTFIntPow)
        self.rb_AOTF1.toggled.connect(self.changeAOTFState)
        self.rb_AOTF2.toggled.connect(self.changeAOTFState)
        self.rb_AOTF3.toggled.connect(self.changeAOTFState)
        self.rb_AOTF4.toggled.connect(self.changeAOTFState)

        # test (event listener)
        self.testButton.clicked.connect(lambda: self.testy())

        # show GUI
        self.show()
        self.initMove()

        # show other GUIs (if activated at start)
        self.showGUIs()

        # closing event
        self.pb_close.clicked.connect(self.exitHandler)

    def testy(self):
        """ for testing and debugging """
        um.MeeladTest()
        print("Do it sweetheart.")

    def sic(self, micProp, val):
        """set value to a corresponding attribute in microscopy class and write JSON"""
        setattr(mic, micProp, val)
        js.writeMICjson()

    def showGUIs(self):
        """ init additional GUIs """
        mic.mainGUIgeo = self.geometry()
        self.setSLMgui()

    def initMove(self):
        """ move main GUI to first screen """
        screensAvailable = self.app.screens()
        screen0 = screensAvailable[0]
        mic.screen0 = screen0
        if len(screensAvailable) == 2:
            mic.screen1 = screensAvailable[1]
        elif len(screensAvailable) == 1:
            mic.screen1 = screen0
        else:
            print('RunMe/initMove: Could not figure out screens!')
        x = int(0+screen0.size().width()*0.1)
        y = int(0+screen0.size().height()*0.1)
        self.move(x, y)

    def setExp(self):
        setattr(mic, 'expTime', self.dsb_expTime.value())
        um.setExposureTime(self.dsb_expTime.value())

    def start2cam(self):
        if self.cb_SLM.isChecked():
            um.startHeadless()
        mic.headless = self.cb_SLM.isChecked()

    def setSLMgui(self):
        if self.cb_SLM.isChecked():
            if self.slmGUI is None:
                holo.mic = mic
                self.slmGUI = holo.slmGUI()
            self.slmGUI.show()
        else:
            self.slmGUI = None
        mic.SLMactive = self.cb_SLM.isChecked()
        js.writeMICjson()

    def startCalibThread(self):
        if self.cb_interrupt.isChecked():
            print('interrupted')
        else:
            # start function in separate thread
            # Create a thread
            self.thread = QThread()
            # Create a worker object
            self.worker = WorkerCalib(self)
            # Move worker to the thread
            self.worker.moveToThread(self.thread)
            # Connect signals and slots
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.progress.connect(self.reportProgress)
            # Start the thread
            self.la_progressBar.setText("running")                  # set text in progress bar to running
            self.thread.start()                                     # starts thread
            self.pb_calib.setEnabled(False)                         # disables start button
            # Final resets
            self.thread.finished.connect(self.finishCalib)            # some clean up of GUI after acq

    def startAcqQThread(self):
        if self.cb_interrupt.isChecked():
            print('interrupted')
        else:
            # start function in separate thread
            # Create a thread
            self.thread = QThread()
            # Create a worker object
            self.worker = WorkerAcq()
            # Move worker to the thread
            self.worker.moveToThread(self.thread)
            # Connect signals and slots
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.progress.connect(self.reportProgress)
            # Start the thread
            self.la_progressBar.setText("running")                  # set text in progress bar to running
            self.thread.start()                                     # starts thread
            self.pb_start.setEnabled(False)                         # disables start button
            # Final resets
            self.thread.finished.connect(self.finishAcq)            # some clean up of GUI after acq

    def reportProgress(self, v):
        """ used to report value from worker thread """
        self.progressBar.setValue(v)

    def finishAcq(self):
        self.pb_start.setEnabled(True)                          # enables start button
        if mic.acqFlag:                                          # interruption flag True for clean acq
            self.progressBar.setValue(100)
            self.la_progressBar.setText("finished")
            print('Acquisition finished!')
        else:                                                   # false for interrupted acq
            self.la_progressBar.setText("interrupted")
            self.cb_interrupt.setCheckState(False)
            print('Acquisition force stopped!')
        mic.acqFlag = True

    def finishCalib(self):
        self.pb_calib.setEnabled(True)  # enables start button
        if xyz.calibFlag:  # interruption flag True for clean calib
            self.progressBar.setValue(100)
            self.la_progressBar.setText("finished")
            print('Calibration finished!')
        else:  # false for interrupted calib
            self.la_progressBar.setText("interrupted")
            self.cb_interrupt.setCheckState(False)
            print('Calibration force stopped!')
        xyz.calibFlag = True

    def getfiles(self):
        file = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory"))
        mic.filePath = file
        self.le_filePath.setText(file)

    def interruptAcq(self):
        if self.cb_interrupt.isChecked():
            um.acqFlag = False
            xyz.calibFlag = False
            mic.acqFlag = False
            mic.acqFlagH = False
            ni.stopCloseTask(mic.task)
        else:
            um.acqFlag = True
            xyz.calibFlag = True
            mic.acqFlag = True
            mic.acqFlagH = True

    def updateGUI(self):
        # updates all values in GUI
        self.updateTabGeneral()
        self.updateTabAdvanced()

    def initialiseGUIpara(self):
        """initialises GUI values"""
        self.cBox_triggMode.addItem('spinning disk')
        self.cBox_triggMode.addItem('light sheet')
        self.cBox_triggMode.addItem('light sheet SIM')
        js.initMICjson(self)
        # self.cBox_triggMode.setCurrentText('light sheet SIM')
        self.cBox_tInterval.addItem('ms')
        self.cBox_tInterval.addItem('s')
        self.cBox_tInterval.addItem('min')
        self.cBox_mdaOrder.addItem('zt')
        self.cBox_mdaOrder.addItem('tz')
        self.rb_laser1.setStyleSheet("color: red;" "background-color: white;")
        self.rb_laser2.setStyleSheet("color: red;" "background-color: white;")
        self.rb_laser3.setStyleSheet("color: red;" "background-color: white;")
        self.rb_laser4.setStyleSheet("color: red;" "background-color: white;")
        self.setUpLasers()
        self.setUpAOTFs()
        # xyz.setMainInstance(self) TODO remove?

    def initFile(self):
        """initialises stuff"""

        # transfer mic instance to subclasses
        um.mic = mic
        ni.mic = mic
        cam.mic = mic
        xyz.mic = mic
        js.mic = mic
        um.initMicUM() # needed because um class called before mic transfered

        # init JSON file
        initFileP = self.le_initFilePath.text()
        mic.initFileP = initFileP
        json = micro.readJSON(initFileP)
        micro.initMic(mic, json)

        # get working directory
        mic.cwd = os.getcwd()

        # loads look up tables for stages
        lutStage = micro.loadLUTstageAO(json.get("stageAO"))
        lutGalvo = micro.loadLUTstageAO(json.get("galvoAO"))
        mic.lut = lutStage
        mic.lutGalvo = lutGalvo

    def changeGalvoHS(self):
        """change galvo pos based on horizontal slider"""
        val = self.hs_galvoPos.value() /100         # get value from slider (/100 need for float)
        self.dsb_galvoPos.setValue(val)             # sets value in box next to slider
        valAO = ni.um2v(val, 'galvo')
        mic.galvoPos = val
        ni.writeSingleAOcopmlete(valAO)

    def changeGalvoPos(self):
        val = self.dsb_galvoPos.value()             # get value from slider (/100 need for float)
        self.hs_galvoPos.setValue(int(val * 100))   # sets value in box next to slider
        valAO = ni.um2v(val, 'galvo')
        mic.galvoPos = val
        ni.writeSingleAOcopmlete(valAO)

    def startGalvo(self):
        gStart = self.dsb_galvoStart.value()
        gEnd = self.dsb_galvoEnd.value()
        gFreq = self.sb_galvoFreq.value()
        gReps = self.sb_galvoReps.value()
        ni.galvoOscilate(gStart, gEnd, gFreq, gReps)

    def changeLaserState(self):
        """switches lasers on and off depending on state or radio button
        changes text ("On", "Off") and color (red, green) depending if laser is on or off"""
        if self.rb_laser1.isChecked():
            um.setLaserState(0, 'On')
            self.rb_laser1.setStyleSheet("color: green;" "background-color: white;")
            self.rb_laser1.setText('On')
        elif not self.rb_laser1.isChecked():
            um.setLaserState(0, 'Off')
            self.rb_laser1.setStyleSheet("color: red;" "background-color: white;")
            self.rb_laser1.setText('Off')
        if self.rb_laser2.isChecked():
            um.setLaserState(1, 'On')
            self.rb_laser2.setStyleSheet("color: green;" "background-color: white;")
            self.rb_laser2.setText('On')
        elif not self.rb_laser2.isChecked():
            um.setLaserState(1, 'Off')
            self.rb_laser2.setStyleSheet("color: red;" "background-color: white;")
            self.rb_laser2.setText('Off')
        if self.rb_laser3.isChecked():
            um.setLaserState(2, 'On')
            self.rb_laser3.setStyleSheet("color: green;" "background-color: white;")
            self.rb_laser3.setText('On')
        elif not self.rb_laser3.isChecked():
            um.setLaserState(2, 'Off')
            self.rb_laser3.setStyleSheet("color: red;" "background-color: white;")
            self.rb_laser3.setText('Off')
        if self.rb_laser4.isChecked():
            um.setLaserState(3, 'On')
            self.rb_laser4.setStyleSheet("color: green;" "background-color: white;")
            self.rb_laser4.setText('On')
        elif not self.rb_laser4.isChecked():
            um.setLaserState(3, 'Off')
            self.rb_laser4.setStyleSheet("color: red;" "background-color: white;")
            self.rb_laser4.setText('Off')

    def changeLaserIntHS(self):
        """changes laser intensity for all four lasers when slider activated"""
        lLas = mic.laserList                             # get list of lasers
        if len(lLas) > 0:                               # if, at least, one laser is selected
            val = self.hs_laser1.value() / 100          # get value from slider (/100 need for float)
            self.sb_laserPow1.setValue(val)             # sets value in box next to slider
            um.setLaser(0, val)                         # changes laser intensity via uManager
            mic.laser1Power = val                       # sets laser power in mic
        if len(lLas) > 1:                               # if, at least, two laser are selected (see first if loop)
            val = self.hs_laser2.value() / 100
            self.sb_laserPow2.setValue(val)
            um.setLaser(1, val)
            mic.laser2Power = val
        if len(lLas) > 2:                               # if, at least, three laser are selected (see first if loop)
            val = self.hs_laser3.value() / 100
            self.sb_laserPow3.setValue(val)
            um.setLaser(2, val)
            mic.laser3Power = val
        if len(lLas) > 3:                               # if, at least, four laser are selected (see first if loop)
            val = self.hs_laser4.value()/100
            self.sb_laserPow4.setValue(val)
            um.setLaser(3, val)
            mic.laser4Power = val

    def changeLaserIntPow(self):
        """changes laser intensity for all four lasers when slider activated"""
        lLas = mic.laserList                             # get list of lasers
        if len(lLas) > 0:                               # if, at least, one laser is selected
            val = self.sb_laserPow1.value()             # read value from box next to slider
            self.hs_laser1.setValue(int(val * 100))     # set slider value (*100 needed for float in slider)
            um.setLaser(0, val)                         # set value in uManager
            mic.laser1Power = val                       # sets laser power in mic
        if len(lLas) > 1:                               # if, at least, two laser are selected (see first if loop)
            val = self.sb_laserPow2.value()
            self.hs_laser2.setValue(int(val * 100))
            um.setLaser(1, val)
            mic.laser2Power = val
        if len(lLas) > 2:                               # if, at least, three laser are selected (see first if loop)
            val = self.sb_laserPow3.value()
            self.hs_laser3.setValue(int(val * 100))
            um.setLaser(2, val)
            mic.laser3Power = val
        if len(lLas) > 3:                               # if, at least, four laser are selected (see first if loop)
            val = self.sb_laserPow4.value()
            self.hs_laser4.setValue(int(val * 100))
            um.setLaser(3, val)
            mic.laser4Power = val

    def changeLaserMode(self):
        """changes the laser mode from constant current to constant power"""
        if self.cb_mode_laser.currentText() == 'CC':
            um.setLaserMode('Constant Current')             # sets the mode in uManager
            self.la_power.setText('Current [A]:')           # cosmetics: changes label
            self.setLaserSliderMinMax('Current')            # sets min/max value for slider and box
        elif self.cb_mode_laser.currentText() == 'CP':
            um.setLaserMode('Constant Power')
            self.la_power.setText('Power [mW]:')
            self.setLaserSliderMinMax('Power')
        else:
            print('runMe/changeLaserMode: Could not read CC or CP!')
            self.la_power.setText('Error')

    def setUpLasers(self):
        """initializes lasers"""
        lDev = um.getDevices()                  # gets all loaded devices in uManager
        print(lDev)
        mic.lDev = lDev
        lLas = um.getLaserFromList(lDev)        # filters the devices for lasers
        self.cb_mode_laser.addItem('CP')        # populate combobox
        self.cb_mode_laser.addItem('CC')        # populate combobox
        self.setLaserSliderMinMax('Power')      # set min/max for slider and box
        aotf = um.isAOTFavailable('lDev')       # checks if aotf loaded

        if len(lLas) > 0:                       # checks if a laser is there (below repeat for up to four lasers)
            self.la_laser1.setText('Laser ' + ''.join(filter(str.isdigit, lLas[0])) + 'nm')        # set name laser
            if aotf:
                self.la_laserAOTF1.setText('AOTF ' + ''.join(filter(str.isdigit, lLas[0])) + 'nm') # set name AOTF
            else:
                self.la_laserAOTF1.setText('n/a')
                self.hs_AOTF1.setEnabled(False)
                self.sb_AOTF1.setEnabled(False)
                self.rb_AOTF1.setEnabled(False)
            um.setLaser(0, 0)                   # set laser power to 0
            um.setLaserState(0, 'Off')          # set laser off
            print(um.getLaserControlMode(lLas[0]))
        else:                                   # if no laser -> disables buttons and sets names to n/a
            self.la_laser1.setText('n/a')
            self.la_laserAOTF1.setText('n/a')
            self.hs_laser1.setEnabled(False)
            self.sb_laserPow1.setEnabled(False)
            self.rb_laser1.setEnabled(False)
            self.hs_AOTF1.setEnabled(False)
            self.sb_AOTF1.setEnabled(False)
            self.rb_AOTF1.setEnabled(False)

        if len(lLas) > 1:
            self.la_laser2.setText('Laser ' + ''.join(filter(str.isdigit, lLas[1])) + 'nm')
            if aotf:
                self.la_laserAOTF2.setText('AOTF ' + ''.join(filter(str.isdigit, lLas[1])) + 'nm')
            else:
                self.la_laserAOTF2.setText('n/a')
                self.hs_AOTF2.setEnabled(False)
                self.sb_AOTF2.setEnabled(False)
                self.rb_AOTF2.setEnabled(False)
            um.setLaser(1, 0)
            um.setLaserState(1, 'Off')
        else:
            self.la_laser2.setText('n/a')
            self.la_laserAOTF2.setText('n/a')
            self.hs_laser2.setEnabled(False)
            self.sb_laserPow2.setEnabled(False)
            self.rb_laser2.setEnabled(False)
            self.hs_AOTF2.setEnabled(False)
            self.sb_AOTF2.setEnabled(False)
            self.rb_AOTF2.setEnabled(False)

        if len(lLas) > 2:
            self.la_laser3.setText('Laser ' + lLas[2] + 'nm')
            if aotf:
                self.la_laserAOTF3.setText('AOTF ' + lLas[2] + 'nm')
            else:
                self.la_laserAOTF3.setText('n/a')
                self.hs_AOTF3.setEnabled(False)
                self.sb_AOTF3.setEnabled(False)
                self.rb_AOTF3.setEnabled(False)
            um.setLaser(2, 0)
            um.setLaserState(2, 'Off')
        else:
            self.la_laser3.setText('n/a')
            self.la_laserAOTF3.setText('n/a')
            self.hs_laser3.setEnabled(False)
            self.sb_laserPow3.setEnabled(False)
            self.rb_laser3.setEnabled(False)
            self.hs_AOTF3.setEnabled(False)
            self.sb_AOTF3.setEnabled(False)
            self.rb_AOTF3.setEnabled(False)

        if len(lLas) > 3:
            self.la_laser4.setText('Laser ' + lLas[3] + 'nm')
            if aotf:
                self.la_laserAOTF4.setText('AOTF ' + lLas[3] + 'nm')
            else:
                self.la_laserAOTF4.setText('n/a')
                self.hs_AOTF4.setEnabled(False)
                self.sb_AOTF4.setEnabled(False)
                self.rb_AOTF4.setEnabled(False)
            um.setLaser(3, 0)
            um.setLaserState(3, 'Off')
        else:
            self.la_laser4.setText('n/a')
            self.la_laserAOTF4.setText('n/a')
            self.hs_laser4.setEnabled(False)
            self.sb_laserPow4.setEnabled(False)
            self.rb_laser4.setEnabled(False)
            self.hs_AOTF4.setEnabled(False)
            self.sb_AOTF4.setEnabled(False)
            self.rb_AOTF4.setEnabled(False)

    def setUpAOTFs(self):
        # initialises ATOF
        self.sb_AOTF_Ch1.setValue(2)        # sets channel of AOTF for first laser TODO: remove hard coding
        self.sb_AOTF_Ch2.setValue(1)        # sets channel of AOTF for second laser TODO: remove hard coding
        self.changeAOTFState()              # cosmetics: called to turn radio buttons red

    def changeAOTFState(self):
        # switches AOTF on and off depending on state or radio button
        # changes text ("On", "Off") and color (red, green) depending if laser is on or off
        if self.rb_AOTF1.isChecked():
            um.setAOTFState(self.sb_AOTF_Ch1.value(), '1')
            self.rb_AOTF1.setStyleSheet("color: green;" "background-color: white;")
            self.rb_AOTF1.setText('On')
        elif not self.rb_AOTF1.isChecked():
            um.setAOTFState(self.sb_AOTF_Ch1.value(), '0')
            self.rb_AOTF1.setStyleSheet("color: red;" "background-color: white;")
            self.rb_AOTF1.setText('Off')
        if self.rb_AOTF2.isChecked():
            um.setAOTFState(self.sb_AOTF_Ch2.value(), '1')
            self.rb_AOTF2.setStyleSheet("color: green;" "background-color: white;")
            self.rb_AOTF2.setText('On')
        elif not self.rb_AOTF2.isChecked():
            um.setAOTFState(self.sb_AOTF_Ch2.value(), '0')
            self.rb_AOTF2.setStyleSheet("color: red;" "background-color: white;")
            self.rb_AOTF2.setText('Off')
        if self.rb_AOTF3.isChecked():
            um.setAOTFState(self.sb_AOTF_Ch3.value(), '1')
            self.rb_AOTF3.setStyleSheet("color: green;" "background-color: white;")
            self.rb_AOTF3.setText('On')
        elif not self.rb_AOTF3.isChecked():
            um.setAOTFState(self.sb_AOTF_Ch3.value(), '0')
            self.rb_AOTF3.setStyleSheet("color: red;" "background-color: white;")
            self.rb_AOTF3.setText('Off')
        if self.rb_AOTF4.isChecked():
            um.setAOTFState(self.sb_AOTF_Ch4.value(), '1')
            self.rb_AOTF4.setStyleSheet("color: green;" "background-color: white;")
            self.rb_AOTF4.setText('On')
        elif not self.rb_AOTF4.isChecked():
            um.setAOTFState(self.sb_AOTF_Ch4.value(), '0')
            self.rb_AOTF4.setStyleSheet("color: red;" "background-color: white;")
            self.rb_AOTF4.setText('Off')

    def changeAOTFIntHS(self):
        # changes AOTF percentage for all four channels when slider activated
        # similar to changeLaserIntHS
        lLas = um.laserList
        if len(lLas) > 0:
            val = self.hs_AOTF1.value() / 100
            self.sb_AOTF1.setValue(val)
            um.setAOTF(self.sb_AOTF_Ch1.value(), val)
            mic.AOTF1 = val
        if len(lLas) > 1:
            val = self.hs_AOTF2.value() / 100
            self.sb_AOTF2.setValue(val)
            um.setAOTF(self.sb_AOTF_Ch2.value(), val)
            mic.AOTF2 = val
        if len(lLas) > 2:
            val = self.hs_AOTF3.value() / 100
            self.sb_ATOF3.setValue(val)
            um.setAOTF(self.sb_AOTF_Ch3.value(), val)
            mic.AOTF3 = val
        if len(lLas) > 3:
            val = self.hs_AOTF4.value() / 100
            self.sb_AOTF4.setValue(val)
            um.setAOTF(self.sb_AOTF_Ch4.value(), val)
            mic.AOTF4 = val

    def changeAOTFIntPow(self):
        # changes AOTF percentage for all four channels when box activated
        # similar to changeLaserIntHS
        lLas = um.laserList
        if len(lLas) > 0:
            val = self.sb_AOTF1.value()
            self.hs_AOTF1.setValue(int(val * 100))
            um.setAOTF(self.sb_AOTF_Ch1.value(), val)
            mic.AOTF1 = val
        if len(lLas) > 1:
            val = self.sb_AOTF2.value()
            self.hs_AOTF2.setValue(int(val * 100))
            um.setAOTF(self.sb_AOTF_Ch2.value(), val)
            mic.AOTF2 = val
        if len(lLas) > 2:
            val = self.sb_AOTF3.value()
            self.hs_AOTF3.setValue(int(val * 100))
            um.setAOTF(self.sb_AOTF_Ch3.value(), val)
            mic.AOTF3 = val
        if len(lLas) > 3:
            val = self.sb_AOTF4.value()
            self.hs_AOTF4.setValue(int(val * 100))
            um.setAOTF(self.sb_AOTF_Ch4.value(), val)
            mic.AOTF4 = val

    def setLaserSliderMinMax(self, stat):
        # reads min/max values from uManager and sets the limits for GUI widgets accordingly
        lLas = mic.laserList
        if len(lLas) > 0:
            self.hs_laser1.setMinimum(um.getLaserMin(lLas[0], stat) * 100)   # factor 100 is needed for float in slider
            self.hs_laser1.setMaximum(um.getLaserMax(lLas[0], stat) * 100)
            self.sb_laserPow1.setMinimum(um.getLaserMin(lLas[0], stat) * 100)
            self.sb_laserPow1.setMaximum(um.getLaserMax(lLas[0], stat) * 100)
        if len(lLas) > 1:
            self.hs_laser2.setMinimum(um.getLaserMin(lLas[1], stat) * 100)
            self.hs_laser2.setMaximum(um.getLaserMax(lLas[1], stat) * 100)
            self.sb_laserPow2.setMinimum(um.getLaserMin(lLas[1], stat) * 100)
            self.sb_laserPow2.setMaximum(um.getLaserMax(lLas[1], stat) * 100)
        if len(lLas) > 2:
            self.hs_laser3.setMinimum(um.getLaserMin(lLas[2], stat) * 100)
            self.hs_laser3.setMaximum(um.getLaserMax(lLas[2], stat) * 100)
            self.sb_laserPow3.setMinimum(um.getLaserMin(lLas[2], stat) * 100)
            self.sb_laserPow3.setMaximum(um.getLaserMax(lLas[2], stat) * 100)
        if len(lLas) > 3:
            self.hs_laser4.setMinimum(um.getLaserMin(lLas[3], stat) * 100)
            self.hs_laser4.setMaximum(um.getLaserMax(lLas[3], stat) * 100)
            self.sb_laserPow4.setMinimum(um.getLaserMin(lLas[3], stat) * 100)
            self.sb_laserPow4.setMaximum(um.getLaserMax(lLas[3], stat) * 100)

    def setMic(self, a):
        global mic
        mic = a

    def getMic(self):
        return mic

    def exitHandler(self):
        print("closing app")
        QtWidgets.QApplication.closeAllWindows()


app = QtWidgets.QApplication(sys.argv)
defaultfont = QtGui.QFont('Arial', 8)
QtWidgets.QApplication.setFont(defaultfont)
window = Ui()
app.exec_()
