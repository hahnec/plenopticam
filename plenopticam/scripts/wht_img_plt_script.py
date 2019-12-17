
# local imports
from plenopticam import lfp_calibrator
from plenopticam.cfg import PlenopticamConfig
from plenopticam import lfp_reader
from plenopticam.lfp_aligner import LfpRotator

try:
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
except ImportError:
    raise ImportError("Package matplotlib wasn't found.")


import numpy as np

def plot_centroids(img, centroids, fn):

    centroids = np.asarray(centroids)
    img = (img-img.min())/(img.max()-img.min())

    plt.style.use("ggplot")

    #plt.imshow(img)
    #plt.plot(centroids[:, 1], centroids[:, 0], 'rx')

    s = 3
    h, w, c = img.shape
    hp, wp = 150, 200
    fig, axs = plt.subplots(s, s, facecolor='w', edgecolor='k')#, figsize=(15, 6), )

    for i in range(s):
        for j in range(s):

            # plot cropped image part
            k = i * (h//s) + (h//s)//2 - hp//2
            l = j * (w//s) + (w//s)//2 - wp//2
            axs[i, j].imshow(img[k:k+hp, l:l+wp, :])

            # plot cropped centroids
            conditions = (centroids[:, 1] >= l) & (centroids[:, 1] <= l+wp-.5) & \
                         (centroids[:, 0] >= k) & (centroids[:, 0] <= k+hp-.5)
            x_centroids = centroids[:, 1][conditions]
            y_centroids = centroids[:, 0][conditions]
            axs[i, j].plot(x_centroids-l, y_centroids-k, 'rx')

    plt.show()
    #plt.savefig('input+mics'+fn+'.eps', format='eps')

    #import tikzplotlib
    #tikzplotlib.save('input+mics'+fn+'.tex')

    return True

# create config object
cfg = PlenopticamConfig()
#cfg.default_values()
#cfg.reset_values()

cfg.params[cfg.cal_path] = "/Users/Admin/Pictures/Plenoptic/CalibFolder/caldata-B5144000580.tar"
cfg.params[cfg.lfp_path] = "/Users/Admin/Pictures/Plenoptic/INRIA_SIROCCO/Mini.LFR"
cfg.params[cfg.opt_cali] = True

cal_opt = False

if cal_opt:
    # decode light field image
    lfp_obj = lfp_reader.LfpReader(cfg)
    lfp_obj.main()
    lfp_img = lfp_obj.lfp_img
    del lfp_obj

# automatic calibration data selection
obj = lfp_calibrator.CaliFinder(cfg)
obj.main()
wht_img = obj.wht_bay
del obj

if cal_opt:
    # perform centroid calibration
    cal_obj = lfp_calibrator.LfpCalibrator(wht_img, cfg)
    cal_obj.main()
    cfg = cal_obj.cfg
    del cal_obj

# load calibration data
cfg.load_cal_data()

# de-rotate centroids
obj = LfpRotator(wht_img, cfg.calibs[cfg.mic_list], rad=None, cfg=cfg)
obj.main()
wht_rot, centroids_rot = obj.lfp_img, obj.centroids
del obj

plot_centroids(wht_img, centroids=cfg.calibs[cfg.mic_list], fn='_')
plot_centroids(wht_rot, centroids=centroids_rot, fn='_rota')
