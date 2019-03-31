import zlib

import numpy as np
from scipy.interpolate import interp2d

def create_gauss_kernel(l=25, sig=1.):
    
    # ensure length is odd
    l = int((l-1)/2) + int((l+1)/2)
    
    # compute Gaussian kernel
    ax = np.arange(-l // 2 + 1., l // 2 + 1.)
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx**2 + yy**2) / (2. * sig**2))
    kernel /= kernel.sum()
    
    return kernel

def uint16_norm(img, min=None, max=None):
    ''' normalize image array to 16-bit unsigned integer '''

    if min is None:
        min = img.min()

    if max is None:
        max = img.max()

    return np.asarray(np.round((img-min)/(max-min)*(2**16-1)), dtype=np.uint16)    # what if negative float?

def uint8_norm(img, min=None, max=None):
    ''' normalize image array to 8-bit unsigned integer '''

    if min is None:
        min = img.min()

    if max is None:
        max = img.max()

    return np.asarray(np.round((img-min)/(max-min)*(2**8-1)), dtype=np.uint8)      # what if negative float?

def type_norm(img, dtype='float16', lim_min=None, lim_max=None):
    ''' normalize numpy image array for provided data type '''

    # e.g.         # RGB image normalization
    #         #self._rgb_img = misc.type_norm(self._rgb_img, dtype='float32', lim_min=2**10, lim_max=2**16-2**10)

    img = np.asarray(img, dtype='float64')
    min = img.min()
    max = img.max()

    if dtype.startswith('float'):
        lim_max = np.finfo(np.dtype(dtype)).max if lim_max is None else lim_max
        lim_min = np.finfo(np.dtype(dtype)).min if lim_min is None else lim_min
        img_norm = (img-min)/(max-min)*(lim_max-lim_min)+lim_min

    elif dtype.startswith(('int', 'uint')):
        lim_max = np.iinfo(np.dtype(dtype)).max if lim_max is None else lim_max
        lim_min = np.iinfo(np.dtype(dtype)).min if lim_min is None else lim_min
        img_norm = np.round((img-min)/(max-min)*(lim_max-lim_min)+lim_min)

    else:
        lim_max = 1.0 if lim_max is None else lim_max
        lim_min = 0.0 if lim_min is None else lim_min
        img_norm = (img-min)/(max-min)*(lim_max-lim_min)+lim_min

    return np.asarray(img_norm, dtype=dtype)

def safe_get(dict, *keys):

    for key in keys:
        try:
            dict = dict[key]
        except KeyError:
            return None

    return dict

def rgb2gray(rgb, standard='HDTV'):

    # HDTV excludes foot- and headroom whereas SDTV leaves some
    GRAY = [0.2126, 0.7152, 0.0722] if standard == 'HDTV' else [0.299, 0.587, 0.114]

    return np.dot(rgb[..., :3], GRAY) if len(rgb.shape) == 3 else rgb

def yuv_conv(rgb, inverse=False, standard='HDTV'):

    # excludes foot- and headroom
    YUV_MAT_HDTV = np.array([[0.2126, -0.09991, 0.615], [0.7152, -0.33609, -0.55861], [0.0722, 0.436, -0.05639]])
    YUV_MAT_HDTV_INV = np.array([[1.0, 1.0, 1.0], [0.0, -0.21482, 2.12798], [1.28033, -0.38059, 0.0]])

    # includes foot- and headroom
    YUV_MAT_SDTV = np.array([[0.299, -0.299, 0.701], [0.587, -0.587, -0.587], [0.144, 0.886, -0.114]])
    YUV_MAT_SDTV_INV = np.array([[1.0, 1.0, 1.0], [0.0, -0.39465, 2.03211], [1.13983, -0.58060, 0]])

    if standard == 'HDTV':
        yuv_mat = YUV_MAT_HDTV_INV if inverse else YUV_MAT_HDTV
    else:
        yuv_mat = YUV_MAT_SDTV_INV if inverse else YUV_MAT_SDTV

    return np.dot(rgb, yuv_mat)

def img_resize(img, x_scale=1, y_scale=None):
    ''' perform image interpolation based on scipy lib '''

    if not y_scale:
        y_scale = x_scale

    n, m, P = img.shape
    new_img = np.zeros([int(n*y_scale), int(m*x_scale), P])
    for p in range(P):
        f = interp2d(range(m), range(n), img[:, :, p])
        new_img[:, :, p] = f(np.linspace(0, m - 1, m * x_scale), np.linspace(0, n - 1, n * y_scale))

    return new_img


def place_dnp(dus):

    m, n = (79, 32)
    str = b'x\x9c\xfb\xff\x7f\x14\x10\t.\x8b\x80A\xc2.\xfc\xf2""\x13q\xca\xaf\x05R\x85""\xd8M\x80\xca\xbf\x14\x11i\xc2\'\xff_D\xa4\x10\x9f\xfc=\xfc\xfa\xbf\x00\xed\xbf\x8c\xdf\xfd\x0bp\xba\x1f\x04\n\x8fc\x97\x86\xbb\x0f\x17\x18h\xf9Q\x80\x05\x00\x00\xce\xd6\xbb\x86x\x9c\x85\x93\xcd\n\x840\x0c\x84M\xb1P\xda\xe0Q<\x08\xc5\x8b`<\xf6\xa0\x08\xb6y\xff\xa7Z\x97]\xf7G\xad\x99\xeb\x97\xa4m:S\x14\xbb@ic\x11\xad\xd1\n\x8a\x93@c\xed{\x1aG\xea}\x8d\xfaP\x01e\xd5RXbbNq\t\xd4V\xe5o\x05\x98\x86\xe6\xc8\x1f\xc5\x99\x1a\xf3-P\xce\x87\x95\xff\xb4\x06\xef\xd4\xde\xed\xba)\xf1Ai\xea\x1c\xbc\x87\xfb3\xde4\xf9\xd7\x11e\x13\xae0\xa7\xd0\x94\xcf\xf6\x8a\xd6+\xbc\xdd\x81\xaam\x80n\xe7k\xcc<\xb7\xba\x00\xa4\x98\xe3\x91\x10T\x1dr\x989\xd4J\xfb%\xcf\x17\xafM\x9f\x1d\xbf\x1d\xd0\x1bKy\xccL\x16\xc7;>\xa2\xc4\xedp\xb9\xbc\x97\xd2`\xa5\xfbI\xef\x93\xf6#\xedW\xfa\x1f\xf1\x7f%\x7f\xe4\xfc\x95v\x7fe\xfdi\xe1\xde\xdf\xdf\x00\x08\xf9\x10\xf3%\xe6s\xcf\xb7Ct\xff\xf9~\x00B\x85\xaej'
    dnp = np.asarray([np.frombuffer(zlib.decompress(x), 'uint8').reshape(n, n) for x in [str[:m], str[m:]]])/255.

    s, t = dus.shape[:2]
    y, x = (s-n, s+(t-s)//2-n)
    dus[y:y+n, x:x+n, :] *= dnp[0, ...]

    return dus