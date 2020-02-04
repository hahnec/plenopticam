try:
    import sys
    sys.path.append('/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages/libsvm')
except:
    pass

import brisque
import os
from itertools import cycle
import matplotlib.pyplot as plt
import numpy as np

from plenopticam.misc import load_img_file, Normalizer

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


if __name__ == "__main__":

    target_folders = [
                       # 'checker'
                       'comparison\dans_colour_srgb',
                       'comparison\clim_clr',
                       #'comparison\clim_wo_gam',
                       #'comparison\clim_bar',
                       #'thumb_collection_bilinear',
                       #'thumb_collection_menon',
                       #'thumb_collection_indi-ccm',
                       #'thumb_collection_malvar_clip_srgb',
                       #'thumb_collection_malvar_ccm-indi',
                       #'thumb_collection_menon_gray-clip-less',
                       #'thumb_collection_value-clip',
                       #'thumb_collection_value-clip-hex',
                       'thumb_collection_menon_rgb-clip',
                       #'thumb_collection_menon_rgb-clip-more'
                      ]
    path = r'C:\Users\chahne\Pictures\Dataset_INRIA_SIROCCO'
    exts = ('png')
    skip_list = []#'Checkerboard', 'Framed'

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

                img = load_img_file(os.path.join(fp, file))

                # extract image tile
                if crop_opt:
                    cy, cx = [x//2 for x in img.shape[:2]]
                    hh, hw = [x//10 for x in img.shape[:2]]
                    img_tile = img[cy-hh:cy+hh+1, cx-hw:cx+hw+1]
                else:
                    img_tile = img#[2:-2, 2:-2, ...]

                #img_tile /= img_tile.max()
                #gain = 10
                #cutoff = 0.5
                #img_tile = 1./(1+np.exp(gain*(cutoff-misc.Normalizer(img_tile).type_norm())))
                score = brisque_metric(Normalizer(img_tile).uint8_norm())
                scores.append(score)
                print(file+': %s' % scores[-1])

            #brisq.get_feature(os.path.join(fp, file))

        score_series.append(scores)

    # plot
    plt.style.use('seaborn-white')
    fig = plt.figure()
    a = 4
    softx__width = 5.39749
    fig.set_size_inches(w=softx__width, h=a)
    width = .2

    labels = ['LFToolbox v0.4', 'CLIM V-SENSE', 'PlenoptiCam v1.0.0']
    labelcycler = cycle(labels)
    labelcycler = cycle(target_folders)

    lines = ["-", "--", "-.", ":"]
    linecycler = cycle(lines)

    markers = ["x", ".", "+", "^", "s", "d"]
    markercycler = cycle(markers)

    for i, scores in enumerate(score_series):
        x_range = [x + (i - len(target_folders) // 2) * width for x in list(range(len(scores)))]  # range(len(scores))#
        plt.bar(x_range, scores, width,
                label=next(labelcycler), linestyle=next(linecycler))  # , marker=next(markercycler))

    # tick labels
    tick_labels = [os.path.splitext(file)[0] for file in files if os.path.splitext(file)[0].split('_')[0] not in skip_list]
    tick_labels = [label.split('_')[-1] if not label.startswith('Bee') else label for label in tick_labels]
    plt.xticks(range(len(tick_labels)), tick_labels, rotation='vertical')

    # leave space for tick labels
    plt.subplots_adjust(bottom=0.25)

    # grids
    plt.grid(True, alpha=.5)

    plt.ylabel('BRISQUE [Score]')
    plt.legend(frameon=True)

    # define axis limits
    plt.ylim(10*(np.min(score_series)//10), 10*(np.max(score_series)//10)+5)
    plt.xlim(-1, len(scores))

    # score assessment
    try:
        series = np.array(score_series)
        cnts = [np.sum(np.argmin(np.swapaxes(series, axis1=0, axis2=1), axis=1) == i) for i in range(len(series))]
        print(cnts)
        print([i.sum() for i in series])
    except:
        pass

    plt.show()
    plt.savefig("brisque_central.pgf")
