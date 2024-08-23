"""class: stages
    1. consistent stage specific properties callable via uManager
    2. calibration of stages (not finished - time conflicts - 20230522)"""

import numpy as np
import time
import matplotlib.pyplot as plt
from hardware import niDAQ as ni
from PyQt5 import QtWidgets

mic = []  # main microscopy instance (used to make sure main instance of mic is used in all files)


class StageZ:
    """Includes relevant properties to control the piezo stage."""
    def __init__(self, name):
        self.name = name                # name of stage
        self.position = 'N/A'           # set position
        self.sequencing = 'N/A'         # use sequencing
        self.speed = 'N/A'              # set speed of stage
        self.acc = 'N/A'                # set acceleration of stage
        self.loop = 'N/A'               # set closed or open loop


def getStageZ(stageName):
    """generic class to define stage specific properties callable via uManager"""
    stage = StageZ(stageName)
    if stageName == 'MCL NanoDrive Z Stage':
        stage.position = 'Set position Z (um)'
    elif stageName == 'Z':
        stage.position = 'Position'
        stage.sequencing = 'UseSequences'
    elif stageName == 'DStage':
        stage.position = 'Position'
        stage.sequencing = 'UseSequences'
    return stage


def startCalib(prog):
    """calibration of stage AO -> control of stage and AI -> monitor needed"""

    # first step (closed loop) prepare stuff
    title = "Calibration step 1"
    message = "Please make sure the stage is in 'closed loop' mode."
    QtWidgets.QMessageBox.about(mic.runMeIns, title, message) # inform user to set stage to "closed loop"
    taskMod = ni.setUpSingleChAO(mic.aoMod)     # set up AO channel
    taskMon = ni.setUpSingleChAI(mic.aiMon)     # set up AI channel
    patUM = np.arange(mic.umMin, mic.umMax, mic.umAccu) # generate um table
    patVmod = np.arange(mic.modMin, mic.modMax, (mic.modMax-mic.modMin)/len(patUM)) # generate V table
    patVmon = np.zeros(len(patVmod))        # init array for closed loop data
    patVmonUp = np.zeros(len(patVmod))      # init array for positive hysteresis
    patVmonDown = np.zeros(len(patVmod))    # init array for negative hysteresis
    c = 100/3/len(patVmod)     # not sure if needed

    # generate figure which will be updated in loop
    figure1, ax1 = plt.subplots()
    plt.ion()
    plot1, = ax1.plot(patVmod, patVmon, label="cl linearity")
    plot2, = ax1.plot(patVmod, patVmonUp, label="hysteresis +")
    plot3, = ax1.plot(patVmod, patVmonDown, label="hysteresis -")
    plt.axis([mic.modMin, mic.modMax, mic.modMin, mic.modMax])
    plt.title("Closed loop")
    plt.xlabel("modulation Voltage [V]", fontsize=18)
    plt.ylabel("piezo Voltage [V]", fontsize=18)
    plt.legend()
    plt.show()

    # stage sends position via AO and reads actual position via AI and updates figure
    for i in range(len(patVmod)):
        if mic.calibFlag:
            #ni.setSingleValueChAO(taskMod, patVmod[i])
            time.sleep(0.001)
            print(i)
            patVmon[i] = i/len(patVmod)*mic.modMax #ni.readSingleValueAI(taskMon)
            prog.emit(int(c*i))
            if i % 100 == 0 or i == len(patVmod)-1:
                plot1.set_ydata(patVmon)
                figure1.canvas.update()
                figure1.canvas.flush_events()

    # step two (open loop)
    title = "Calibration step 2"
    message = "Please make sure the stage is in 'open loop' mode."

    # stage sends position via AO and reads actual position via AI in positive direction
    if mic.calibFlag:
        QtWidgets.QMessageBox.about(mic.runMeIns, title, message)
    plt.title("Open loop +")
    for i in range(len(patVmod)):
        if mic.calibFlag:
            # ni.setSingleValueChAO(taskMod, patVmod[i])
            time.sleep(0.001)
            print(i)
            patVmonUp[i] = i / len(patVmod) * mic.modMax * 0.9 # ni.readSingleValueAI(taskMon)
            prog.emit(int(c * i + len(patVmod)))
            if i % 100 == 0 or i == len(patVmod) - 1:
                plot2.set_ydata(patVmonUp)
                figure1.canvas.update()
                figure1.canvas.flush_events()

    # stage sends position via AO and reads actual position via AI in negative direction
    plt.title("Open loop -")
    for i in range(len(patVmod)):
        if mic.calibFlag:
            # ni.setSingleValueChAO(taskMod, patVmod[i])
            time.sleep(0.001)
            print(i)
            patVmonDown[i] = i / len(patVmod) * mic.modMax * 0.8 # ni.readSingleValueAI(taskMon)
            prog.emit(int(c * i + 2 * len(patVmod)))
            if i % 100 == 0 or i == len(patVmod) - 1:
                plot3.set_ydata(patVmonDown)
                figure1.canvas.update()
                figure1.canvas.flush_events()

    # close tasks
    ni.closeTask(taskMod)
    ni.closeTask(taskMon)