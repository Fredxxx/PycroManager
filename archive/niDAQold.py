import nidaqmx as ni
import matplotlib.pyplot as plt
import numpy as np
import labviewDLL as lv
#import uManagerInt as um
#import threading as TH
#from nidaqmx import stream_readers, stream_writers
import time

system = ni.system.System.local()
for device in system.devices:
    print(device)

pat = np.zeros(1)           # global variable for scan pattern
intTime = 10 * 10 ** -3
setTime = intTime*10
trigTime = 1 * 10 ** -3
delTime = 0.5*intTime
delTime2 = intTime-delTime-trigTime
outDat = np.zeros(2)
outputAO = np.zeros(2)


def generateScanPat2(mode):
    global pat
    if mode == 'AOstair':
        zStart = float(str(lv.InitialStepV)[9:-1])
        zEnd = zStart + float(str(lv.zRange)[9:-1])
        zStepS = float(str(lv.zRange)[9:-1])/float(str(lv.NumberOfZPlanes))
        pat = np.arange(zStart, zEnd, zStepS)
    return pat


def generateScanPat1(mode, outputDisplay):
    global pat
    if mode == 'stair+trig':
        aTrig = 5           # Amplitude trig
        aStair = 5          # Amplitude stair
        stepSize = 0.5      # of steps
        freq = int(aStair/stepSize) + 1 # how many triggers needed
        samp = freq * 2     # of samples written
        pat = np.zeros([samp, 0])
        # generate stair function (actually only line)
        t2 = np.linspace(0, 1, freq, endpoint=False)
        yStair = t2 * (aStair+stepSize)
        pat = yStair

        if outputDisplay == 1:                     # for plotting
            yTrig1 = np.zeros(samp)         # init trig values
            for j in range(0, samp):        # iterate trig values
                if (j % 2) == 0:
                    yTrig1[j] = 0
                else:
                    yTrig1[j] = aTrig
            t1 = np.linspace(0, 1, samp, endpoint=False)  # time axis
            c = np.empty((yStair.size * 2,), dtype=yStair.dtype) # stair
            c[0::2] = yStair
            c[1::2] = yStair
            plt.plot(t1, c, t1, yTrig1)
            plt.ylim(-1, aTrig+1)
        return pat


def writeAO(task, output1, output2):
    outputAO[0] = output1
    outputAO[1] = output2
    task.write(outputAO, auto_start=True)


def setSingleValueChAO(task, output1):
    task.write(output1, auto_start=True)


def setUpSingleChAO():
    task = ni.Task()
    task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
    return task


def closeTask(task1):
    task1.close()


def camStageTimingLast(task, j):
    writeAO(task, 5, pat[j])
    time.sleep(trigTime)
    writeAO(task, 0, 0) # should be 0 xxx, simulation purpose
    time.sleep(intTime)
    # include::: readout first image


def camStageTiming(task, j, pat1): # call this function adds a few ms per loop
    writeAO(task, 5, pat1[j])
    time.sleep(trigTime)
    writeAO(task, 0, pat1[j])
    time.sleep(delTime)
    writeAO(task, 0, pat1[j+1])
    time.sleep(delTime2)
    # include::: readout first image
    # move to next z plane
    #writeAO(task, 0, pat[j+1]) # should be 0 xxx, simulation purpose

'''
pat = generateScanPat1('stair+trig', 0)
um.prepMDA(len(pat))
um.startMDA()
with ni.Task() as taskAI, ni.Task() as taskAO:
    taskAI.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    taskAO.ao_channels.add_ao_voltage_chan("Dev1/ao0:1")
    # move stage to start position
    while 0 < 1:
        writeAO(taskAO, 0, pat[0])
        time.sleep(setTime)
        # first trigger to cam
        camStageTiming(taskAO, 0, pat)
        writeAO(taskAO, 5, pat[1])  # should be 0 xxx, simulation purpose
        i = 0
        while i < len(pat) - 2:
            # if cam finished received
            if taskAI.read() > 2.3:
                i += 1
                # isStageSettled
                camStageTiming(taskAO, i, pat)
        camStageTimingLast(taskAO, i+1)


def testAnalogInOut():
    with ni.Task() as taskAI, ni.Task() as taskAO:
        taskAI.ai_channels.add_ai_voltage_chan("Dev1/ai0")
        taskAO.ao_channels.add_ao_voltage_chan("Dev1/ao0")
        o = 0
        while True:
            if taskAI.read() > 2.3:
                o = 5
            else:
                o = 0
            taskAO.write(o, auto_start=True)
        #i+=1


#def setAOtask():
with ni.Task() as ao0, ni.Task() as ai0:
    fs = 200000
    NR_OF_CHANNELS = 2
    frames_per_buffer = 10
    refresh_rate_hz = 100000
    samples_per_frame = int(fs // refresh_rate_hz)
    timeRes = 1 / fs * samples_per_frame * 1000000
    read_buffer = np.zeros((NR_OF_CHANNELS, samples_per_frame), dtype=np.float64)
    timebase = np.arange(samples_per_frame) / fs



    ao0.ao_channels.add_ao_voltage_chan('Dev1/ao0')
    ao0.ao_channels.add_ao_voltage_chan('Dev1/ao1')
    ao0.timing.cfg_samp_clk_timing(rate=fs, sample_mode=ni.constants.AcquisitionType.CONTINUOUS)
    ao0.out_stream.output_buf_size = samples_per_frame * frames_per_buffer * NR_OF_CHANNELS
    #aiTh = TH.Thread(target=constantAIread, args=(1,))
    ai0.ai_channels.add_ai_voltage_chan('Dev1/ai0')
    ai0.triggers.start_trigger.cfg_dig_edge_start_trig("ao/StartTrigger", trigger_edge=ni.constants.Edge.RISING)
    ai0.timing.cfg_samp_clk_timing(rate=fs, sample_mode=ni.constants.AcquisitionType.CONTINUOUS)
    #ai0.input_buf_size = (samples_per_frame * frames_per_buffer, 1)

    ao0.out_stream.output_buf_size = samples_per_frame * frames_per_buffer * NR_OF_CHANNELS
    ai0.in_stream.input_buf_size = samples_per_frame * frames_per_buffer * NR_OF_CHANNELS

    reader = stream_readers.AnalogMultiChannelReader(ai0.in_stream)
    writer = stream_writers.AnalogSingleChannelWriter(ao0.out_stream)

    wave = np.zeros(samples_per_frame * frames_per_buffer)*0
    writer.write_many_sample(wave)
    output = np.zeros((1, 2))
    ao0.start()
    ai0.start()
    c = 0

    while c < 250:
        #reader.read_many_sample(data=output)
        reader.read_many_sample(output, samples_per_frame, timeout=ni.constants.WAIT_INFINITELY)
        #output = np.around(output, 2)  # Round all values to 2 decimals to avoid overflow
        #print(c)
        print(output)
        time.sleep(0.25)
        c=c+1
    #reader = ni.stream_readers.AnalogMultiChannelReader(ai0.in_stream)
    #writer = ni.stream_writers.AnalogMultiChannelWriter(ao0.out_stream)
    #ao0.timing.cfg_samp_clk_timing(1)
    #ao0.triggers.start_trigger.cfg_anlg_edge_start_trig("APFI0", trigger_level=2.3)

    #ao0.write([5, 5], auto_start=True)

    #runAcq = TH.Thread(target=runTest, args=(1,))
    #runAcq.start()
'''


def constantAIread():
    with ni.Task() as ai0:
        ai0.ai_channels.add_ai_voltage_chan('Dev1/ai1')
        ai0.triggers.start_trigger.cfg_dig_edge_start_trig("ao/StartTrigger", trigger_edge=ni.constants.Edge.RISING)


def runTest(self, a):
    print('runAcq started!')
    for i in range(0, 100):
        time.sleep(0.1)
        self.progressBar.setValue(i+1)
    print('runAcq finished!')


def generateScanPat(mode, output):
    global pat
    if mode == 'stair+trig':
        aTrig = 5           # Amplitude trig
        aStair = 5          # Amplitude stair
        stepSize = 0.5      # of steps
        freq = int(aStair/stepSize) + 1 # how many triggers needed
        samp = freq * 2     # of samples written
        pat = np.zeros([samp, 0])
        # generate stair function (actually only line)
        t2 = np.linspace(0, 1, freq, endpoint=False)
        yStair = t2 * (aStair+stepSize)
        pat = yStair

        if output == 1:                     # for plotting
            yTrig1 = np.zeros(samp)         # init trig values
            for j in range(0, samp):        # iterate trig values
                if (j % 2) == 0:
                    yTrig1[j] = 0
                else:
                    yTrig1[j] = aTrig
            t1 = np.linspace(0, 1, samp, endpoint=False)  # time axis
            c = np.empty((yStair.size * 2,), dtype=yStair.dtype) # stair
            c[0::2] = yStair
            c[1::2] = yStair
            plt.plot(t1, c, t1, yTrig1)
            plt.ylim(-1, aTrig+1)
        return pat
