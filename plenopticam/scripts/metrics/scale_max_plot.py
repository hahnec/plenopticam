import matplotlib.pyplot as plt
import numpy as np
import os
import zipfile

from plenopticam.misc import load_img_file
from plenopticam.lfp_calibrator import PitchEstimator

# Text rendering with LaTeX
from matplotlib import rc
rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})
rc('text', usetex=True)
import matplotlib as mpl
#mpl.rcParams['text.usetex'] = True
mpl.rcParams['text.latex.preamble'] = [r'\usepackage{amsmath}']

fig = plt.figure()
ax = fig.add_subplot(111)

linestyle = ['-', '--', '-.', ':', (0, (3, 5, 1, 5, 1, 5))]
min_len = 130

# file settings
CEA_PATH = os.path.join('..', '..', '..', 'examples', 'data', 'synth_spots')

# extract zip archive
with zipfile.ZipFile(CEA_PATH + '.zip', 'r') as zip_obj:
    zip_obj.extractall(CEA_PATH)

for i, fname in enumerate(['a', 'b', 'c', 'd']):

    img = load_img_file(os.path.join(CEA_PATH, fname+'.png'))
    obj = PitchEstimator(img=img)
    obj.main()
    maxima = np.asarray(obj.get_maxima())
    refined_max, nu = obj.interpolate_maxima(maxima)
    scale_arg, scale_max = np.argmax(refined_max)/10, np.max(refined_max)

    label = '('+fname+')' if len(fname) == 1 else 'Lytro Illum'
    ax.plot(nu, refined_max, linestyle=linestyle[i], label=label)
    ax.plot(scale_arg, scale_max, 'rx')

ax.set_aspect(3)
ax.set_xlabel(r'$\nu$')#[a.u.]
ax.set_ylabel(r'$\displaystyle\operatorname{max}\left(P(\nu, \mathbf{x})\right)$')#Norm. intensity \text{[a.u.]}
ax.legend(loc='upper right')
fig.savefig("scale_max_plot.pdf", bbox_inches="tight")
plt.show()
