from pycromanager import Core, Acquisition, multi_d_acquisition_events
import time
from hardware import niDAQ as ni
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType
import nidaqmx.stream_writers as niWriters
import numpy as np

task = []


def initTask2ao():
    aoTask = ni.Task(new_task_name="task2ao")
    aoTask.ao_channels.add_ao_voltage_chan('Dev2/ao0')
    aoTask.ao_channels.add_ao_voltage_chan('Dev2/ao1')
    return aoTask


def getSamples2ao():
    reps = 20  # how many times an event (cam triggering) is happening
    samplesPerEvent = 40  # samples per event
    aCamTrig = 5  # amplitude for camera trigger
    upTime = 0.25  # TTL uptime

    numUps = int(samplesPerEvent * upTime)
    numDown = int(samplesPerEvent - numUps)
    samples = np.zeros([2, samplesPerEvent])

    seqTTL = []
    seqAO = []
    for i in range(reps):
        seqTTL = np.append(aCamTrig * np.ones(numUps), np.zeros(numDown))
        seqAO = np.append(np.zeros(numUps), aCamTrig * np.ones(numDown))

    samples[0] = seqTTL
    samples[1] = seqAO

    return samples


def setUpTask(task1):
    reps = 20 # how many times an event (cam triggering) is happening
    expTime = 35 # in ms
    delTimeZ = 9  # in ms if expTime too fast for cam
    samplesPerEvent = 40  # samples per event

    freq = 1 / ((expTime+delTimeZ) * 10 ** -3)
    numSamples = samplesPerEvent * reps
    rate = freq * samplesPerEvent

    task1.timing.cfg_samp_clk_timing(rate=rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=numSamples)
    task1.write(samp)


def closeTask(task2, timeOut):
    task2.wait_until_done(timeout=timeOut)
    task2.stop()
    task2.close()


def getTask():
    return task

st = 0
en = 5
numStep = 18.5
step = (en-st)/numStep
#
# ev = multi_d_acquisition_events(z_start=st, z_end=en, z_step=step, num_time_points=5, time_interval_s=0, order='zt')
# ev = multi_d_acquisition_events(num_time_points=100, time_interval_s=0)
ev = multi_d_acquisition_events(z_start=st, z_end=en, z_step=step)

for i in range(len(ev)):
    print(ev[i])
    #print(ev[i]['axes']["z"])


def hookFn(event):
    task.start()
    return event


task = initTask2ao()
samp = getSamples2ao()
setUpTask(task)
print(task)

start = time.time()
with Acquisition(directory="C:\\temp", name="scan", show_display=True, post_camera_hook_fn=hookFn) as acq:
    acq.acquire(ev)
end = time.time()

print((end-start)*10**3)
closeTask(task, 25)
diff = (end-start-0.5)/len(ev)*10**3
fps = 1/diff*10**3
print('time per image:', str(diff))
print('fps:', str(fps))


def initTask2ao():
    aoTask = ni.Task()
    aoTask.ao_channels.add_ao_voltage_chan('Dev2/ao0')
    aoTask.ao_channels.add_ao_voltage_chan('Dev2/ao1')
    return aoTask


def getSamples2ao():
    reps = 10  # how many times an event (cam triggering) is happening
    samplesPerEvent = 40  # samples per event
    aCamTrig = 5  # amplitude for camera trigger
    upTime = 0.25  # TTL uptime

    numUps = int(samplesPerEvent * upTime)
    numDown = int(samplesPerEvent - numUps)
    samples = np.zeros([2, samplesPerEvent])

    seqTTL = []
    seqAO = []
    for i in range(reps):
        seqTTL = np.append(aCamTrig * np.ones(numUps), np.zeros(numDown))
        seqAO = np.append(np.zeros(numUps), aCamTrig * np.ones(numDown))

    samples[0] = seqTTL
    samples[1] = seqAO

    return samples


def setUpTask(task1):
    reps = 10  # how many times an event (cam triggering) is happening
    expTime = 20  # in ms
    delTimeZ = 0  # in ms if expTime too fast for cam
    samplesPerEvent = 40  # samples per event

    freq = 1 / ((expTime+delTimeZ) * 10 ** -3)
    numSamples = samplesPerEvent * reps
    rate = freq * samplesPerEvent

    task1.timing.cfg_samp_clk_timing(rate=rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=numSamples)
    task1.write(samp)


def closeTask(task2, timeOut):
    task2.wait_until_done(timeout=timeOut)
    task2.stop()
    task2.close()


# task = initTask2ao()
# samp = getSamples2ao()
# setUpTask(task)
# task.start()
# closeTask(task, 10)
