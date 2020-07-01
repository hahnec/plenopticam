from plenopticam.lfp_calibrator import *
from plenopticam.misc import PlenopticamStatus, load_img_file
from plenopticam.cfg import PlenopticamConfig, constants

import numpy as np
import matplotlib.pyplot as plt
from color_space_converter import rgb2gry

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
fname = './b'
cfg.params[cfg.cal_path] = fname + '.png'
cfg.params[cfg.cal_meth] = constants.CALI_METH[2]   #'peak'   #
wht_img = load_img_file(cfg.params[cfg.cal_path])
crop = True

# load ground truth (remove outlying centers)
spots_grnd_trth = np.loadtxt(fname + '.txt')
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
obj = CentroidRefiner(peak_img, centroids, cfg, sta, M, cfg.params[cfg.cal_meth])
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
    obj = GridFitter(coords_list=mic_list, cfg=cfg, sta=sta)
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
#plt.savefig(fname+".pgf", bbox_inches="tight")
plt.show()

# quantitative centroid error analysis
c_lists = [('CentroidExtractor', raw_centroids), ('CentroidRefiner', ref_centroids),
           ('CentroidSorter', srt_mics[:, :2]), ('GridFitter', fit_mics[:, :2])]
for name, c_list in c_lists:
    c_errs = list()
    grnd_candidates = list(spots_grnd_trth)
    for cn in c_list:
        closest = [sum(x) for x in (np.array(grnd_candidates) - cn)**2] if len(grnd_candidates) > 0 else [sum(cn**2)]
        closest, idx = min(closest), np.argmin(closest)
        c_errs.append(np.sqrt(closest))
        #grnd_candidates.pop(idx) if len(grnd_candidates) > 0 else None
    print(name+': '+str(np.mean(np.asarray(c_errs))))
