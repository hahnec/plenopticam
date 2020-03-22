import numpy as np


def hsv2rgb(hsv):
    """ Convert HSV color space to RGB color space

    :param hsv: numpy.ndarray
    :return: numpy.ndarray
    """

    hi = np.floor(hsv[..., 0] / 60.0) % 6
    hi = hi.astype('uint8')
    v = hsv[..., 2].astype('float')
    f = (hsv[..., 0] / 60.0) - np.floor(hsv[..., 0] / 60.0)
    p = v * (1.0 - hsv[..., 1])
    q = v * (1.0 - (f * hsv[..., 1]))
    t = v * (1.0 - ((1.0 - f) * hsv[..., 1]))

    rgb = np.zeros(hsv.shape)
    rgb[hi == 0, :] = np.dstack((v, t, p))[hi == 0, :]
    rgb[hi == 1, :] = np.dstack((q, v, p))[hi == 1, :]
    rgb[hi == 2, :] = np.dstack((p, v, t))[hi == 2, :]
    rgb[hi == 3, :] = np.dstack((p, q, v))[hi == 3, :]
    rgb[hi == 4, :] = np.dstack((t, p, v))[hi == 4, :]
    rgb[hi == 5, :] = np.dstack((v, p, q))[hi == 5, :]

    return rgb


def rgb2hsv(rgb):
    """ Convert RGB color space to HSV color space

    :param rgb: numpy.ndarray
    :return: numpy.ndarray
    """

    rgb = rgb.astype('float')
    maxv = np.amax(rgb, axis=2)
    maxc = np.argmax(rgb, axis=2)
    minv = np.amin(rgb, axis=2)
    minc = np.argmin(rgb, axis=2)

    # slicing implementation of HSV channel definitions
    hsv = np.zeros(rgb.shape, dtype='float')
    hsv[maxc == minc, 0] = np.zeros(hsv[maxc == minc, 0].shape)
    hsv[maxc == 0, 0] = (((rgb[..., 1] - rgb[..., 2]) * 60.0 / (maxv - minv +np.spacing(1))) % 360.0)[maxc == 0]
    hsv[maxc == 1, 0] = (((rgb[..., 2] - rgb[..., 0]) * 60.0 / (maxv - minv +np.spacing(1))) + 120.0)[maxc == 1]
    hsv[maxc == 2, 0] = (((rgb[..., 0] - rgb[..., 1]) * 60.0 / (maxv - minv +np.spacing(1))) + 240.0)[maxc == 2]
    hsv[maxv == 0, 1] = np.zeros(hsv[maxv == 0, 1].shape)
    hsv[maxv != 0, 1] = (1 - minv / (maxv + np.spacing(1)))[maxv != 0]
    hsv[..., 2] = maxv

    return hsv


def hsv_conv(img, inverse=False):

    if len(img.shape) != 3 or img.shape[2] != 3:
        raise BaseException

    if not inverse:
        arr = rgb2hsv(img)
    else:
        arr = hsv2rgb(img)

    return arr


def rgb2gray(rgb, standard='HDTV'):

    # HDTV excludes foot- and headroom whereas SDTV accommodates some
    GRAY = [0.2126, 0.7152, 0.0722] if standard == 'HDTV' else [0.299, 0.587, 0.114]

    return np.dot(rgb[..., :3], GRAY) if len(rgb.shape) == 3 else rgb


def yuv_conv(img, inverse=False, standard='HDTV'):

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

    return np.dot(img, yuv_mat)


def rgb2xyz(rgb):
    '''
    https://web.archive.org/web/20120502065620/http://cookbooks.adobe.com/post_Useful_color_equations__RGB_to_LAB_converter-14227.html
    '''

    rgb = rgb / np.max(rgb)

    for ch in range(rgb.shape[2]):
        mask = rgb[..., ch] > 0.04045
        rgb[..., ch][mask] = np.power((rgb[..., ch] + 0.055) / 1.055, 2.4)[mask]
        rgb[..., ch][~mask] /= 12.92

    rgb *= 100

    # Observer. = 2°, Illuminant = D65 (from Adobe)
    mat_adb = np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]])

    # from Reinhard et al. paper (2001)
    mat_itu = np.array([[0.4306, 0.2220, 0.0202], [0.3415, 0.7067, 0.1295], [0.1784, 0.0713, 0.9394]])

    xyz = np.dot(rgb, mat_adb)

    return xyz

# Observer. = 2°, Illuminant = D65
REF_X = 95.047
REF_Y = 100.000
REF_Z = 108.883


def xyz2lab(xyz):

    xyz[..., 0] /= REF_X
    xyz[..., 1] /= REF_Y
    xyz[..., 2] /= REF_Z

    for ch in range(xyz.shape[2]):
        mask = xyz[..., ch]>0.008856
        xyz[..., ch][mask] = np.power(xyz[..., ch], 1/3.)[mask]
        xyz[..., ch][~mask] = (7.787*xyz[..., ch] + 16/116.)[~mask]

    lab = np.zeros(xyz.shape)
    lab[..., 0] = (116 * xyz[..., 1]) - 16
    lab[..., 1] = 500 * (xyz[..., 0]-xyz[..., 1])
    lab[..., 2] = 200 * (xyz[..., 1]-xyz[..., 2])

    return lab


def lab2xyz(lab):

    xyz = np.zeros(lab.shape)
    xyz[..., 1] = (lab[..., 0] + 16) / 116.
    xyz[..., 0] = lab[..., 1] / 500. + xyz[..., 1]
    xyz[..., 2] = xyz[..., 1] - lab[..., 2] / 200.

    for ch in range(xyz.shape[2]):
        mask = np.power(xyz[..., ch], 3) > 0.008856
        xyz[..., ch][mask] = np.power(xyz[..., ch], 3)[mask]
        xyz[..., ch][~mask] = (xyz[..., ch] - 16/116.)[~mask] / 7.787

    xyz[..., 0] *= REF_X
    xyz[..., 1] *= REF_Y
    xyz[..., 2] *= REF_Z

    return xyz


def xyz2rgb(xyz):

    xyz /= 100.

    # Observer. = 2°, Illuminant = D65
    mat = np.array([[3.2406, -0.9689, -0.0557], [-1.5372,  1.8758, -0.204], [-0.4986, -0.0415,  1.057]])
    rgb = np.dot(xyz, mat)

    for ch in range(rgb.shape[2]):
        mask = rgb[..., ch] > 0.0031308
        rgb[..., ch][mask] = 1.055 * np.power(rgb[..., ch], 1/2.4)[mask] - 0.055
        rgb[..., ch][~mask] *= 12.92

    return rgb


def rgb2lab(rgb):

    xyz = rgb2xyz(rgb)
    lab = xyz2lab(xyz)

    return lab


def lab2rgb(lab):
    xyz = lab2xyz(lab)
    rgb = xyz2rgb(xyz)

    return rgb
