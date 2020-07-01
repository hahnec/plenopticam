import sys
sys.path.append('/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages/libsvm')
from plenopticam import misc
import brisque


def brisque_metric(img_tile):

    brisq = brisque.BRISQUE()
    score = brisq.get_score(img_tile)

    return score

from scipy import fftpack
import numpy as np
import os

def blur_metric(img_tile):
    ''' img_tile : cropped image '''

    img = misc.rgb2gray(img_tile) if len(img_tile.shape) == 3 else img_tile
    y, x = img.shape

    magnitude = np.abs(fftpack.fft2(img))
    magnitudeCrop = magnitude[:int(np.ceil(y/2)), :int(np.ceil(x/2))]
    #figure, imshow(magnitude,[0 1000]), colormap gray # magnitude


    F2 = fftpack.fftshift(magnitude)
    psd2D = np.abs(F2) ** 2

    #plt.figure(1)
    #plt.imshow(psd2D/np.percentile(psd2D, 95))
    #plt.show()

    # total energy
    TE = sum(sum(magnitudeCrop**2))

    # high frequency energy
    freq_bounds = (int(np.ceil(y/500)), int(np.ceil(x/500)))
    HE = TE - sum(sum(magnitudeCrop[:freq_bounds[0], :freq_bounds[1]]**2))

    # energy ratio (Sharpness)
    S = HE/TE

    return S


def michelson_contrast(img_tile):
    ''' https://colorusage.arc.nasa.gov/luminance_cont.php '''

    lum_tile = misc.yuv_conv(img_tile)[..., 0]

    c_m = (lum_tile.max() - lum_tile.min()) / (lum_tile.max() + lum_tile.min())

    return c_m


def crop_imgs(folder, coords_lists):

    img_tiles, files = list(), list()
    exts = ('tif', 'tiff', 'png')

    misc.mkdir_p(os.path.join(folder, 'auto-crop'))
    folders = [f for f in os.listdir(folder) if f.endswith(exts)]
    folders.sort()

    for i, file in enumerate(folders):
        coords_nested = coords_lists[i]
        for j, coords in enumerate(coords_nested):
            if coords[0] != 0 and coords[1] != 0:
                cy, cx, h, w = coords
                img = misc.load_img_file(os.path.join(folder, file))
                tile = img[cy-h//2:cy+h//2, cx-w//2:cx+w//2, ...]
                img_tiles.append(tile)
                files.append(file)
                fn, ext = os.path.splitext(file)
                misc.save_img_file(tile, os.path.join(folder, 'auto-crop', fn+'_crop'+str(j)), 'png', tag=True)

    return img_tiles, files


if __name__ == "__main__":

    fp_lytro = '/Users/Admin/Unterlagen/PhD/07 publications/18_plenopticam/softwarex_pcam/img/refo_lytro'
    fp_ours = '/Users/Admin/Unterlagen/PhD/07 publications/18_plenopticam/softwarex_pcam/img/refo_upscale_7px_/'

    # bumblebee crop positions
    coords_lists_lytro = [
                          [[423, 255, 341, 511], [0, 0, 0, 0], [0, 0, 0, 0]],                             # far
                          [[1032, 1080, 242, 363], [465, 1500, 248, 372], [765, 1330, 262, 393]],         # middle
                          [[1260, 2190, 300, 450], [418, 2295, 220, 330], [930, 2310, 208, 312]]          # close
                         ]

    scale_comp_y = 2.3629130967*7/9
    scale_comp_x = 2.2812244898*7/9

    coords_lists_lytro = np.asarray(coords_lists_lytro, dtype='int')
    coords_lists_pcam = np.round(coords_lists_lytro*scale_comp_x).astype('int')

    coords_lists_pcam[0, 0, :2] += [158, 159]
    coords_lists_pcam[1, :, :2] += [120, -20]
    coords_lists_pcam[2, :, :2] += [40, -100]

    s_list = list()

    # loop over directories
    for set in [(fp_lytro, coords_lists_lytro), (fp_ours, coords_lists_pcam)]:

        fp, coords_lists = set

        img_tiles, slice_fns = crop_imgs(fp, coords_lists)

        # loop over filenames in directory
        for img_tile, slice_fn in zip(img_tiles, slice_fns):

            # leave out alpha channel if present
            img_tile = img_tile[..., :3]

            # rescale tile for fair comparison
            img_tile = misc.img_resize(img_tile, scale_comp_x, scale_comp_y) if fp.__contains__('refo_lytro') else img_tile

            img_tile = np.asarray(img_tile, dtype='uint16')

            # store results
            s_list.append((slice_fn, blur_metric(img_tile), michelson_contrast(img_tile), brisque_metric(img_tile)))

    for s in s_list:
        print(s)

    s_arr = np.asarray(s_list)
    np.save('refocus_metrics', s_list)
