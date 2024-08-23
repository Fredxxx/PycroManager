from pycromanager import Acquisition, multi_d_acquisition_events, Core, start_headless
import os
cwd = os.getcwd()

#umApp = "D:\\WorkStuff\\labA3Marc\\Pycro\\uManager\\Micro-Manager-2.0_20230524"
umApp = cwd + "\\uManager\\Micro-Manager-2.0_20230524"
umConfig1 = "D:\\WorkStuff\\labA3Marc\\Pycro\\uManager\\Micro-Manager-2.0_20230524\\MMConfig_demo.cfg"
umPort1 = 4847
#start_headless(umApp, umConfig1, port=umPort1)
#mmc1 = Core(port=umPort1)
save_dir = "C:\\temp"
print(cwd)
print(os.path.isdir(umApp))
print(os.path.isfile(umConfig1))

#
# def image_saved_fn(axes, dataset):
#     pixels = dataset.read_image(**axes)
#     # TODO: use the pixels for something, like post-processing or a custom image viewer
#
#
# with Acquisition(directory=save_dir, name="scan", show_display=True, port=umPort1, image_saved_fn=image_saved_fn) as acq:
#     events = multi_d_acquisition_events(num_time_points=5)
#     acq.acquire(events)
#
# # Another way to access to the saved data
# d = acq.get_dataset()
