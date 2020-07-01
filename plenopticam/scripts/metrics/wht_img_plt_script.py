
# local imports
from plenopticam import lfp_calibrator
from plenopticam.cfg import PlenopticamConfig
from plenopticam import lfp_reader
from plenopticam.lfp_aligner import LfpRotator
from plenopticam.lfp_aligner.cfa_processor import CfaProcessor
from color_space_converter import rgb2gry

try:
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    from matplotlib.patches import ConnectionPatch
    import matplotlib.patheffects as mpe
    import matplotlib.patheffects as path_effects
except ImportError:
    raise ImportError("Package matplotlib wasn't found.")

import numpy as np

# Text rendering with LaTeX
from matplotlib import rc
#rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})
rc('text', usetex=True)
# for Palatino
rc('font', **{'family': 'serif', 'serif': ['Palatino']})


def plot_centroids(img, centroids, fn, marker_color):

    centroids = np.asarray(centroids)
    img = (img-img.min())/(img.max()-img.min())

    plt.style.use("ggplot")

    s = 2
    h, w, c = img.shape if len(img.shape) == 3 else img.shape + (1,)
    hp, wp = 100, 100
    fig, axs = plt.subplots(1, s, facecolor='w', edgecolor='k', sharex='all')#, figsize=(15, 6), )

    xy = list()
    xy.append(centroids[(centroids[:, 2] == max(centroids[:, 2])//2) & (centroids[:, 3] == 0)])
    xy.append(centroids[(centroids[:, 2] == max(centroids[:, 2])//2) & (centroids[:, 3] == max(centroids[:, 3]))])

    for i in range(s):

        # plot cropped image part
        k = h//2 - hp//2 #i * (h//s) + (h//s)//2 - hp//2
        l = i*w - i*wp #j * (w//s) + (w//s)//2 - wp//2
        axs[i].imshow(img[k:k+hp, l:l+wp, ...], cmap='gray')

        # plot cropped centroids
        conditions = (centroids[:, 1] >= l) & (centroids[:, 1] <= l+wp-.5) & \
                     (centroids[:, 0] >= k) & (centroids[:, 0] <= k+hp-.5)
        x_centroids = centroids[:, 1][conditions]
        y_centroids = centroids[:, 0][conditions]
        axs[i].plot(x_centroids-l, y_centroids-k, 'bx')
        axs[i].grid(False)

        axs[i].tick_params(top=False, bottom=False, left=False, right=False,
                           labelleft=False, labelbottom=False)

        xy[i] = xy[i][0][:2]-np.array([k, l])

    con = ConnectionPatch(xyA=xy[0][::-1], xyB=xy[1][::-1], coordsA="data", coordsB="data",
                          axesA=axs[0], axesB=axs[1], linewidth=4, alpha=0.3)
    outline = mpe.Stroke(linewidth=12, foreground=marker_color)
    con.set_path_effects([outline])
    axs[1].add_artist(con)

    axs[0].plot(xy[0][1], xy[0][0], marker='o', color=marker_color, markersize=10, alpha=0.4)
    axs[1].plot(xy[1][1], xy[1][0], marker='o', color=marker_color, markersize=10, alpha=0.4)

    # set common labels
    fig.text(0.5, 0.2, 'Horizontal dimension [px]', ha='center', va='center', fontsize=14)
    fig.text(0.06, 0.5, 'Vertical dimension [px]', ha='center', va='center', rotation='vertical', fontsize=14)

    #import tikzplotlib
    #tikzplotlib.save('input+mics' + fn + '.tex')
    plt.savefig('input+mics'+fn+'.pdf', bbox_inches='tight', format='pdf')

    plt.show()

    return True


if __name__ == "__main__":

    # create config object
    cfg = PlenopticamConfig()
    #cfg.default_values()
    #cfg.reset_values()

    cfg.params[cfg.cal_path] = r"/Users/Admin/Pictures/Plenoptic/CalibFolder/caldata-B5144000580.tar"
    cfg.params[cfg.lfp_path] = r"/Users/Admin/Pictures/Plenoptic/INRIA_SIROCCO/Building.LFR"
    #cfg.params[cfg.cal_path] = r"../../../../test/data/caldata-B5144402350.tar"
    #cfg.params[cfg.lfp_path] = r"../../../../test/data/gradient_rose_far.lfr"
    cfg.lfpimg['bay'] = "GRBG"
    cfg.params[cfg.opt_cali] = True
    cfg.params[cfg.opt_rota] = True
    cfg.params[cfg.opt_dbug] = False
    cfg.params[cfg.cal_meth] = 'grid-fit'

    cal_opt = False

    if cal_opt:
        # decode light field image
        lfp_obj = lfp_reader.LfpReader(cfg)
        lfp_obj.main()
        lfp_img = lfp_obj.lfp_img[:, :-16]
        del lfp_obj

    # automatic calibration data selection
    obj = lfp_calibrator.CaliFinder(cfg)
    obj.main()
    wht_img = obj.wht_bay[:, :-16]
    del obj

    if cal_opt:
        # perform centroid calibration
        cal_obj = lfp_calibrator.LfpCalibrator(wht_img, cfg)
        cal_obj.main()
        cfg = cal_obj.cfg
        del cal_obj
    else:
        # convert Bayer to RGB representation
        if len(wht_img.shape) == 2 and 'bay' in cfg.lfpimg:
            # perform color filter array management and obtain rgb image
            cfa_obj = CfaProcessor(bay_img=wht_img, cfg=cfg)
            cfa_obj.bay2rgb()
            wht_img = cfa_obj.rgb_img
            del cfa_obj

    # ensure white image is monochromatic
    wht_img = rgb2gry(wht_img)[..., 0] if len(wht_img.shape) is 3 else wht_img

    # load calibration data
    cfg.load_cal_data()

    if cfg.params[cfg.opt_rota]:
        # de-rotate centroids
        obj = LfpRotator(wht_img, cfg.calibs[cfg.mic_list], rad=None, cfg=cfg)
        obj.main()
        wht_rot, centroids_rot = obj.lfp_img, obj.centroids
        del obj

    plot_centroids(wht_img, centroids=cfg.calibs[cfg.mic_list], fn='_', marker_color='red')
    plot_centroids(wht_rot, centroids=centroids_rot, fn='_rota', marker_color='green')
