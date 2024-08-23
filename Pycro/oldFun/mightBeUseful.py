
def saveTiffstack(frames):
    # saves multipage tiff in a simple way TODO: add metadata and make smart decisions if time, z or ... series
    # TODO: save subtiffs for large TIFF files
    save_directory = para.filePath
    save_name = para.fileName
    finPath = save_directory + '\\' + save_name + '_0000.tif'           # final save path
    c = 0
    while Path(finPath).exists():                     # check if path already exist and add number
        c += 1
        finPath = save_directory + '\\' + save_name + '_' + "{:04n}".format(c) + '.tif'
    print("Writing", len(frames), "frames to", finPath)
    img = np.array(frames, np.uint16).reshape(len(frames), len(frames[0]), len(frames[0][0]))
    tifffile.imwrite(finPath, img, imagej=True)
    # tifffile.imwrite(finPath, img, imagej=True, metadata=getMetadat('Z', len(frames)))


def twogaussMeelad(self, xx, yy):

    mask_d = np.zeros((self.holo.yPix, self.holo.xPix))
    mask_u = np.zeros((self.holo.yPix, self.holo.xPix))

    circle_d = np.sqrt((xx - self.holo.xOffset - self.holo.meelad_dx) ** 2 +
                       (yy - self.holo.yOffset - self.holo.meelad_dy) ** 2)

    circle_u = np.sqrt((xx - self.holo.xOffset + self.holo.meelad_dx) ** 2 +
                       (yy - self.holo.yOffset + self.holo.meelad_dy) ** 2)

    mask_d[circle_d < self.holo.radiusOut + 1] = 1
    mask_u[circle_u < self.holo.radiusOut + 1] = 1

    mask_d = self.blurrImagGauss(mask_d, self.holo.lowPass)
    mask_u = self.blurrImagGauss(mask_u, self.holo.lowPass)

    rcoord_d = (xx - self.holo.xOffset - self.holo.meelad_dx) ** 2 +\
               (yy - self.holo.yOffset - self.holo.meelad_dy) ** 2

    rcoord_u = (xx - self.holo.xOffset + self.holo.meelad_dx) ** 2 +\
               (yy - self.holo.yOffset + self.holo.meelad_dy) ** 2

    gauss_meelad_d = (rcoord_d / (2 * self.holo.radGauss)) * mask_d
    gauss_meelad_u = (rcoord_u / (2 * self.holo.radGauss)) * mask_u
    gauss_meelad = gauss_meelad_d + gauss_meelad_u

    return gauss_meelad

def getMetadat(ser, l):
    posZ = np.zeros(l)
    for i in range(l):
        posZ[i] = i
    meta = {
        'Pixels': {
            'PhysicalSizeX': 0.102,
            'PhysicalSizeXUnit': 'µm',
            'PhysicalSizeY': 0.102,
            'PhysicalSizeYUnit': 'µm'},
        'Plane': {'PositionZ': posZ},
    }
    return meta



def cameraHookFn(event):
    ''' hook function: code is executed after each camera image '''
    patt = getPattern()
    c = getCount()
    #print(event['axes']['z'])
    ni.setSingleValueChAO(getAOTask(), patt[event['axes']['z']])     # changes AO value
    time.sleep(para.addTime)                            # extra delay for stage settling
    return event


def preHardwareFn(event):
    # hook function: code is executed before hardware does stuff
    # print('preHardwareFn')
    countH = getCount()
    countH += 1
    c = int((countH+1)*countTick)                        # for progressbar
    if acqFlag:                                     # runs for uninterrupted acq
        progressEmit.emit(c)
    else:                                           # acq interrupted
        event = None                                # sends none to pycromanagers acquisition engine to not do anything
        if h1Flag:                                  # complicated way to only print interrupt statement once
            setH1Flag(False)
            print('Acquisition interrupted at', c, '%')
    setCount(countH)
    return event



def uManagerMDA(prog):
    """ multidimensional acquisition in uManager mode
        uManger -> use uManager loaded stage in "core-focus", no DAQ card used (slow)
        uMangerAO -> use analog modulation input of stage via DAD card (faster) """
    # start = time.time() # debug:timing
    tracemalloc.start()

    # set progressBar signal, interruption flag and saving directory
    setProgressEmit(prog)
    setH1Flag(True)
    save_directory = Path(para.filePath)
    save_name = para.fileName

    # get hardware (stage, cam) ready
    zStage = mmc.get_focus_device()  # Fetch currently used Piezostage.
    PiezoStage = stag.getStageZ(zStage)
    para.setZstageLimits(mmc.get_property_lower_limit(PiezoStage.name, PiezoStage.position),
                         mmc.get_property_upper_limit(PiezoStage.name, PiezoStage.position))
    preScanPos = mmc.get_position(PiezoStage.name)

    # cam.setCamMode("uManagerMode")
    # generate scan patterns and um events
    if notZstack():
        print("No, scan pattern generated.")
    else:
        if mode == 'uManager' or notZstack():
            para.InitialStepV = preScanPos
            setPattern(ni.generateScanPat('stair'))     # generate pattern in um direct
        elif mode == 'uManagerAO':
            try:
                mmc.set_focus_device('Z')  # TODO set 'DStage' into initFile
            except:
                try:
                    mmc.set_focus_device('DStage')  # TODO set 'DStage' into initFile
                except:
                    print("Could not change focusing device to demo ('Z' or 'DStage')")
            mmc.set_property(PiezoStage.name, PiezoStage.position, preScanPos - para.zRange / 2)
            para.InitialStepV = 0                            # for relative Piezo movement.
            setPattern(ni.generateScanPat('AOstair'))        # generate AO pattern
    setCountTick(100, len(patUM), para.tSteps)           # calc % per each image
    events = genMDAevents()
    setCount(-1)                                 # set count to 0

    # do acquisition
    if mode == 'uManager' or notZstack():
        with Acquisition(directory=save_directory, name=save_name, pre_hardware_hook_fn=preHardwareFn,
                         show_display=False, saving_queue_size=5000) as acq:
            acq.acquire(events)
    elif mode == 'uManagerAO':
        setAOTask(ni.setUpSingleChAO("Dev1/ao0"))  # initialise task (AO output)
        start = time.time()
        with Acquisition(directory=save_directory, name=save_name, pre_hardware_hook_fn=preHardwareFn,
                         post_camera_hook_fn=cameraHookFn, show_display=False, saving_queue_size=5000) as acq:
            acq.acquire(events)                 # do acquisition
        end = time.time()
        ni.setSingleValueChAO(getAOTask(), 0)
        ni.closeTask(taskAO)
        diff = (end - start) / len(events) * 10 ** 3
        fps = 1 / diff * 10 ** 3
        print('1. time per image:', str(diff))
        print('1. fps:', str(fps))
    else:
        print("no such uManager moder registered")

    # reset stage
    mmc.set_focus_device(zStage)
    mmc.set_position(zStage, preScanPos)

    # end = time.time() # debug: timing
    # print('uManager time per vol: ' + str((end - start) * 10 ** 3) + '[ms]') # debug: timing
    # print('uManager time per image after close task: ' + str((end-start)/len(pat)*10**3) + '[ms]') # debug: timing

    def displayImgOld(self, im):
        plt.close()
        plt.imshow(im, cmap='gray')
        mngr = plt.get_current_fig_manager()
        self.setFigGUI(mngr)
        plt.axis('scaled')
        plt.colorbar()
        plt.show()

        # in gui
        im = im / np.pi / 2 * 255
        im = im.astype(np.uint8)
        image = QtGui.QImage(im, im.shape[1], im.shape[0], QtGui.QImage.Format_Indexed8)
        pix = QtGui.QPixmap.fromImage(image)
        self.la_im1.setGeometry(QRect(0, 0, im.shape[1], im.shape[0]))
        print(self.imDis.geometry())
        self.imDis.setGeometry(QRect(10, 10, im.shape[1], im.shape[0]))
        self.la_im1.setPixmap(pix)
        print(self.imDis.geometry())
        # self.gl_im.addWidget(self.la_im)
        # self.setLayout(self.gl_im)

    def setFigGUI(self, mngr):
        geom = mngr.window.geometry()
        x, y, dx, dy = geom.getRect()
        t = mic.mainGUIgeo
        mainHeight = t.height()
        slmGenHeight = self.geometry().height()
        slmGenWidth = self.geometry().width()
        dyy = mainHeight - slmGenHeight - 30
        newX = t.bottomRight().xx()
        newY = t.bottomRight().yy() - slmGenHeight - 30 - dyy
        mngr.window.setGeometry(newX, newY, slmGenWidth, dyy)