
import brisque
import os
from itertools import cycle
import matplotlib.pyplot as plt
import numpy as np

from plenopticam.misc import load_img_file

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


def brisque_metric(img_tile):

    brisq = brisque.BRISQUE()
    score = brisq.get_score(img_tile)

    return score


def psnr(img1=None, img2=None, quant_steps=2**8-1):

    img1 = np.asarray(img1, dtype=np.float64)/img1.max()
    img2 = np.asarray(img2, dtype=np.float64)/img2.max()

    mse = np.mean((img1-img2)**2)
    if mse == 0:
        return 100
    return 20*np.log10(quant_steps/np.sqrt(mse))


def hist_dist(img1, img2):

    hist_a, hist_b = hist_conv(img1, img2)
    res = np.sqrt(np.sum(np.square(hist_a-hist_b)))
    #res = np.mean(np.abs(hist_a-hist_b))
    #res = chi2_dist(hist_a, hist_b)

    return res


def hist_conv(img1, img2, bins=2**8-1):

    hist_a = np.histogram(img1, bins)[0]
    hist_b = np.histogram(img2, bins)[0]

    return hist_a, hist_b

def chi2_dist(hist_a, hist_b, eps=1e-10):

    return .5*np.sum([((a-b)**2)/(a+b+eps) for (a, b) in zip(hist_a, hist_b)])


if __name__ == "__main__":

    plt.style.use('seaborn-white')

    fig = plt.figure()
    a = 4
    softx__width = 5.39749
    fig.set_size_inches(w=softx__width, h=a)

    target_folders = [
                       'comparison\dans_colour_srgb',
                       'comparison\clim_clr',
                       'thumb_collection_gam09-bidg+illgam_mic'
                      ]
    path = r'C:\Users\chahne\Pictures\Dataset_INRIA_SIROCCO'
    exts = ('png')
    skip_list = []  #["Checkerboard, Framed"]

    labels = ['LFToolbox v0.4', 'CLIM V-SENSE', 'PlenoptiCam v1.0.0']
    labelcycler = cycle(labels)
    labelcycler = cycle(target_folders)

    lines = ["-", "--", "-.", ":"]
    linecycler = cycle(lines)

    markers = ["x", ".", "+", "^", "s", "d"]
    markercycler = cycle(markers)

    crop_opt = False

    score_series = list()
    for i, target_folder in enumerate(target_folders):
        fp = os.path.join(path, target_folder)

        files = [f for f in os.listdir(fp) if f.endswith(exts)]
        files.sort()

        scores = list()
        for file in files:

            # skip file if missing
            if os.path.splitext(file)[0].split('_')[0] not in skip_list:

                img_ref = load_img_file(os.path.join(fp, file))
                if target_folder.startswith('thumb_collection'):
                    img_src = load_img_file(os.path.join(fp, 'other_views', os.path.splitext(file)[0]+'_2_7'+'.png'))
                else:
                    img_src = load_img_file(os.path.join(fp, 'other_views', file.split('__')[0]+'28__'+file.split('__')[1]))

                score = hist_dist(img_ref, img_src)
                scores.append(score)
                print(file+': %s' % scores[-1])

        label = target_folder.split('_')[-1].replace('_', '-')
        #label = target_folder.split('_')[0]
        plt.plot(range(len(scores)), scores, linewidth=1,
                 label=next(labelcycler), linestyle=next(linecycler), marker=next(markercycler))

        score_series.append(scores)

    # tick labels
    tick_labels = [os.path.splitext(file)[0] for file in files if os.path.splitext(file)[0].split('_')[0] not in skip_list]
    tick_labels = [label.split('_')[-1] if not label.startswith('Bee') else label for label in tick_labels]
    plt.xticks(range(len(tick_labels)), tick_labels, rotation='vertical')

    # leave space for tick labels
    plt.subplots_adjust(bottom=0.25)

    # grids
    plt.grid(True, alpha=.5)

    plt.ylim(0, np.asarray(score_series)[1].mean())
    plt.ylabel('Histogram distance $D$ [a.u.]')
    plt.legend(frameon=True)

    plt.show()
    plt.savefig("hist_dist.pgf")

    # score assessment
    series = np.array(score_series)
    cnts = np.sum(np.argmin(np.swapaxes(series, axis1=0, axis2=1), axis=1) == series.shape[0]-1)
    print(cnts)
