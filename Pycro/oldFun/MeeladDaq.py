import numpy as np
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType

# init task with 2 AO on DAQ
ni.Task(new_task_name='mTask')
mTask.ao_channels.add_ao_voltage_chan('Dev1/ao0')
mTask.ao_channels.add_ao_voltage_chan('Dev1/ao1')

# gen seq
timePoints = 1000
aSin = 5
fSin = 1
x = np.arange(0, timePoints, 0.1)
seqSin = aSin*np.sin(fSin*x)
seqCos = aSin*np.cos(fSin*x)
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
mTask.wait_until_done(timeout=100)
mTask.stop()
mTask.close()

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