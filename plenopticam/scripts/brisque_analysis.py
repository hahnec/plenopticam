try:
    import sys
    sys.path.append('/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages/libsvm')
except:
    pass

import brisque
import os
from itertools import cycle
import matplotlib.pyplot as plt

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


if __name__ == "__main__":

    plt.style.use('seaborn-white')

    fig = plt.figure()
    a = 4
    softx__width = 5.39749
    fig.set_size_inches(w=softx__width, h=a)

    path = r'C:\Users\chahne\Pictures\Dataset_INRIA_SIROCCO'
    exts = ('png')
    target_folders = [
                      'checker',
                      ]
    skip_list = ["Checkerboard", "Framed"]

    labels = ['LFToolbox v0.4', 'PlenoptiCam v0.2.5']
    labelcycler = cycle(labels)
    labelcycler = cycle(target_folders)

    lines = ["-", "--", "-.", ":"]
    linecycler = cycle(lines)

    markers = [".", "+", "^", "s", "d", "x"]
    markercycler = cycle(markers)

    crop_opt = False

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
                    img_tile = img[2:-2, 2:-2, ...]

                score = brisque_metric(img_tile)
                scores.append(score)
                print(file+': %s' % scores[-1])

            #brisq.get_feature(os.path.join(fp, file))

        label = target_folder.split('_')[-1].replace('_', '-')
        plt.plot(range(len(scores)), scores, linewidth=1,
                 label=next(labelcycler), linestyle=next(linecycler), marker=next(markercycler))

    # tick labels
    tick_labels = [os.path.splitext(file)[0] for file in files if os.path.splitext(file)[0].split('_')[0] not in skip_list]
    tick_labels = [label.split('_')[-1] if not label.startswith('Bee') else label for label in tick_labels]
    plt.xticks(range(len(tick_labels)), tick_labels, rotation='vertical')

    # leave space for tick labels
    plt.subplots_adjust(bottom=0.25)

    # grids
    plt.grid(True, alpha=.5)

    plt.ylabel('BRISQUE [Score]')
    plt.legend()

    plt.show()
    plt.savefig("brisque_central.pgf")
