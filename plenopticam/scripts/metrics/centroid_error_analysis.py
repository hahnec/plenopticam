from plenopticam.lfp_calibrator import *
from plenopticam.misc import PlenopticamStatus, load_img_file
from plenopticam.cfg import PlenopticamConfig, constants

import numpy as np
import matplotlib.pyplot as plt
from color_space_converter import rgb2gry
import os
import zipfile

# Text rendering with LaTeX
from matplotlib import rc
rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})
rc('text', usetex=True)
# for Palatino
# rc('font',**{'family':'serif','serif':['Palatino']})

# plenopticam objects
cfg = PlenopticamConfig()
sta = PlenopticamStatus()

# file settings
fname = 'd'
CEA_PATH = os.path.join('..', '..', '..', 'examples', 'data', 'synth_spots')

# extract zip archive
with zipfile.ZipFile(CEA_PATH + '.zip', 'r') as zip_obj:
    zip_obj.extractall(CEA_PATH)

# calibration settings
cfg.params[cfg.cal_path] = os.path.join(CEA_PATH, fname + '.png')
cfg.params[cfg.cal_meth] = constants.CALI_METH[2]
wht_img = load_img_file(cfg.params[cfg.cal_path])
crop = False
plt_idx = False

# load ground truth (remove outlying centers)
spots_grnd_trth = np.loadtxt(os.path.join(CEA_PATH, fname + '.txt'))
spots_grnd_trth = spots_grnd_trth[spots_grnd_trth[:, 1] > 0]
spots_grnd_trth = spots_grnd_trth[spots_grnd_trth[:, 0] > 0]
spots_grnd_trth = spots_grnd_trth[spots_grnd_trth[:, 1] < wht_img.shape[1]]
spots_grnd_trth = spots_grnd_trth[spots_grnd_trth[:, 0] < wht_img.shape[0]]

# ensure white image is monochromatic
if len(wht_img.shape) == 3:
    wht_img = rgb2gry(wht_img)[..., 0] if wht_img.shape[-1] == 3 else wht_img

# estimate micro image diameter
obj = PitchEstimator(wht_img, cfg, sta)
obj.main()
M = obj.M
del obj
print("Estimated pitch size: %s " % M)

# compute all centroids of micro images
obj = CentroidExtractor(wht_img, cfg, sta, M)
obj.main()
centroids = obj.centroids
peak_img = obj.peak_img
del obj

raw_centroids = np.array(centroids)

# refine centroids with sub-pixel precision using provided method
obj = CentroidRefiner(peak_img, centroids, cfg, sta, M)
obj.main()
centroids = obj.centroids_refined
del obj

ref_centroids = np.array(centroids)

# reorder MICs and assign indices based on the detected MLA pattern
obj = CentroidSorter(centroids, cfg, sta)
obj.main()
mic_list, pattern, pitch = obj.mic_list, obj.pattern, obj.pitch
del obj

srt_mics = np.array(mic_list)

# fit grid of MICs using least-squares method to obtain accurate MICs from line intersections
if cfg.params[cfg.cal_meth] == c.CALI_METH[2]:
    cfg.calibs[cfg.pat_type] = pattern
    obj = GridFitter(coords_list=mic_list, cfg=cfg, sta=sta, arr_shape=wht_img.shape)
    obj.main()
    mic_list = obj.grid_fit
    del obj

fit_mics = np.array(mic_list)

plt.figure()
plt.imshow(wht_img, cmap='gray', interpolation='nearest')
plt.plot(spots_grnd_trth[:, 1], spots_grnd_trth[:, 0], 'rx', label=r'Ground-truth $\mathring{\mathbf{c}}_{j,h}$')
plt.plot(raw_centroids[:, 1], raw_centroids[:, 0], '*', color='orange', label=r'\textsc{CentroidExtractor}')
plt.plot(ref_centroids[:, 1], ref_centroids[:, 0], 'b+', label=r'\textsc{CentroidRefiner}')
plt.plot(srt_mics[:, 1], srt_mics[:, 0], 'g.', label=r'\textsc{CentroidSorter}')
plt.plot(fit_mics[:, 1], fit_mics[:, 0], 'kx', label=r'\textsc{GridFitter}') if cfg.params[cfg.cal_meth] == c.CALI_METH[2] else None
plt.legend(loc='upper right')

# plot micro image indices
if plt_idx:
    str_list = list(zip(list(map(str, srt_mics[:, 2].astype('int'))), list(map(str, srt_mics[:, 3].astype('int')))))
    labels = ['('+s1+', '+s2+')' for s1, s2 in str_list]
    for x, y, s in zip(srt_mics[:, 1]-40, srt_mics[:, 0]-20, labels):
        plt.text(x, y, s=s, fontsize=13, color='black')

# remove all the ticks (both axes), and tick labels
plt.tick_params(top=False, bottom=False, left=False, right=False, labelleft=False, labelbottom=False)

# crop image
if crop:
    fac = 1.2
    y_u, y_b, x_l, x_r = [fac*wht_img.shape[0]//3, (3-fac)*wht_img.shape[0]//3,
                          fac*wht_img.shape[1]//3, (3-fac)*wht_img.shape[1]//3]
    plt.xlim(x_l, x_r)
    plt.ylim(y_b, y_u)

# save figure
plt.savefig(fname+".pdf", bbox_inches="tight")
plt.show()

# quantitative centroid error analysis
c_lists = [('CentroidExtractor', raw_centroids), ('CentroidRefiner', ref_centroids),
           ('CentroidSorter', srt_mics[:, :2]), ('GridFitter', fit_mics[:, :2])]
for name, c_list in c_lists:
    c_errs = list()
    grnd_trth = spots_grnd_trth.copy()
    # iterate through all centers
    for cn in c_list:
        # absolute pixel deviations from euclidean distance
        closest = [sum(x**2)**.5 for x in (grnd_trth-cn)] if len(grnd_trth) > 0 else [sum(cn**2)]
        # pick minimum deviation to identify matching center in unsorted set of ground-truths
        closest, idx = min(closest), np.argmin(closest)
        # remove picked ground-truth center from list
        np.delete(grnd_trth, idx, axis=0)
        # store deviation of center
        c_errs.append(closest)
    # print mean deviation of all centers
    print(name+': '+str(np.mean(np.asarray(c_errs))))
