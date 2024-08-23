# class to communicate with NI DAQ card
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType
import numpy as np
#from softwareHelpers import parameters as p

import time

# system = ni.system.System.local()
# for device in system.devices:
#    print(device)
mic = []  # main microscopy instance (used to make sure main instance of mic is used in all files)


def initTask2ao(name):
    """ initialises task with two analog outputs """

    aoTask = ni.Task(new_task_name=name)
    aoTask.ao_channels.add_ao_voltage_chan('Dev1/ao0')              # TODO remove hard coding for Dev2
    aoTask.ao_channels.add_ao_voltage_chan('Dev1/ao1')

    return aoTask


def initDaqSeq():
    """ initialises sequence for DAQ card for
        channel ao0: TTL signal
        channel ao1: AO step signal"""

    # get some numbers ready
    numUps = int(mic.digEvent * mic.uptimeTTL * 0.01)               # how many points per TTL in upstate
    numDown = int(mic.digEvent - numUps)                            # how many points per TTL in downstate
    seqTTL = []                                                     # initialise TTL seq vector
    seqAO = []                                                      # initialise AO seq vector
    patAO = generateScanPat()[1]

    # calculate and stack seq for each TTL pulse
    for i in range(mic.numStepsZ):
        seqTTL = np.append(seqTTL, np.append(mic.amplitudeTTL * np.ones(numUps), np.zeros(numDown)))
        seqAO = np.append(seqAO, patAO[i] * np.ones(mic.digEvent))

    # initialise and populate final seq
    seq = np.zeros([2, mic.digEvent * mic.numStepsZ])
    seq[0] = seqTTL
    seq[1] = seqAO
    # set last val to start (return stage to starting position)
    d = len(seqTTL) + int(mic.expTime / (mic.expTime + mic.addTime) * mic.digEvent) - mic.digEvent
    seqAO1 = np.roll(seqAO, d)
    seqAO1[d:] = patAO[i]
    seqAO1[-1:] = patAO[0]
    seq[1] = seqAO1

    return seq


def initDaqSeqLS():
    """ initialises sequence for DAQ card for
        channel ao0: TTL signal
        channel ao1: AO step signal"""

    # get some numbers ready

    numUps = int(mic.digEvent * mic.uptimeTTL * 0.01)               # how many points per TTL in upstate
    numDown = int(mic.digEvent - numUps)                            # how many points per TTL in downstate
    seqTTL = []                                                     # initialise TTL seq vector
    seqAO = []                                                      # initialise AO seq vector
    patAO = generateScanPatLS()[1]
    deltaDigEv = mic.digEvent - len(patAO)

    # calculate and stack seq for each TTL pulse
    for i in range(mic.numStepsZ):
        seqTTL = np.append(seqTTL, np.append(mic.amplitudeTTL * np.ones(numUps), np.zeros(numDown)))
        seqAO = np.append(seqAO, np.append(patAO, patAO[0] * np.ones(deltaDigEv)))

    # initialise and populate final seq
    seq = np.zeros([2, mic.digEvent * mic.numStepsZ])
    seq[0] = seqTTL
    seq[1] = seqAO

    return seq


def initDaqSeqLSsnapShot():
    """ initialises sequence for DAQ card for
        channel ao0: TTL signal
        channel ao1: AO step signal"""

    # get some numbers ready
    numUps = int(mic.digEvent * mic.uptimeTTL * 0.01)                   # how many points per TTL in upstate
    numDown = int(mic.digEvent - numUps)                              # how many points per TTL in downstate
    seqTTL = []                                                     # initialise TTL seq vector
    patAO = generateScanPatLS()[1]

    # calculate and stack seq for each TTL pulse
    seqTTL = np.append(mic.amplitudeTTL * np.ones(numUps), np.zeros(numDown))

    # initialise and populate final seq
    seq = np.zeros([2, mic.digEvent])
    seq[0] = patAO
    seq[1] = seqTTL

    return seq


def switchRows(seq):
    seq1 = np.zeros([2, int(seq.size/2)])
    s1 = seq[0]
    s2 = seq[1]
    seq1[0] = s2
    seq1[1] = s1
    return seq1


def setTaskTiming(task, seq):
    """ sets the timing of the analog out put """

    # get things ready
    freq = 1 / ((mic.expTime + mic.addTime) * 10 ** -3)                  # calculate freq for TTL pulse seq
    numSamples = mic.digEvent * mic.numStepsZ                            # how may samples to send
    rate = freq * mic.digEvent                                         # rate a single sample will be sent

    # set timing and write sequence to task
    task.timing.cfg_samp_clk_timing(rate=rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=numSamples)
    task.write(seq)


def setTaskTimingSnapShotLS(task, seq):
    """ sets the timing of the analog out put """

    # get things ready
    freq = 1 / ((mic.expTime + mic.addTime) * 10 ** -3)  # calculate freq for TTL pulse seq
    numSamples = mic.digEvent  # how may samples to send
    rate = freq * mic.digEvent  # rate a single sample will be sent

    # set timing and write sequence to task
    task.timing.cfg_samp_clk_timing(rate=rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=numSamples)
    task.write(seq)


def stopCloseTask(task):
    """ stops task"""
    if not task == []:
        try:
            task.stop()
        finally:
            print("No task to stop")


def waitForTask(task, timeOut):
    """ 1. wait 'timeOut' or until task is done, 2. stop task, 3. close task """
    task.wait_until_done(timeout=timeOut)


def waitStopCloseTask(task, timeOut):
    """ 1. wait 'timeOut' or until task is done, 2. stop task, 3. close task """
    task.wait_until_done(timeout=timeOut)
    task.stop()
    task.close()


def setVoltage2ao(task, num):
    """ write a single value to a two AO channel task """
    task.stop()
    task.timing.cfg_samp_clk_timing(rate=1000, sample_mode=AcquisitionType.FINITE, samps_per_chan=2)
    sam = np.zeros([2, 2])
    sam[0] = [num, num]
    sam[1] = [num, num]
    task.write(sam, auto_start=True)


def galvoOscilate(gStart, gEnd, gFreq, reps):
    numSamples = 2000
    stepSize = np.abs(2*(gStart-gEnd)/numSamples)
    arr1 = np.arange(gStart, gEnd, stepSize)  # generate stair function in um
    arr2 = arr1[::-1]
    arr0 = np.concatenate([arr1, arr2])
    arrV = um2v(arr0, 'galvo')
    with ni.Task() as task:
        task.ao_channels.add_ao_voltage_chan('Dev1/ao0')  # TODO remove hard coding for Dev2
        task.ao_channels.add_ao_voltage_chan('Dev1/ao1')
        task.timing.cfg_samp_clk_timing(rate=1000, sample_mode=AcquisitionType.FINITE, samps_per_chan=numSamples)
        task.write(arrV)
        task.start()


def writeSingleAOcopmlete(val):
    with ni.Task() as task:
        task.ao_channels.add_ao_voltage_chan('Dev1/ao0')  # TODO remove hard coding for Dev2
        task.ao_channels.add_ao_voltage_chan('Dev1/ao1')
        task.timing.cfg_samp_clk_timing(rate=1000, sample_mode=AcquisitionType.FINITE, samps_per_chan=2)
        sam = np.zeros([2, 2])
        sam[0] = [val, val]
        sam[1] = [0, 0]
        task.write(sam, auto_start=True)


def setVoltage2aoDiff(task, num0, num1):
    """ write a single value to a two AO channel task """
    task.stop()
    task.timing.cfg_samp_clk_timing(rate=1000, sample_mode=AcquisitionType.FINITE, samps_per_chan=2)
    sam = np.zeros([2, 2])
    sam[0] = [num0, num0]
    sam[1] = [num1, num1]
    task.write(sam, auto_start=True)


def generateScanPat():
    """ generates simple scan pattern for z focus (single line) """

    mic.stepSizeZ = mic.zRange / (mic.numStepsZ - 1)                # calc number of z planes
    mic.posStartZ = mic.InitialStepV                              # start position of scan pattern
    zEnd = mic.posStartZ + mic.zRange + mic.stepSizeZ               # end (+1 for range function)
    # p.posStartZ, zEnd = checkScanLimits(p.posStartZ, zEnd)  # check scan limits TODO needs checking
    patUM = np.arange(mic.posStartZ, zEnd, mic.stepSizeZ)         # generate stair function in um
    patV = um2v(patUM, 'stage')                               # convert um stair to v stair
    mic.posEndZ = mic.posStartZ + mic.zRange                        # set zEnd in para

    return patUM, patV


def generateScanPatLS():
    """ generates simple scan pattern for z focus (single line) """

    stepSizeG = np.abs(mic.galvoStart - mic.galvoEnd) * (mic.expTime + mic.addTime) / mic.digEvent / mic.expTime # calc stepsize of datapoints
    # p.posStartZ, zEnd = checkScanLimits(p.posStartZ, zEnd)   # check scan limits TODO needs checking
    patUM = np.arange(mic.galvoStart, mic.galvoEnd, stepSizeG)     # generate stair function in um
    patV = um2v(patUM, 'galvo')                                # convert um stair to v stair

    return patUM, patV


def um2v(d, mode):
    """ converts um into V using look up table (LUT) """

    if mode == 'stage':
        lut = mic.lut                                                  # load LUT
    elif mode == 'galvo':
        lut= mic.lutGalvo                                              # load LUT galvo
    else:
        print("niDAQ/um2V: Could not find mode of AO device.")

    if isinstance(d, float):                                        # convert a single float
        idx = (np.abs(lut[:, 1]-d)).argmin()
        val = lut[idx, 0]
    elif isinstance(d, int):                                        # convert a single int
        idx = (np.abs(lut[:, 1] - d)).argmin()
        val = lut[idx, 0]
    else:                                                           # convert a vector of values
        val1 = []
        for k in d:
            idx = (np.abs(lut[:, 1] - k)).argmin()
            val1.append(lut[idx, 0])
        val = np.array(val1)

    return val


def freeNIdev():
    system = ni.system.System.local()  # load local system
    task_names = system.tasks.task_names  # returns a list of task names
    for task in system.tasks:
        stopCloseTask(task)
    # loaded_task = task.load()  # load the task


# old functions might still be used somewhere TODO needs checking which are obsolete

def checkScanLimits(start, end):
    # checks scan limits and sets to min or max value
    s, e = mic.getZstageLimits()
    if start < s:
        start = s
        print("Lower stage limit reached. Scan range limited.")
    elif end > e:
        end = e
        print("Upper stage limit reached. Scan range limited.")
    return start, end


def setSingleValueChAO(task, out):
    # writes a single value to AO output
    task.write(out, auto_start=True)


def readSingleValueAI(task):
    # reads a single value to AO output
    out = task.read()
    return out


def setDoubleChAO(task, trigState, out2):
    # writes a doublet value to two AO outputs
    if trigState == 'high':
        out1 = 5
    elif trigState == 'low':
        out1 = 0
    else:
        out1 = trigState
    task.write([out1, out2], auto_start=True)


def setUpSingleChAO(a):
    # initialise a task with an AO output channel
    chName = a
    task = ni.Task()
    task.ao_channels.add_ao_voltage_chan(chName)
    return task


def setUpSingleChAI(a):
    # initialise a task with an AO output channel
    chName = a
    task = ni.Task()
    task.ai_channels.add_ai_voltage_chan(chName)
    return task


def closeTask(task1):
    # closes a task
    task1.close()
