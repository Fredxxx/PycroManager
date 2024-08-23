# class to interact with uManager interface
# uManger needs to be started first before pycromanager can interact with it
#

import time

import numpy as np
from pycromanager import Acquisition, multi_d_acquisition_events, Core, start_headless
from hardware import camera as cam
from hardware import niDAQ as ni
from nidaqmx.constants import AcquisitionType
from hardware import stages as stag
import tracemalloc

mic = []  # main microscopy instance (used to make sure main instance of mic is used in all files)

# get uManager core
mmc = Core()
mmc2 = []


def initMicUM():
    mic.core = mmc

def genMDAeventsZT():
    events = []
    shutter = True
    event = {
        'axes': {
            'time': 0,
            'z': 0
        },
        'z': 0,
        'min_start_time': 0,
        'keep_shutter_open': shutter,
        'idx': 0
    }
    events.append(event)
    for i in events:
        print(i)
    return events


# def savedImageFn(axes, dataset):
#     c = int(p.progTick * len(dataset.index))
#     p.progressEmit.emit(c)


def genMDAevents():
    if mic.zRange == 0 or mic.numStepsZ == 0:
        ev = multi_d_acquisition_events(num_time_points=mic.tSteps, time_interval_s=mic.tInt, order=mic.mdaOrder,
                                        keep_shutter_open_between_z_steps=True)
    else:
        ev = multi_d_acquisition_events(z_start=mic.posStartZ, z_end=mic.posEndZ, z_step=mic.stepSizeZ,
                                        num_time_points=mic.tSteps, time_interval_s=mic.tInt,
                                        order=mic.mdaOrder, keep_shutter_open_between_z_steps=True)
    for i in ev:
        print(i)
    return ev


def hardTrigHook(ev):
    task = mic.task
    task.stop()
    time.sleep(mic.delay)
    task.start()
    return ev


def savedImageFn(axes, dataset):
    c = int(mic.progTick * len(dataset.index))
    mic.progressEmit.emit(c)
    if not mic.acqFlag:  # abort acq for press interrupt
        print('abort')
        mic.acq.abort()


def startAcq(prog):
    if mic.acqMode == 'spinning disk':
        hardwareTriggering(prog)
    elif mic.acqMode == 'light sheet':
        hardwareTriggeringLS(prog)
    elif mic.acqMode == 'light sheet SIM':
        hardwareTriggeringLS_SIM(prog)
    else:
        print("uManagerInt/startAcq: Acquisition/Trigger mode not found.")


def hardwareTriggering(prog):
    """ multidimensional acquisition in uManager mode
        uManger -> use uManager loaded stage in "core-focus", no DAQ card used (slow)
        uMangerAO -> use analog modulation input of stage via DAD card (faster) """
    # tracemalloc.start()

    # set progressBar signal, interruption flag and saving directory
    # setProgressEmit(prog)
    # setH1Flag(True)
    save_directory = mic.filePath
    save_name = mic.fileName

    # get hardware (stage, cam) ready
    zStage = mmc.get_focus_device()  # fetch current z stage
    stageZ = stag.getStageZ(zStage)
    # if not stageZ == 'DStage':
    #     para.setZstageLimits(mmc.get_property_lower_limit(stageZ.name, stageZ.position),
    #                          mmc.get_property_upper_limit(stageZ.name, stageZ.position))
    preScanPos = mmc.get_position(stageZ.name)
    stageDemo = stag.getStageZ('DStage')  # TODO make readable from init.file
    camera = cam.getCam(mmc.get_property("Core", "Camera"))
    cam.setTrig(camera, "external")         # InfoMeelad: sets camera into external trigger mode

    # generate scan patterns, um events and get stage ready
    if notZstack():
        print("No, scan pattern generated.")
        mic.setStageSeq(zStage)
    else:
        mmc.set_property(stageZ.name, stageZ.position, preScanPos - mic.zRange / 2)
        mmc.set_focus_device(stageDemo.name)
        mmc.set_property(stageDemo.name, stageDemo.sequencing, 'Yes')
        mic.setStageSeq(stageDemo.name)
        mic.InitialStepV = 0  # for relative Piezo movement.
        mic.scanPattern = ni.generateScanPat()  # generate AO pattern
    events = genMDAevents()
    mic.setProgTick(100 / len(events))
    mic.setProgEmit(prog)

    # set up task
    mic.digEvents = 40
    niTask = ni.initTask2ao("hardwareTrigCamAndStair")  # InfoMeelad: get card ready - init 2 analog outputs
    mic.setTask(niTask)
    seq = ni.initDaqSeq()                               # InfoMeelad: generete signal
    ni.setTaskTiming(niTask, seq)                       # InfoMeelad: send signal to DAQ card and set the timing

    # do acquisition
    with Acquisition(directory=save_directory, name=save_name, post_camera_hook_fn=hardTrigHook,
                     show_display=mic.liveImg, image_saved_fn=savedImageFn, saving_queue_size=5000) as acq:
        acq.acquire(events)  # do acquisition
        while mic.acqFlagH:
            time.sleep(0.2)
            data = acq.get_dataset()
            if len(data.index) == len(events):  # stops at last image (should not be needed)
                waitLastImg = (mic.expTime + mic.addTime + 10) * 10 ** -3
                time.sleep(waitLastImg)  # wait for last image to be acquired
                print('Last image taken.')
                mic.acqFlagH = False
        if not mic.acqFlag:  # abort acq for press interrupt
            print('abort')
            acq.abort()
        time.sleep(1)

    # reset AO stage and close task
    ni.waitForTask(niTask, 600)                              # InfoMeelad: wait for the sequence to finish
    ni.setVoltage2ao(niTask, 0)                              # InfoMeelad: sets 2 AOs to zero
    ni.waitStopCloseTask(niTask, 10)                         # InfoMeelad: close task

    # reset z stage and cam
    mmc.set_focus_device(zStage)
    mmc.set_position(zStage, preScanPos)
    cam.setTrig(camera, "internal")    # InfoMeelad: set camera to internal triggering -> so it can be used by micromanager again


def hardwareTriggeringLS(prog):
    """ multidimensional acquisition in uManager mode
        uManger -> use uManager loaded stage in "core-focus", no DAQ card used (slow)
        uMangerAO -> use analog modulation input of stage via DAD card (faster) """
    # tracemalloc.start()

    # set progressBar signal, interruption flag and saving directory
    save_directory = mic.filePath
    save_name = mic.fileName
    save_name2 = mic.fileName + "_cam2"

    # get hardware (stage, cam) ready
    zStage = mmc.get_focus_device()  # fetch current z stage
    stageZ = stag.getStageZ(zStage)
    mic.digEvent = 100  # 100 points in AO signal for glavo
    # if not stageZ == 'DStage':
    #     para.setZstageLimits(mmc.get_property_lower_limit(stageZ.name, stageZ.position),
    #                          mmc.get_property_upper_limit(stageZ.name, stageZ.position))
    preScanPos = mmc.get_position(stageZ.name)
    stageDemo = stag.getStageZ('DStage')  # TODO make readable from init.file
    camera = cam.getCam(mmc.get_property("Core", "Camera"))
    cam.setTrig(camera, "external")

    # generate scan patterns, um events and get stage ready
    if notZstack():
        print("No, scan pattern generated.")
        mic.setStageSeq(zStage)
    else:
        mmc.set_property(stageZ.name, stageZ.position, preScanPos - mic.zRange / 2)
        mmc.set_focus_device(stageDemo.name)
        mmc.set_property(stageDemo.name, stageDemo.sequencing, 'Yes')
        mic.stageSeq = stageDemo.name
        mic.InitialStepV = 0  # for relative Piezo movement.
        mic.scanPattern = ni.generateScanPat()  # generate AO pattern
    events = genMDAevents()
    mic.progTick = 100 / len(events)
    mic.progressEmit = prog

    # set up task
    niTask = ni.initTask2ao("hardwareTrigCamAndStair")
    mic.task = niTask
    seq = ni.initDaqSeqLS()
    seq = ni.switchRows(seq)
    ni.setTaskTiming(niTask, seq)

    # do acquisition
    #with Acquisition(directory=save_directory, name=save_name, post_camera_hook_fn=hardTrigHook,
    #                show_display=mic.liveImg, image_saved_fn=savedImageFn, saving_queue_size=5000) as acq:
    if mic.headless:
        updateCam2()
        acq2 = Acquisition(directory=save_directory, name=save_name2, show_display=mic.liveImg, port=mic.umPort2,
                           saving_queue_size=5000)
    with Acquisition(directory=save_directory, name=save_name, image_saved_fn=savedImageFn,
                     post_camera_hook_fn=hardTrigHook, show_display=mic.liveImg, saving_queue_size=5000) as acq:
        if mic.headless:
            acq2.acquire(events)
            mic.acq2 = acq2
        acq.acquire(events)  # do acquisition
        mic.acq = acq

    # reset AO stage and close task
    ni.waitForTask(niTask, 600)
    ni.setVoltage2ao(niTask, 0)
    ni.waitStopCloseTask(niTask, 10)

    if mic.headless:
        acq2.mark_finished()

    # reset z stage
    mmc.set_focus_device(zStage)
    mmc.set_position(zStage, preScanPos)
    cam.setTrig(camera, "internal")

def hardwareTriggeringLS_SIM(prog):
    """ multidimensional acquisition in uManager mode
        uManger -> use uManager loaded stage in "core-focus", no DAQ card used (slow)
        uMangerAO -> use analog modulation input of stage via DAD card (faster) """

    # set saving directory and name
    save_directory = mic.filePath
    save_name = mic.fileName

    # get hardware (stage, cam) ready
    zStage = mmc.get_focus_device()     # fetch current z stage
    stageZ = stag.getStageZ(zStage)     # get stage instance from class stages
    mic.digEvent = 100                  # 100 points in AO signal for galvo
    preScanPos = mmc.get_position(stageZ.name)  # save start position of stage to reset the position after scan
    stageDemo = stag.getStageZ('DStage')  # get demo stage instance from class stages -> used for sequencing
    camera = cam.getCam(mmc.get_property("Core", "Camera")) # get camera instance from class cameras
    cam.setTrig(camera, "external")         # sets the camera mode into external trigger mode

    # generate scan patterns, um events and get stage ready
    if notZstack(): # dirty fix for time series
        print("No, scan pattern generated.")
        mic.setStageSeq(zStage)
    else:
        mmc.set_focus_device(stageDemo.name) # sets uManager focusing device to demo cam -> trick to get into fast imaging
        mmc.set_property(stageDemo.name, stageDemo.sequencing, 'Yes') # sets uManager to fast mode
        mic.stageSeq = stageDemo.name   # documenting reasons no function
        mic.InitialStepV = 0  # for relative Piezo movement. TODO: SIM mode checking
        mic.scanPattern = ni.generateScanPat()  # generate AO pattern
    events = genMDAevents() # generates events for uManager corresponding to scan pattern
    mic.progTick = 100 / len(events) # cosmetics -> live progressbar
    mic.progressEmit = prog # cosmetics -> live progressbar

    # set up task
    niTask = ni.initTask2ao("hardwareTrigCamAndStair")
    mic.task = niTask
    seq = ni.initDaqSeq() # TODO: SIM mode checking
    # seq = ni.switchRows(seq) # TODO: SIM mode checking
    ni.setTaskTiming(niTask, seq) # TODO: SIM mode checking

    # do acquisition
    #with Acquisition(directory=save_directory, name=save_name, post_camera_hook_fn=hardTrigHook,
    #                show_display=mic.liveImg, image_saved_fn=savedImageFn, saving_queue_size=5000) as acq:

    with Acquisition(directory=save_directory, name=save_name, image_saved_fn=savedImageFn,
                     post_camera_hook_fn=hardTrigHook, show_display=mic.liveImg, saving_queue_size=5000) as acq:
        acq.acquire(events)  # do acquisition
        mic.acq = acq

    # reset AO stage and close task
    ni.waitForTask(niTask, 600)
    ni.setVoltage2ao(niTask, 0)
    ni.waitStopCloseTask(niTask, 10)

    # reset z stage
    mmc.set_focus_device(zStage)
    mmc.set_position(zStage, preScanPos)
    cam.setTrig(camera, "internal")

def updateCam2():
    mmc2.set_exposure(mic.expTime2)


def startHeadless():
    """start second instance of micromanager in headless (background) mode"""
    global mmc2
    start_headless(mic.cwd+mic.umApp, mic.cwd+mic.umConfig1, port=mic.umPort2)
    mmc2 = Core(port=mic.umPort2)


def test():
    """
       Test that a hardware sequenced acquisition can be aborted mid-sequence
       """
    mmc1 = Core()
    mmc1.set_property('Z', 'UseSequences', 'Yes')

    def hook_fn(_events):
        assert check_acq_sequenced(_events, 1000), 'Sequenced acquisition is not built correctly'
        return _events

    core = Core()
    core.set_exposure(200)

    save_directory = mic.filePath
    save_name = mic.fileName

    with Acquisition(save_directory, 'acq', show_display=True,
                     pre_hardware_hook_fn=hook_fn) as acq:
        events = multi_d_acquisition_events(z_start=0, z_end=999, z_step=1)
        acq.acquire(events)
        time.sleep(2)
        acq.abort()

    dataset = acq.get_dataset()
    assert (len(dataset.index) < 1000)


def check_acq_sequenced(events, expected_num_events):
    return isinstance(events, list) and len(events) == expected_num_events


def notZstack():
    if mic.zRange == 0 or mic.numStepsZ == 0:
        return True
    else:
        return False

def MeeladTest():
    # init task with 2 AO on DAQ
    mTask = ni.initTask2ao("MeeladTask")

    # gen seq
    timePoints = 1000
    aSin = 4.5
    fSin = 0.1
    offSin = 5
    x = np.arange(0, timePoints, 0.1)
    seqSin = aSin*np.sin(fSin*x) + offSin
    seqCos = aSin*np.cos(fSin*x) + offSin
    seq = np.zeros([2, timePoints*10])
    seq[0] = seqSin
    seq[1] = seqCos
    # send seq to DAQ
    # deal with timing on DAQ
    s = np.size(seq)
    mTask.timing.cfg_samp_clk_timing(rate=500, sample_mode=AcquisitionType.FINITE, samps_per_chan=timePoints*10)
    mTask.write(seq)
    # start task
    mTask.start()
    # wait for end of task
    # close task
    ni.waitStopCloseTask(mTask, 100)

    print('Hello Meelad')

    '''# # set single values
    # mTask = ni.initTask2ao("MeeladTask")  # InfoMeelad: get card ready - init 2 analog outputs
    # ni.setVoltage2ao(mTask, 5)
    # time.sleep(1)
    # ni.setVoltage2ao(mTask, 4)
    # time.sleep(1)
    # ni.setVoltage2ao(mTask, 3)
    # time.sleep(1)
    # ni.setVoltage2ao(mTask, 2)
    # time.sleep(1)
    # ni.setVoltage2ao(mTask, 1)
    # time.sleep(1)
    # ni.setVoltage2ao(mTask, 0)
    # ni.waitStopCloseTask(mTask, 10)'''

def getDevices():
    # reads uManagers hardware config file and lists all devices loaded 
    devices = mmc.get_loaded_devices()
    listDev = [devices.get(i) for i in range(devices.size())]
    return listDev


def loadConfig(path):
    mmc.load_system_configuration(path)


def getLaserFromList(lDev):
    # filters device list for substrings "laser" and "Laser"
    lLaser = []
    for dev in lDev:
        if dev.find('laser') != -1 or dev.find('Laser') != -1:
            lLaser.append(dev)
    mic.laserList = lLaser
    return lLaser


def isAOTFavailable(lDev):
    """ searches for substrings "aotf" and "AOTF" in devices """
    ret = False
    for dev in lDev:
        if dev.find('aotf') != -1 or dev.find('AOTF') != -1:
            ret = True
    return ret


def setLaser(c, val):
    # set laser power in uManager
    mmc.set_property(mic.laserList[c], 'Power', val)


def setLaserState(c, stat):
    # set laser state in uManager
    if c < len(mic.laserList):  # if laser slot is enabled
        mmc.set_property(mic.laserList[c], 'Laser', stat)


def setAOTF(c, val):
    # sets AOTF value in uManager
    if c > 0:  # if laser slot is enabled
        try:
            mmc.set_property('AAAOTF', 'Channel', str(c))  # changes to desired channel
            time.sleep(0.25)
            mmc.set_property('AAAOTF', 'Power (% of max)', val)  # sets power
        except:
            print('no device named AAAOTF found')


def setAOTFState(c, stat):
    # sets AOTF state in uManager
    if c > 0:  # if laser slot is enabled
        try:
            mmc.set_property('AAAOTF', 'Channel', str(c))  # changes to desired channel
            time.sleep(0.25)
            mmc.set_property('AAAOTF', 'State', stat)  # sets power
        except:
            print('no device named AAAOTF found')


def setLaserMode(stat):
    for c in range(len(mic.laserList)):
        print('set laser ' + mic.laserList[c] + ' to ' + stat)
        mmc.set_property(mic.laserList[c], 'Control Mode', stat)


def getLaserMin(las, stat):
    lasMin = mmc.get_property_lower_limit(las, stat)
    return lasMin


def getLaserMax(las, stat):
    lasMax = mmc.get_property_upper_limit(las, stat)
    return lasMax


def getLaserControlMode(las):
    cMode = mmc.get_property(las, 'Control Mode')
    return cMode


def setExposureTime(expT):
    mmc.set_exposure(expT)


def getUmExposureTime():
    expT = mmc.get_exposure()
    return expT
