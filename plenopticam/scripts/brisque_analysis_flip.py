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

    path = r'C:\Users\chahne\Pictures\Dataset_INRIA_SIROCCO'
    exts = ('png')
    target_folders = [
                        #'comparison\dans_colour_srgb',
                        #'comparison\clim_clr',
                        #'thumb_collection_menon_rgb-clip',
                        'thumb_collection_menon_gray-clip-less',
                        'thumb_collection_menon_gray-clip',
                        'thumb_collection_value-clip',
                        'thumb_collection_menon_rgb-clip'
                      ]
    skip_list = [
                 ]

    labels = ['LFToolbox v0.4', 'CLIM_V-SENSE', 'PlenoptiCam v1.0.0']
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

                img = load_img_file(os.path.join(fp, file))

                # extract image tile
                if crop_opt:
                    cy, cx = [x//2 for x in img.shape[:2]]
                    hh, hw = [x//10 for x in img.shape[:2]]
                    img_tile = img[cy-hh:cy+hh+1, cx-hw:cx+hw+1]
                else:
                    img_tile = img#[2:-2, 2:-2, ...]

                score = brisque_metric(Normalizer(img_tile).uint8_norm())
                scores.append(score)
                print(file+': %s' % scores[-1])

            #brisq.get_feature(os.path.join(fp, file))

        score_series.append(scores)

    # plot
    plt.style.use('seaborn-white')
    fig = plt.figure()
    softx__width = 5.39749
    a = softx__width*4   #4
    fig.set_size_inches(w=softx__width, h=a)
    width = .25

    for i, scores in enumerate(score_series):
        label = target_folder.split('_')[-1].replace('_', '-')
        index = [x + (i - len(target_folders) // 2) * width for x in list(range(len(scores)))]
        plt.barh(index, scores, width,
                 label=next(labelcycler))  # , linestyle=next(linecycler))#, marker=next(markercycler))

    # tick labels
    tick_labels = [os.path.splitext(file)[0] for file in files if os.path.splitext(file)[0].split('_')[0] not in skip_list]
    tick_labels = [label.split('_')[-1] if not label.startswith('Bee') else label for label in tick_labels]
    plt.yticks(range(len(tick_labels)), tick_labels, rotation='horizontal')

    # leave space for tick labels
    plt.subplots_adjust(left=0.25)

    # grids
    plt.grid(True, alpha=.5)

    # define axis limits
    plt.xlim(10*(np.min(score_series)//10), 10*(np.max(score_series)//10)+5)
    plt.ylim(-1, len(scores))

    # aspect ratio
    fig.axes[0].set_aspect(a / softx__width)

    #plt.gca().invert_xaxis()

    plt.xlabel('BRISQUE [Score]')
    plt.legend(frameon=True)

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
