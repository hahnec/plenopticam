import sys
sys.path.append('/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages/libsvm')
from plenopticam import misc
from color_space_converter import rgb2gry
import brisque
from scipy import fftpack
import numpy as np
import os


def brisque_metric(img_tile):

    brisq = brisque.BRISQUE()
    score = brisq.get_score(img_tile)

    return score


def blur_metric(img_tile):
    """ img_tile : cropped image """

    img = rgb2gry(img_tile)[..., 0] if len(img_tile.shape) == 3 else img_tile
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
    """ https://colorusage.arc.nasa.gov/luminance_cont.php """

    #lum_tile = misc.yuv_conv(img_tile)[..., 0]
    lum_tile = rgb2gry(img_tile)[..., 0]

    c_m = (lum_tile.max() - lum_tile.min()) / (lum_tile.max() + lum_tile.min())

    return c_m


def crop_imgs(folder, coords_lists):

    img_tiles, files = list(), list()
    slice_fns = list()
    exts = ('tif', 'tiff', 'png')

    misc.mkdir_p(os.path.join(folder, 'auto-crop'))
    files = [f for f in os.listdir(folder) if f.endswith(exts) and not f.startswith('.')]
    files.sort()

    for i, file in enumerate(files):
        coords_nested = coords_lists[i]
        for j, coords in enumerate(coords_nested):
            if coords[0] != 0 and coords[1] != 0:
                cy, cx, h, w = coords
                img = misc.load_img_file(os.path.join(folder, file))[..., :3]
                tile = img[int(cy-h/2):int(cy+h/2), int(cx-w/2):int(cx+w/2), ...]
                img_tiles.append(tile)
                fn, ext = os.path.splitext(file)
                misc.save_img_file(tile, os.path.join(folder, 'auto-crop', fn+'_crop'+str(j)), 'png', tag=True)
                slice_fns.append(file)

    return img_tiles, slice_fns


if __name__ == "__main__":

    fp_ours = '/Users/Admin/Unterlagen/PhD/07 publications/18_plenopticam/IEEEtran_1st-revision/img/refo_upscale_7px'
    fp_lytro = '/Users/Admin/Unterlagen/PhD/07 publications/18_plenopticam/IEEEtran_1st-revision/img/refo_lpt'
    fp_ours_native = '/Users/Admin/Unterlagen/PhD/07 publications/18_plenopticam/IEEEtran_1st-revision/img/refo_7px'

    lpts_y, lpts_x = np.array([1.1638176638, 1.2116716123])

    # bumblebee crop positions (cy, cx, h, w)
    coords_lists_lytro = [
                          [[423/lpts_y, 255/lpts_x, 341/lpts_y, 510/lpts_x], [0, 0, 0, 0], [0, 0, 0, 0]],                             # far
                          [[1032/lpts_y, 1080/lpts_x, 242/lpts_y, 363/lpts_x], [465/lpts_y, 1500/lpts_x, 248/lpts_y, 372/lpts_x], [765/lpts_y, 1330/lpts_x, 262/lpts_y, 393/lpts_x]],         # middle
                          [[1260/lpts_y, 2190/lpts_x, 300/lpts_y, 450/lpts_x], [418/lpts_y, 2295/lpts_x, 220/lpts_y, 330/lpts_x], [930/lpts_y, 2310/lpts_x, 208/lpts_y, 312/lpts_x]]          # close
                         ]

    coords_lists_lytro = np.round(np.array(coords_lists_lytro))#.astype('int')

    scale_comp_y = 2.3629130967*7/9*lpts_y
    scale_comp_x = 2.2812244898*7/9*lpts_x

    coords_lists_lytro = np.asarray(coords_lists_lytro, dtype='int')
    coords_lists_pcam = np.round(coords_lists_lytro*scale_comp_x).astype('int')

    coords_lists_pcam[0, 0, :2] += np.round(np.array([-5, 5])).astype('int')#[158, 159]
    coords_lists_pcam[1, :, :2] += np.round(np.array([-5, 5])).astype('int')
    coords_lists_pcam[2, :, :2] += np.round(np.array([-5, 5])).astype('int')

    coords_lists_native = np.round(coords_lists_pcam/7).astype('int')
    s_list = list()

    # iterate through directories
    for set in [(fp_lytro, coords_lists_lytro), (fp_ours, coords_lists_pcam), (fp_ours_native, coords_lists_native)]:

        fp, coords_lists = set

        img_tiles, slice_fns = crop_imgs(fp, coords_lists)
        i = 0
        # iterate through file names in directory
        for img_tile, slice_fn in zip(img_tiles, slice_fns):

            # leave out alpha channel if present
            img_tile = img_tile[..., :3]

            # rescale tile for fair comparison
            if fp.__contains__('refo_lytro') or fp.__contains__('refo_lpt'):
                img_tile = misc.img_resize(img_tile, scale_comp_x, scale_comp_y)
            elif not fp.__contains__('upscale'):
                img_tile = misc.img_resize(img_tile, 7)

            # normalize intensities
            img_tile = misc.Normalizer(img_tile).uint8_norm()

            # store results
            s_list.append((slice_fn, blur_metric(img_tile), michelson_contrast(img_tile), brisque_metric(img_tile), img_tile.shape))

    for s in s_list:
        print(s)

    s_arr = np.asarray(s_list)
    np.save('refo_metrics', s_list)
