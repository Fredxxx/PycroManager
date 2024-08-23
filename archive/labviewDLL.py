from ctypes import CDLL, c_double

dll = CDLL("D:\\WorkStuff\\LabView\\build\\marc9.dll")


MinVoltage = c_double(-5)
MaxVoltage = c_double(5)
InitialStepV = c_double(0)
TTLUptime = int(50)
triggerTimingMs = c_double(1)
delayMs = c_double(0)
NumberOfZPlanes = int(15)
zRange = c_double(5)
extDelay = c_double(0)


def getAllPara():
    return MinVoltage, MaxVoltage, InitialStepV, TTLUptime, triggerTimingMs, delayMs, NumberOfZPlanes, zRange


def setAOmax(a):
    global MaxVoltage
    MaxVoltage = c_double(a)
    print('setAOmax:', str(MaxVoltage))


def setAOmin(a):
    global MinVoltage
    MinVoltage = c_double(a)
    print('setAOmin:', str(MinVoltage))


def setIniZstep(a):
    global InitialStepV
    InitialStepV = c_double(a)
    print('setIniZstep:', str(InitialStepV))


def setTTLuptime(a):
    global TTLUptime
    TTLUptime = int(a)
    print('setTTLuptime:', str(TTLUptime))


def setTrigTiming(a, b):
    global triggerTimingMs
    c = a+b     # trigger time unit = exposure time + extra delay
    triggerTimingMs = c_double(c)
    print('setTrigTiming:', str(triggerTimingMs))


def setDelay(a):
    global delayMs
    delayMs = c_double(a)
    print('setDelay:', str(delayMs))


def setZsteps(a):
    global NumberOfZPlanes
    NumberOfZPlanes = int(a)
    print('setZsteps:', str(NumberOfZPlanes))


def setZrange(a):
    global zRange
    zRange = c_double(a)
    print('setZrange:', str(zRange))


def setExtDelay(a):
    global extDelay
    extDelay = c_double(a)
    print('setExtDelay:', str(extDelay))


def trigTime2exp():
    expT = triggerTimingMs - extDelay
    return expT
    print('trigTime2exp:', str(expT))


def setAOminmax(minV, maxV):
    global MinVoltage
    global MaxVoltage
    MinVoltage = c_double(minV)
    MaxVoltage = c_double(maxV)


def setAOsTo(ao0h, ao1h):
    ao0 = c_double(ao0h)
    ao1 = c_double(ao1h)
    dll.TwoAnalog_SetVoltage(MaxVoltage, MinVoltage, ao0, ao1)
    print('setAOsTo:', "ao0 set to", str(ao0))
    print('setAOsTo:', "ao1 set to", str(ao1))


def startTrigAndStair(TTLUptime1, triggerTimingMs1, delayMs1, InitialStepV1, NumberOfZPlanes1, zRange1):
    global TTLUptime
    global triggerTimingMs
    global delayMs
    global InitialStepV
    global NumberOfZPlanes
    global zRange
    TTLUptime = TTLUptime1
    triggerTimingMs = c_double(triggerTimingMs1)
    delayMs = c_double(delayMs1)
    InitialStepV = c_double(InitialStepV1)
    NumberOfZPlanes = NumberOfZPlanes1
    zRange = c_double(zRange1)
    dll.TwoAnalog_triggerAndStaircase_pyDLL_subVI(TTLUptime, MinVoltage, triggerTimingMs, MaxVoltage,
                                                  delayMs, InitialStepV, NumberOfZPlanes, zRange)
    print('startTrigAndStair:', "started")

