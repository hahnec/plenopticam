import os
from itertools import cycle
import matplotlib.pyplot as plt
import numpy as np
import platform
import imageio
from scipy.stats import wasserstein_distance


pgf = False
if pgf:
    import matplotlib
    matplotlib.use("pgf")
    matplotlib.rcParams.update({
        "pgf.texsystem": "pdflatex",
        'font.family': 'serif',
        'text.usetex': True,
        'pgf.rcfonts': False,
    })
else:
    os.environ["PATH"] += os.pathsep + '/usr/local/texlive/2015/bin/x86_64-darwin'
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')


def psnr(img1=None, img2=None, quant_steps=2**8-1):

    img1 = np.asarray(img1, dtype=np.float64)/img1.max()
    img2 = np.asarray(img2, dtype=np.float64)/img2.max()

    mse = np.mean((img1-img2)**2)
    if mse == 0:
        return 100
    return 20*np.log10(quant_steps/np.sqrt(mse))


def hist_dist(img1, img2):

    hist_a, hist_b = hist_conv(img1, img2)
    #hist_a = hist_a.astype('float64') / np.sum(hist_a)
    #hist_b = hist_b.astype('float64') / np.sum(hist_b)
    res = np.sqrt(np.sum(np.square(hist_a-hist_b)))
    #res = np.sqrt(np.sum(np.square(hist_a-hist_b)))
    #res = np.mean(np.abs(hist_a-hist_b))
    #res = chi2_dist(hist_a, hist_b)

    return res


def hist_conv(img1, img2, bins=2**8-1):

    hist_a = np.histogram(img1, bins)[0]
    hist_b = np.histogram(img2, bins)[0]

    return hist_a, hist_b


def chi2_dist(hist_a, hist_b, eps=1e-10):

    return .5*np.sum([((a-b)**2)/(a+b+eps) for (a, b) in zip(hist_a, hist_b)])


def stat_vars(src, ref):

    # reshape source and reference images
    r, z = src.reshape([-1, src.shape[2]]).T, ref.reshape([-1, ref.shape[2]]).T

    # compute covariance matrices
    cov_r, cov_z = np.cov(r), np.cov(z)

    # compute color channel means
    mu_r, mu_z = r.mean(axis=1)[..., np.newaxis], z.mean(axis=1)[..., np.newaxis]

    return mu_r, mu_z, cov_r, cov_z


def w2_dist(mu_a: np.ndarray, mu_b: np.ndarray, cov_a: np.ndarray, cov_b: np.ndarray) -> float:
    """
    Wasserstein-2 distance metric is a similarity measure for Gaussian distributions

    :param mu_a: Gaussian mean of distribution *a*
    :param mu_b: Gaussian mean of distribution *b*
    :param cov_a: Covariance matrix of distribution *a*
    :param cov_b: Covariance matrix of distribution *b*

    :type mu_a: :class:`~numpy:numpy.ndarray`
    :type mu_b: :class:`~numpy:numpy.ndarray`
    :type cov_a: :class:`~numpy:numpy.ndarray`
    :type cov_b: :class:`~numpy:numpy.ndarray`

    :return: **scalar**: Wasserstein-2 metric as a scalar
    :rtype: float
    """

    mean_dist = np.sum((mu_a-mu_b)**2)
    vars_dist = np.trace(cov_a+cov_b-2*(np.dot(np.abs(cov_b)**.5, np.dot(np.abs(cov_a), np.abs(cov_b)**.5))**.5))

    return float(mean_dist + vars_dist)


def w2_metric(src, ref):

     mu_r, mu_z, cov_r, cov_z = stat_vars(src, ref)
     w2_val = w2_dist(mu_r, mu_z, cov_r, cov_z)

     return w2_val


if __name__ == "__main__":

    plt.style.use('seaborn-white')

    fig = plt.figure()
    a = 3.6 #4
    softx_width = 5.39749
    ieee_width = 7.14113
    fig.set_size_inches(w=ieee_width, h=a)

    target_folders = [
                       'comparison/dans_colour_srgb',
                       'comparison/clim_clr',
                       'comparison/pcam/hm',
                       'comparison/pcam/mkl',
                       'comparison/pcam/POT',
                       'comparison/pcam/mvgd',
                       'comparison/pcam/hm-mkl-hm',
                       'comparison/pcam/hm-mvgd-hm',
                      ]

    width = .75/len(target_folders)

    if platform.system() == 'Windows':
        path = r'C:\Users\chahne\Pictures\Dataset_INRIA_SIROCCO'
    elif platform.system() == 'Darwin':
        path = r'/Users/Admin/Pictures/Plenoptic/'
    else:
        path = os.getcwd()

    exts = ('png')

    labels = [
                'LFToolbox v0.5',
                'CLIM-VSENSE',
                'HM',
                'MKL by Pitié [19]',
                'POT toolbox [20]',
                'Our MVGD by Eq. (34)',
                'Our HM-MKL-HM',
                'Our HM-MVGD-HM',
            ]
    labelcycler = cycle(labels)
    #labelcycler = cycle(target_folders)

    lines = ["solid", "dotted", (0, (1, 10)), "dashed", (0, (5, 5)), "dashdot", (0, (3, 10, 1, 10, 1, 10)), (0, (3, 10, 1, 10, 1, 10))]
    linecycler = cycle(lines)

    markers = ["x", ".", "*", "+", "o", "s", "d", "O"]
    markercycler = cycle(markers)

    hatches = ['\\', '.', '*', '-', 'o', 'O', '/', '\\/...']  #'x', '|'

    crop_opt = False
    #ax1 = plt.gca()
    #ax2 = ax1.twinx()

    import matplotlib.gridspec as gridspec
    gs = gridspec.GridSpec(2, 1)
    gs.update(hspace=0.05)

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    score_series = list()
    w2_score_series = list()
    for i, target_folder in enumerate(target_folders):
        fp = os.path.join(path, target_folder)

        files = [f for f in os.listdir(fp) if f.endswith(exts)]
        files.sort()
        files = files[:len(files)//3]#[0::3]

        scores = list()
        w2_scores = list()
        for file in files:

            if target_folder.__contains__('pcam'):
                img_ref = imageio.imread(os.path.join(os.path.dirname(fp), 'central_views', file))
                img_src = imageio.imread(os.path.join(fp, file))
            else:
                img_ref = imageio.imread(os.path.join(fp, file))
                img_src = imageio.imread(os.path.join(fp, 'other_views', file.split('__')[0]+'28__'+file.split('__')[1]))

            score = hist_dist(img_ref, img_src)
            w2_score = wasserstein_distance(img_src[..., 1].flatten(), img_ref[..., 1].flatten())
            #w2_score = w2_metric(img_src, img_ref)
            scores.append(score)
            w2_scores.append(w2_score)
            print(file+': %s' % scores[-1])

        label = target_folder.split('_')[-1].replace('_', '-')
        x_range = [x+(i-len(target_folders)//2) * width for x in range(len(scores))]
        ax1.bar(x_range, w2_scores, width, hatch=hatches[i], label=next(labelcycler))#, labels=next(labelcycler), alpha=.3baseline='wiggle',
        ax2.bar(x_range, scores, width, hatch=hatches[i])    #, marker=next(markercycler)) #, linestyle=next(linecycler)

        score_series.append(scores)
        w2_score_series.append(w2_scores)

    # tick labels
    tick_labels = [os.path.splitext(file)[0] for file in files]
    tick_labels = [label.split('_')[-1] if not label.startswith('Bee') else label.replace('_', '\_') for label in tick_labels]
    ax2.set_xticks(range(len(tick_labels)))
    ax2.set_xticklabels(tick_labels, rotation=40, ha='right')

    ax1.tick_params(bottom=True)
    ax2.tick_params(bottom=True)
    plt.setp(ax1.get_xticklabels(), visible=False)

    # leave space for tick labels
    fig.subplots_adjust(bottom=0.2)

    scnd_max = np.partition(np.asarray(score_series).flatten(), -2)[-2]
    mean = np.mean(np.asarray(score_series))
    w2mean = np.mean(np.asarray(w2_score_series))
    ax1.set_ylim(0, w2mean)
    ax2.set_ylim(0, mean)
    ax1.set_xlim(x_range[0]-10*width, x_range[-1]+3*width)
    ax1.set_ylabel('$W_1$ [a.u.]')
    ax2.set_ylabel('$D_2$ [a.u.]')
    ax1.yaxis.set_label_coords(x=-.085, y=.5)
    ax2.yaxis.set_label_coords(x=-.085, y=.5)
    ax1.legend(frameon=False, loc='lower left', bbox_to_anchor=(-0.15, 1.01), ncol=len(target_folders)//2, borderaxespad=0)

    for ax, ax_range in zip([ax1, ax2], [[0, 2, 4], [0, 10000, 20000]]):
        ax_yticklabels = []
        ax_yticks = []
        for txt_obj in ax.get_yticklabels():
            if txt_obj.get_position()[1] < 0:
                ax_yticklabels.append('')
                txt_obj.set_text('')
            else:
                ax_yticklabels.append(txt_obj.get_text())
            ax_yticks.append(txt_obj.get_position()[1])
            txt_obj.set_visible(True)
        print(ax_yticks, ax_yticklabels)
        ax.set_yticks(ax_range)
        ax.set_yticklabels([str(x) if x < 10 else "{:0=1.0f}e4".format(x/1e4) for x in ax_range])

    if False:
        from matplotlib import ticker
        formatter = ticker.ScalarFormatter(useMathText=True)
        formatter.set_scientific(True)
        formatter.set_powerlimits((-1, 1))
        ax2.yaxis.set_major_formatter(formatter)

    ax1.grid(True, alpha=.5)
    ax2.grid(True, alpha=.5)
    ax1.axhline(0, color='k', linewidth=1)

    ax1.tick_params(axis="x", direction="out", length=4)
    ax1.tick_params(axis="y", direction="out", length=4)
    ax2.tick_params(axis="x", direction="out", length=4)
    ax2.tick_params(axis="y", direction="out", length=4)

    #fig.tight_layout()
    #plt.savefig("hist+wasser_dist.pgf")
    plt.savefig("hist+wasser_dist.png", dpi=300)
    plt.savefig("hist+wasser_dist.pdf")
    plt.savefig("hist+wasser_dist.svg")
    plt.show()

    # score assessment
    series = np.array(score_series)
    cnts = np.sum(np.argmin(np.swapaxes(series, axis1=0, axis2=1), axis=1) == series.shape[0]-1)
    print(cnts)
