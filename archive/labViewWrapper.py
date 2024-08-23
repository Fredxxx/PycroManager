
physChannels = "Dev1/ao0:1"         # ports for analog outputs
                                    # (first channel = stair function, second channel =trigger function)
minVoltage = -10                    # minimal voltage for both analog output channels
maxVoltage = 10                     # maximal voltage for both analog output channels
sampleClockSource = 'OnboardClock'  # sample clock source
zPlanes = 15                        # number of z planes
zRange = 5                          # scan range in z in V
startZpos = 0                       # initial z position in V
amplTTL = 5                         # high level of TTL pulse, low is always 0
triggerTime = 1                     # time for an up and high level circle of the TTL pulse in ms
TTLuptime = 50                      # percentage the TTL is in the high level stage
stepPoints = 1000                   # number of datapoints per TTL pulse
delay = 0.25                         # delay between trigger and stair signal in ms

def update_Variables()
    global minVoltage
    minVoltage =
def get_PhysicalChannels():
    return physChannels

def get_minVoltage():
    return minVoltage

def get_maxVoltage():
    return maxVoltage

def get_sampleClockSource():
    return sampleClockSource

def get_zPlanes():
    return zPlanes

def get_zRange():
    return zRange

def get_startZpos():
    return startZpos

def get_amplTTL():
    return amplTTL

def get_triggerTime():
    return triggerTime

def get_TTLuptime():
    return TTLuptime

def get_stepPoints():
    return stepPoints

def get_delay():
    return delay