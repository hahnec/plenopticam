import matplotlib.pyplot as plt
import numpy as np

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

for i, fname in enumerate(['a', 'b', 'c', 'd']):    #, 'lytro'
    data = np.loadtxt(fname+'_nu.txt')
    val_max, arg_max, rel_max, arg_rel_max = np.loadtxt(fname+'_extrema.txt')
    scale_arg, scale_max = (arg_max, val_max) if val_max / arg_max > rel_max / arg_rel_max else (arg_rel_max, rel_max)
    data_x = np.arange(len(data))
    #data_x = 2**(data//2) * np.sqrt(2**np.mod(data_x, 2)) * 1.18

    label = '('+fname+')' if len(fname) == 1 else 'Lytro Illum'
    ax.plot(data_x/10, data, linestyle=linestyle[i], label=label)
    ax.plot(scale_arg, scale_max, 'rx')

ax.set_aspect(3)
ax.set_xlabel(r'$\nu$')#[a.u.]
ax.set_ylabel(r'$\displaystyle\operatorname{max}\left(P(\nu, \mathbf{x})\right)$')#Norm. intensity \text{[a.u.]}
ax.legend(loc='upper right')
fig.savefig("scale_max_plot.pdf", bbox_inches="tight")
plt.show()
