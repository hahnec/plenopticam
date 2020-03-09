from plenopticam.misc import rgb2gray

import numpy as np
import os
from plenopticam import misc
import platform

def blur_metric(img_tile):
    ''' img_tile : cropped image '''

    img = rgb2gray(img_tile) if len(img_tile.shape) == 3 else img_tile
    y, x = img.shape

    magnitude = abs(np.fft.fft2(img))
    magnitudeCrop = magnitude[:int(np.ceil(y/2)), :int(np.ceil(x/2))]
    #figure, imshow(magnitude,[0 1000]), colormap gray # magnitude

    # total energy
    TE = sum(sum(magnitudeCrop**2))

    # high frequency energy
    freq_bounds = (y//100, x//100)
    HE = TE - sum(sum(magnitudeCrop[:freq_bounds[0], :freq_bounds[1]]**2))

    # energy ratio (Sharpness)
    S = HE/TE

    return S


def michelson_contrast(img_tile):
    ''' https://colorusage.arc.nasa.gov/luminance_cont.php '''

    lum_tile = misc.yuv_conv(img_tile)[..., 0]

    c_m = (lum_tile.max() - lum_tile.min()) / (lum_tile.max() + lum_tile.min())

    return c_m


if __name__ == "__main__":

    if platform.system() == 'Windows':
        fp_lytro = ''
        fp_ours = ''
    elif platform.system() == 'Darwin':
        fp_lytro = '/Volumes/SD CARD 1/IEEEtran/img/refo_lytro'
        fp_ours = '/Volumes/SD CARD 1/IEEEtran/img/refo_upscale_7px'
    else:
        fp_lytro = ''
        fp_ours = ''

    # loop over directories
    for fp in [fp_lytro, fp_ours]:
        slice_fns = [f for f in os.listdir(fp) if f.__contains__('crop')]

        s_list = list()

        # loop over filenames in directory
        for slice_fn in slice_fns:

            # load cropped slice
            img_tile = misc.load_img_file(os.path.join(fp, slice_fn))

            # remove alpha channel if present
            img_tile = img_tile[..., :3]

            # rescale tile for fair comparison
            img_tile = misc.img_resize(img_tile, 2.28122448) if fp.__contains__('refo_lytro') else img_tile

            # store results
            s_list.append((slice_fn, blur_metric(img_tile), michelson_contrast(img_tile)))

        for s in s_list:
            print(s)
