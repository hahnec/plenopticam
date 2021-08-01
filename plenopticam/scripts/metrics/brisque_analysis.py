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
import platform

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
                       #'checker'
                       'comparison/dans_colour_srgb',
                       'comparison/clim_clr',
                       #'comparison/clim_wo_gam',
                       #'comparison/clim_bar',
                       'thumb_collection_paper'
                      ]

    if platform.system() == 'Windows':
        path = r'C:\Users\chahne\Pictures\Dataset_INRIA_SIROCCO'
    elif platform.system() == 'Darwin':
        path = r'/Users/Admin/Pictures/Plenoptic/'
    else:
        path = os.getcwd()

    exts = ('png', 'tiff')
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
                    img = img[2:-2, 2:-2, ...] if file.endswith('Thumb.png') else img
                    cy, cx = [x//2 for x in img.shape[:2]]
                    hh, hw = [x//10 for x in img.shape[:2]]
                    img_tile = img[cy-hh:cy+hh+1, cx-hw:cx+hw+1]
                elif target_folder.__contains__('dans_colour_srgb') or target_folder.__contains__('clim_clr'):
                    # crop edges to remove zigzag pattern
                    img_tile = img[2:-2, 2:-2, ...]
                else:
                    img_tile = img

                score = brisque_metric(Normalizer(img_tile).uint8_norm())
                scores.append(score)
                print(file+': %s' % scores[-1])

            #brisq.get_feature(os.path.join(fp, file))

        score_series.append(scores)

    # plot
    plt.style.use('seaborn-white')
    fig = plt.figure()
    a = 3 #4
    softx_width = 5.39749
    ieee_width = 7.14113
    fig.set_size_inches(w=ieee_width, h=a)
    width = .2

    labels = ['LFToolbox v0.5', 'CLIM-VSENSE', 'PlenoptiCam v1.0']
    labelcycler = cycle(labels)
    #labelcycler = cycle(target_folders)

    lines = ["-", "--", "-.", ":"]
    linecycler = cycle(lines)

    markers = ["x", ".", "+", "^", "s", "d"]
    markercycler = cycle(markers)

    hatches = ['/', '.', '+']
    hatchcycler = cycle(hatches)

    for i, scores in enumerate(score_series):
        x_range = [x + (i - len(target_folders) // 2) * width for x in list(range(len(scores)))]  # range(len(scores))#
        plt.bar(x_range, scores, width, #edgecolor='black',
                label=next(labelcycler), hatch=next(hatchcycler))  # , marker=next(markercycler)) linestyle=next(linecycler),

    # tick labels
    tick_labels = [os.path.splitext(file)[0] for file in files if os.path.splitext(file)[0].split('_')[0] not in skip_list]
    tick_labels = [label.split('_')[-1] if not label.startswith('Bee') else label for label in tick_labels]
    plt.xticks(range(len(tick_labels)), tick_labels, rotation=90, ha='center')

    # leave space for tick labels
    plt.subplots_adjust(bottom=0.33)

    # grids
    plt.grid(True, alpha=.35)

    plt.ylabel('BRISQUE [Score]')
    plt.gca().yaxis.set_label_coords(x=-.07, y=.5)
    plt.legend(frameon=True, loc='upper left', bbox_to_anchor=(0.033, 1.01))

    plt.tick_params(axis="x", direction="out", length=4)
    plt.tick_params(axis="y", direction="out", length=4)

    # define axis limits
    if np.asarray(score_series).dtype != 'O':
        plt.ylim(10*(np.min(score_series)//10), 10*np.ceil(np.max(score_series)/10))
        x_range = [x+-.5*width for x in range(len(scores))]
        plt.xlim(x_range[0]-3*width, x_range[-1]+4*width)

    # score assessment
    try:
        series = np.asarray(score_series)
        cnts = [np.sum(np.argmin(np.swapaxes(series, axis1=0, axis2=1), axis=1) == i) for i in range(len(series))]
        print(cnts)
        print([i.sum() for i in series])
    except:
        pass

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.35)
    plt.savefig("brisque_central.pdf")
    plt.show()
