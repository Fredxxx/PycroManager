mic = []  # main microscopy instance (used to make sure main instance of mic is used in all files)


class Cam:
    """generic class to define camera specific properties callable via uManager"""
    def __init__(self, name):
        self.name = name                                    # name of camera
        self.sensorMode = 'N/A'                             # area vs light sheet
        self.trigger = 'N/A'                                # normal vs sequencing
        self.triggerPolarity = 'N/A'                        # pos vs neg
        self.triggerSource = 'N/A'                          # internal vs external
        self.trigOutKind = 'N/A'                            # type of trigger out
        self.trigOutPol = 'N/A'                             # polarity of trigger out
        self.trigOutDel = 'N/A'                             # delay of trigger out
        self.exposure = 'N/A'                               # exposure time
        self.expUnits = 'N/A'                               # units of exposure time
        self.pixType = 'N/A'                                # such as 16bit


def getCam(camName):
    """This function returns an instance of the camera with used properties."""
    camera = Cam(camName)
    if camName == 'HamamatsuHam_DCAM':
        camera.sensorMode = 'SENSOR MODE'
        camera.trigger = 'Trigger'
        camera.triggerPolarity = 'TriggerPolarity'
        camera.triggerSource = 'TRIGGER SOURCE'
        camera.trigOutKind = 'OUTPUT TRIGGER KIND[0]'
        camera.trigOutPol = 'OUTPUT TRIGGER POLARITY[0]'
        camera.trigOutDel = 'OUTPUT TRIGGER DELAY[0]'
        camera.exposure = 'Exposure'
        camera.expUnits = 'EXPOSURE TIME UNITS'
        camera.pixType = 'PixelType'
    elif camName == 'spinnaker':    # TODO set up for FLIR cams
        camera.exposure = 'Exposure'
    mic.camera = camera.name
    return camera


def setTrig(cam, trigMode):
    if cam.name == 'HamamatsuHam_DCAM':
        if trigMode == "external":
            mic.core.set_property(cam.name, cam.triggerSource, 'EXTERNAL')
            mic.core.set_property(cam.name, cam.triggerPolarity, 'POSITIVE')
            mic.core.set_property(cam.name, cam.trigger, 'NORMAL')
        elif trigMode == 'internal':
            mic.core.set_property(cam.name, cam.triggerSource, 'INTERNAL')
        else:
            print("camera/setCamTrig: Could not identify trigger mode of Hamamatsu_DCAM!")
    elif cam.name == 'Camera':
        if trigMode == "external":
            print("Demo cam set to external!")
        elif trigMode == 'internal':
            print("Demo cam set to internal!")
        else:
            print("camera/setCamTrig: Could not identify trigger mode of Camera (Demo cam)!")
    else:
        print("camera/setCamTrig: Could not identify camera instance!")


def setTrigOut(cam, trigMode):
    if trigMode == 'AOTF':
        mic.core.set_property(cam.name, cam.trigOutKind, 'EXPOSURE')
        mic.core.set_property(cam.name, cam.trigOutPol, 'POSITIVE')
    else:
        print("camera/setTrigOut: Could not identify trigger out mode!")


def getImageProp():
    # determine image size
    mic.core.snap_image()
    y_pixels = mic.core.get_image_height()
    x_pixels = mic.core.get_image_width()
    return y_pixels, x_pixels
