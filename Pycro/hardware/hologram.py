from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import QRect, Qt
import numpy as np
import scipy
import tifffile
from softwareHelpers import jsonReadWrite as js

mic = []  # main microscopy instance (used to make sure main instance of mic is used in all files)


class Hologram:
    """generic class to define hologram specific properties"""
    def __init__(self, name):

        # general
        self.xOffset = float(400)                           # spatial offset of mask in x direction
        self.yOffset = float(300)                           # spatial offset of mask in y direction
        self.SLMmode = 'xy grating'                         # mode of pattern generation (Gauss, Bessel, ...)

        # Mask
        self.lowPass = float(5)                             # low pass filter in pix
        self.radiusOut = float(250)                         # outer radius for mask
        self.radiusIn = float(30)                           # inner radius for mask

        # grating
        self.xAngle = float(1)                              # grating period in x direction
        self.yAngle = float(5)                              # grating period in y direction
        self.xPer = float(1)                                # grating period in x direction
        self.yPer = float(5)                                # grating period in y direction
        self.xNA = float(1)                                 # grating period in x direction
        self.yNA = float(5)                                 # grating period in y direction

        # NA calculation
        self.pixS = float(2.0)                             # pixel size of SLM in mm
        self.flens = float(500)                             # focal lenght of lens after SLM
        self.fobjective = float(5)                          # assumed focal length of objective (flens = ftl/Mag)
        self.refractiveIdx = float(1.33)                    # refractive index

        # bessel
        self.rAngle = float(15)                             # grating period in radial direction
        self.rPer = float(15)                               # grating period in radial direction
        self.rNA = float(15)                                # grating period in radial direction

        # gauss
        self.radGauss = float(15)                           # radius of lens curvature

        # advanced
        self.name = name                                    # name the entity
        self.wavelength = float(0.492)                      # wavelength
        self.xPix = int(800)                                # SLM pixel in x
        self.yPix = int(600)                                # SLM pixel in y
        self.mainGUIgeo = []                                # geometry of initialised main GUI
        self.maxPhase = int(182)                            # phase to wrap SLM hologram in uint8

        # meelad Gauss
        self.meelad_dx = float(0)                           # distance of beams from xOffset
        self.meelad_dy = float(0)                           # distance of beams from yOffset

    def setMainGUIgeo(self, a):
        self.mainGUIgeo = a


class slmWindow(QtWidgets.QMainWindow):
    """slm window, should be displayed on slm screen"""
    def __init__(self):
        super().__init__()
        uic.loadUi('slm.ui', self)  # loads GUI
        self.setWindowTitle('SLM generator')
        self.show()

    def updateSLMwin(self):
        """ will update the slm gui with the generated hologram"""
        im = mic.slmIm                                                          # get image from mic
        image = QtGui.QImage(im, im.shape[1], im.shape[0], QtGui.QImage.Format_Indexed8) # convert to QImage
        pix = QtGui.QPixmap.fromImage(image)                                    # convert QImage to QPixmap
        self.la_im1.setGeometry(QRect(0, 0, im.shape[1], im.shape[0]))          # resizes display
        self.slmScrollArea.setGeometry(QRect(0, 0, im.shape[1], im.shape[0]))   # resize window
        self.la_im1.setPixmap(pix)
        # set image into display
        x = int(mic.screen1.size().height() / 2 - im.shape[0]/2)
        y = int(mic.screen0.size().width() + mic.screen1.size().width()/2 - im.shape[1]/2)
        self.move(y, x)


class slmGUI(QtWidgets.QMainWindow):
    """slm generator gui: to adjust SLM pattern parameters and update SLM screen"""
    slmWin = []     # SLM instance needed to update SLM

    def __init__(self):

        super().__init__()
        uic.loadUi('slmGUI.ui', self)  # loads GUI

        # set default values
        self.setWindowTitle('SLM generator')
        self.holo = Hologram('slmHolo')
        self.cb_SLMmode.addItem('xy grating')
        self.cb_SLMmode.addItem('Bessel')
        self.cb_SLMmode.addItem('Gauss')
        self.cb_SLMmode.addItem('Two Gauss')
        self.slmWin = slmWindow()
        js.initSLMjson(self)
        self.periodChange()

        # event listener
        self.cb_SLMmode.currentIndexChanged.connect(self.updateSLMgui)
        self.sb_lambda.valueChanged.connect(self.updateSLMgui)
        self.dsb_radius.valueChanged.connect(self.updateSLMgui)
        self.dsb_radIn.valueChanged.connect(self.updateSLMgui)
        self.dsb_rollOff.valueChanged.connect(self.updateSLMgui)
        self.dsb_xOff.valueChanged.connect(self.updateSLMgui)
        self.dsb_yOff.valueChanged.connect(self.updateSLMgui)
        self.dsb_xAngle.valueChanged.connect(self.angelChange)
        self.dsb_yAngle.valueChanged.connect(self.angelChange)
        self.dsb_rAngle.valueChanged.connect(self.angelChange)
        self.dsb_xPeriod.valueChanged.connect(self.periodChange)
        self.dsb_yPeriod.valueChanged.connect(self.periodChange)
        self.dsb_rPeriod.valueChanged.connect(self.periodChange)
        self.dsb_xNA.valueChanged.connect(self.NAchange)
        self.dsb_yNA.valueChanged.connect(self.NAchange)
        self.dsb_rNA.valueChanged.connect(self.NAchange)
        self.sb_xPix.valueChanged.connect(self.updateSLMgui)
        self.sb_yPix.valueChanged.connect(self.updateSLMgui)
        self.dsb_radGauss.valueChanged.connect(self.updateSLMgui)
        self.dsb_fLens.valueChanged.connect(self.updateSLMgui)
        self.dsb_fObj.valueChanged.connect(self.updateSLMgui)
        self.dsb_refractiveInd.valueChanged.connect(self.updateSLMgui)
        self.dsb_pixSizeSLM.valueChanged.connect(self.updateSLMgui)
        self.dsb_meelad_dy.valueChanged.connect(self.updateSLMgui)
        self.dsb_meelad_dx.valueChanged.connect(self.updateSLMgui)

        # show, move and update GUIs
        self.show()
        self.moveSLMgenGUI()
        self.updateSLMgui()

    def updateSLMgui(self):
        """ update holo with new parameters, write them to the json and update SLM """
        js.updateSLMholoClass(self)     # update holo class with new parameters
        js.writeSLMjson(self)           # update json file
        self.setSLM()                   # apply changes to SLM

    def setSLM(self):
        """ check which hologram mode is selected:
         'xy grating': tilt in x and y
         'r grating (Bessel)': radial phase increase + xy tilt
         tip: add phase image, multiply masks"""
        xx, yy, x, y = self.meshGrid()                                  # init variable to calculate hologram
        im = np.zeros([len(x), len(y)])
        self.modGUIwidgets(self.holo.SLMmode)
        if self.holo.SLMmode == 'xy grating':
            im = self.gratingXY2(xx, yy)                                 # generate pattern
        elif self.holo.SLMmode == 'Bessel':
            im = self.gratingR(xx, yy) + self.gratingXY(xx, yy)         # generate pattern
        elif self.holo.SLMmode == 'Gauss':
            im = self.gauss(xx, yy) + self.gratingXY2(xx, yy)            # generate pattern

        elif self.holo.SLMmode == 'Two Gauss':
            im = self.twogauss(xx, yy) + self.gratingXY(xx, yy)         # generate pattern
        else:
            print('SLM mode not recognized.')

        # imW = self.wrapPhaseFn(im, 2*np.pi*self.holo.maxPhase/255)      # wrap to max phase
        imW = self.wrapPhaseFn(im, self.holo.wavelength)  # wrap to max phase

        if self.holo.SLMmode == 'Two Gauss':
            # imWM = self.maskCircleTwoGauss(imW, xx, yy) # when use two masks at the same time
            imWM = imW  # when use one mask separated - using moving masks
        else:
            imWM = self.maskCircle(imW, xx, yy)                             # multiply masks

        self.displayImg(imWM)                                           # show hologram in GUI

    def modGUIwidgets(self, mode):
        if mode == 'xy grating':
            self.dsb_rAngle.setEnabled(False)  # disable/enable unused GUI widgets
            self.dsb_rPeriod.setEnabled(False)
            self.dsb_rNA.setEnabled(False)
            self.dsb_rAngle.show()
            self.dsb_rPeriod.show()
            self.dsb_rNA.show()
            self.la_radGauss.hide()
            self.dsb_radGauss.hide()
        elif mode == 'Bessel':
            self.dsb_rAngle.setEnabled(True)  # disable/enable unused GUI widgets
            self.dsb_rPeriod.setEnabled(True)
            self.dsb_rNA.setEnabled(True)
            self.la_radGauss.hide()
            self.dsb_radGauss.hide()
            self.dsb_rAngle.show()
            self.dsb_rPeriod.show()
            self.dsb_rNA.show()
            self.la_r.show()
        elif mode == 'Gauss' or mode == 'Two Gauss':
            self.la_radGauss.show()
            self.dsb_radGauss.show()
            self.dsb_rAngle.hide()
            self.dsb_rPeriod.hide()
            self.dsb_rNA.hide()
            self.la_r.hide()

    def maskCircle(self, im, xx, yy):
        """ multiply im with circular mask """
        mask = np.zeros((self.holo.yPix, self.holo.xPix))
        circle = np.sqrt((xx - self.holo.xOffset) ** 2 + (yy - self.holo.yOffset) ** 2)
        mask[circle < self.holo.radiusOut + 1] = 1
        mask[circle < self.holo.radiusIn] = 0
        mask = self.blurrImagGauss(mask, self.holo.lowPass)
        imMask = mask*im
        return imMask

    def maskCircleTwoGauss(self, im, xx, yy, displace_x, delta_y):
        """ multiply im with two circular masks """
        xc = self.holo.xOffset
        yc = self.holo.yOffset
        delta_x = self.holo.meelad_dx
        delta_y = self.holo.meelad_dy

        # ********  Two Phase and Two Mask  ********

        # One moving mask - Meelad
        # mask = np.zeros((self.holo.yPix, self.holo.xPix))
        # circle_move = np.sqrt((xx - xc + delta_x / 2) ** 2 + (yy - yc + delta_y / 2) ** 2)
        # mask[circle_move < self.holo.radiusOut + 1] = 1

        # ********  One Phase and Two Mask  ********

        # Two mask at the same time - Meelad
        mask = np.zeros((self.holo.yPix, self.holo.xPix))
        circle_d = np.sqrt((xx - xc - displace_x / 2) ** 2 + (yy - yc - delta_y / 2) ** 2)
        circle_u = np.sqrt((xx - xc + displace_x / 2) ** 2 + (yy - yc + delta_y / 2) ** 2)
        mask[circle_d < self.holo.radiusOut + 1] = 1
        mask[circle_u < self.holo.radiusOut + 1] = 1

        mask = self.blurrImagGauss(mask, self.holo.lowPass)
        imMask = mask * im
        return imMask

    def blurrImagGauss(self, im, rad):
        image = scipy.ndimage.gaussian_filter(im, sigma=rad, mode='reflect', truncate=4.0)
        return image

    def wrapPhaseFn(self, img, phase):
        """ wrap the image by phase """
        im = img % phase
        return im

    def displayImg(self, im):
        """ displays the hologram in GUI and on second screen """
        # im = im / (2*np.pi) * 255                       # conversion for uint, wavelength dependence
        im = im / self.holo.wavelength * self.holo.maxPhase # conversion for uint, wavelength dependence
        im = im.astype(np.uint8)                        # convert data type to uint8
        # tifffile.imwrite("D:\\SLM2.tiff", im)
        image = QtGui.QImage(im, im.shape[1], im.shape[0], QtGui.QImage.Format_Indexed8)    # to QImage
        pix = QtGui.QPixmap.fromImage(image)            # to QPixmap
        mic.slmIm = im                                  # sets image in mic (saving)
        self.la_im1.setGeometry(QRect(0, 0, im.shape[1], im.shape[0]))          # update GUI components
        self.scrollArea.setGeometry(QRect(10, 130, im.shape[1], im.shape[0]))   # update GUI components
        self.la_im1.setPixmap(pix)                                              # update GUI components
        self.slmWin.updateSLMwin()                                              # update GUI components of SLM
        self.slmWin.showFullScreen()

    def meshGrid(self):
        """ init vectors + arrays with length of hologram with increasing values"""
        x = np.linspace(0, self.holo.xPix-1, self.holo.xPix)
        y = np.linspace(0, self.holo.yPix-1, self.holo.yPix)
        xx, yy = np.meshgrid(x, y)
        return xx, yy, x, y

    def gratingXY(self, xx, yy):
        """ returns an image with grating in x and y direction """
        xGrating = np.tan(np.deg2rad(self.holo.xAngle)) * xx * self.holo.pixS
        yGrating = np.tan(np.deg2rad(self.holo.yAngle)) * yy
        gratingXY = xGrating + yGrating
        return gratingXY

    def gratingXY2(self, xx, yy):
        """ returns an image with grating in x and y direction """
        xGrating = np.tan(np.deg2rad(self.holo.xAngle)) * xx
        yGrating = np.tan(np.deg2rad(self.holo.yAngle)) * yy
        gratingXY = xGrating + yGrating
        return gratingXY

    def gratingR(self, xx, yy):
        """ returns an image with grating in r direction """
        circle = np.sqrt((xx - self.holo.xOffset) ** 2 + (yy - self.holo.yOffset) ** 2)
        # rGrating = np.tan(np.deg2rad(self.holo.rAngle)) * circle
        # Meelad
        rGrating = - np.tan(np.deg2rad(self.holo.rAngle)) * circle
        return rGrating

    def gauss(self, xx, yy):
        """ returns an image with grating in r direction """
        xc = self.holo.xOffset
        yc = self.holo.yOffset
        r_lens = self.holo.radGauss

        # Fred
        # gauss = ((xx - self.holo.xOffset) ** 2 + (yy - self.holo.yOffset) ** 2) / self.holo.radGauss
        # gauss = np.sqrt(self.holo.radGauss ** 2 - (xx - self.holo.xOffset) ** 2 - (yy - self.holo.yOffset) ** 2)

        # Lens Phase - Meelad
        # r = np.sqrt((xx - xc) ** 2 + (yy - yc) ** 2)
        # cmask = np.zeros((self.holo.yPix, self.holo.xPix))
        # cmask[r <= r_lens] = 1
        # lphase = r_lens ** 2 - r ** 2
        # gauss = np.sqrt(lphase * cmask)

        # Gauss Phase - Meelad
        r = np.sqrt((xx - xc) ** 2 + (yy - yc) ** 2)
        gauss = r_lens - (r ** 2) / (2 * r_lens)

        return gauss

    def twogauss(self, xx, yy):

        xc = self.holo.xOffset
        yc = self.holo.yOffset
        delta_x = self.holo.meelad_dx
        delta_y = self.holo.meelad_dy
        r_lens = self.holo.radGauss

        # ********  Two Phase and Two Mask  ********

        # ru = np.sqrt((xx - xc + delta_x / 2) ** 2 + (yy - yc + delta_y / 2) ** 2)
        # rd = np.sqrt((xx - xc - delta_x / 2) ** 2 + (yy - yc - delta_y / 2) ** 2)

        # Two Lens Phase - Meelad
        # cmasku = np.zeros((self.holo.yPix, self.holo.xPix))
        # cmasku[ru < r_lens] = 1
        # cmaskd = np.zeros((self.holo.yPix, self.holo.xPix))
        # cmaskd[rd < r_lens] = 1
        # phaseu = r_lens ** 2 - ru ** 2
        # phaseu = np.sqrt(phaseu * cmasku)
        # phased = r_lens ** 2 - rd ** 2
        # phased = np.sqrt(phased * cmaskd)

        # Two Gauss Phase - Meelad
        # phaseu = r_lens - (ru ** 2) / (2 * r_lens)
        # phased = r_lens - (rd ** 2) / (2 * r_lens)
        #
        # # One moving mask - Meelad
        # twogauss = self.maskCircleTwoGauss(phaseu, xx, yy, delta_x, delta_y) + \
        #            self.maskCircleTwoGauss(phased, xx, yy, -delta_x, -delta_y)

        # ********  One Phase and Two Mask  ********

        # Gauss Phase - Meelad
        r = np.sqrt((xx - xc) ** 2 + (yy - yc) ** 2)
        phase = r_lens - (r ** 2) / (2 * r_lens)
        twogauss = self.maskCircleTwoGauss(phase, xx, yy, delta_x, delta_y)

        return twogauss

    def angelChange(self):
        """change period and NA boxes and update SLM accordingly"""
        # change period
        self.dsb_xPeriod.blockSignals(True)  # disable event listener
        self.dsb_yPeriod.blockSignals(True)
        self.dsb_rPeriod.blockSignals(True)
        self.dsb_xPeriod.setValue(self.angle2period(self.dsb_xAngle.value()))  # update period
        self.dsb_yPeriod.setValue(self.angle2period(self.dsb_yAngle.value()))
        self.dsb_rPeriod.setValue(self.angle2period(self.dsb_rAngle.value()))
        self.dsb_xPeriod.blockSignals(False)  # enable event listener
        self.dsb_yPeriod.blockSignals(False)
        self.dsb_rPeriod.blockSignals(False)
        # change NA
        self.dsb_xNA.blockSignals(True)  # disable event listener
        self.dsb_yNA.blockSignals(True)
        self.dsb_rNA.blockSignals(True)
        self.dsb_xNA.setValue(self.period2NA(self.dsb_xPeriod.value()))  # update NA
        self.dsb_yNA.setValue(self.period2NA(self.dsb_yPeriod.value()))
        self.dsb_rNA.setValue(self.period2NA(self.dsb_rPeriod.value()))
        self.dsb_xNA.blockSignals(False)  # enable event listener
        self.dsb_yNA.blockSignals(False)
        self.dsb_rNA.blockSignals(False)
        # update holo and SLM
        self.updateSLMgui()

    def periodChange(self):
        """change angle and NA boxes and update SLM accordingly"""
        # change angle
        self.dsb_xAngle.blockSignals(True)  # disable event listener
        self.dsb_yAngle.blockSignals(True)
        self.dsb_rAngle.blockSignals(True)
        self.dsb_xAngle.setValue(self.period2angle(self.dsb_xPeriod.value()))  # update angle
        self.dsb_yAngle.setValue(self.period2angle(self.dsb_yPeriod.value()))
        self.dsb_rAngle.setValue(self.period2angle(self.dsb_rPeriod.value()))
        self.dsb_xAngle.blockSignals(False)  # enable event listener
        self.dsb_yAngle.blockSignals(False)
        self.dsb_rAngle.blockSignals(False)
        # change NA
        self.dsb_xNA.blockSignals(True)  # disable event listener
        self.dsb_yNA.blockSignals(True)
        self.dsb_rNA.blockSignals(True)
        self.dsb_xNA.setValue(self.period2NA(self.dsb_xPeriod.value()))  # update NA
        self.dsb_yNA.setValue(self.period2NA(self.dsb_yPeriod.value()))
        self.dsb_rNA.setValue(self.period2NA(self.dsb_rPeriod.value()))
        self.dsb_xNA.blockSignals(False)  # enable event listener
        self.dsb_yNA.blockSignals(False)
        self.dsb_rNA.blockSignals(False)
        # update holo and SLM
        self.updateSLMgui()

    def NAchange(self):
        """change angle and period boxes and update SLM accordingly"""
        # change period
        self.dsb_xPeriod.blockSignals(True)  # disable event listener
        self.dsb_yPeriod.blockSignals(True)
        self.dsb_rPeriod.blockSignals(True)
        self.dsb_xPeriod.setValue(self.NA2period(self.dsb_xNA.value()))  # update period
        self.dsb_yPeriod.setValue(self.NA2period(self.dsb_yNA.value()))
        self.dsb_rPeriod.setValue(self.NA2period(self.dsb_rNA.value()))
        self.dsb_xPeriod.blockSignals(False)  # enable event listener
        self.dsb_yPeriod.blockSignals(False)
        self.dsb_rPeriod.blockSignals(False)
        # change angle
        self.dsb_xAngle.blockSignals(True)  # disable event listener
        self.dsb_yAngle.blockSignals(True)
        self.dsb_rAngle.blockSignals(True)
        self.dsb_xAngle.setValue(self.period2angle(self.dsb_xPeriod.value()))  # update angle
        self.dsb_yAngle.setValue(self.period2angle(self.dsb_yPeriod.value()))
        self.dsb_rAngle.setValue(self.period2angle(self.dsb_rPeriod.value()))
        self.dsb_xAngle.blockSignals(False)  # enable event listener
        self.dsb_yAngle.blockSignals(False)
        self.dsb_rAngle.blockSignals(False)
        # update holo and SLM
        self.updateSLMgui()

    def NA2angle(self, NA):
        if NA == 0.0:
            return 0.0
        elif NA > self.holo.refractiveIdx:
            print("hologram/NA2angle: NA larger than refractive index")
            return self.holo.refractiveIdx
        else:
            angle = np.rad2deg(np.arctan(self.holo.fobjective / self.holo.flens * np.tan(np.arcsin(NA / self.holo.refractiveIdx))))
            return angle

    def angle2NA(self, angle):
        if angle == 0.0:
            return 0.0
        else:
            NA = np.sin(np.arctan(self.holo.flens / self.holo.fobjective * np.tan(np.deg2rad(angle)))) * self.holo.refractiveIdx
            return NA

    def NA2period(self, NA):
        if NA == 0.0:
            return 0.0
        elif NA > self.holo.refractiveIdx:
            print("hologram/NA2angle: NA larger than refractive index")
            return self.holo.refractiveIdx
        else:
            angle = np.arctan(self.holo.fobjective / self.holo.flens * np.tan(np.arcsin(NA / self.holo.refractiveIdx)))
            per = self.holo.wavelength / self.holo.pixS / np.tan(angle)
            return per

    def period2NA(self, per):
        if per == 0.0:
            return 0.0
        else:
            NA = np.sin(np.arctan(self.holo.flens / self.holo.fobjective * self.holo.wavelength/per/self.holo.pixS)) \
                 * self.holo.refractiveIdx
            return NA

    def period2angle(self, period):
        if period == 0.0:
            return 0.0
        else:
            angle = np.rad2deg(np.arctan(self.holo.wavelength / period / self.holo.pixS))
        return angle

    def angle2period(self, angle):
        if angle == 0.0:
            return 0.0
        else:
            period = self.holo.wavelength / self.holo.pixS / np.tan(np.deg2rad(angle))
            #period = 2 * np.pi / np.tan(np.deg2rad(angle))
            return period

    def moveSLMgenGUI(self):
        """ moves SLM generator GUI next to main GUI (cosmetics) """
        t = mic.mainGUIgeo.bottomRight()
        x = t.x()
        y = t.y() - self.geometry().height() - 30
        self.move(x, y)
