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


def rgb2lab(input):
    ''' https://stackoverflow.com/questions/13405956/convert-an-image-rgb-lab-with-python
    :param input: RGB tuple
    :return: Lab tuple
    '''

    num = 0
    RGB = [0, 0, 0]

    for value in input:
        value = float(value) / 255

        if value > 0.04045:
            value = ((value + 0.055) / 1.055) ** 2.4
        else :
            value = value / 12.92

        RGB[num] = value * 100
        num = num + 1

    XYZ = [0, 0, 0]

    X = RGB[0] * 0.4124 + RGB[1] * 0.3576 + RGB[2] * 0.1805
    Y = RGB[0] * 0.2126 + RGB[1] * 0.7152 + RGB[2] * 0.0722
    Z = RGB[0] * 0.0193 + RGB[1] * 0.1192 + RGB[2] * 0.9505
    XYZ[0] = round(X, 4)
    XYZ[1] = round(Y, 4)
    XYZ[2] = round(Z, 4)

    XYZ[0] = float(XYZ[0]) / 95.047         # ref_X =  95.047   Observer= 2°, Illuminant= D65
    XYZ[1] = float(XYZ[1]) / 100.0          # ref_Y = 100.000
    XYZ[2] = float(XYZ[2]) / 108.883        # ref_Z = 108.883

    num = 0
    for value in XYZ:

        if value > 0.008856:
            value = value ** (0.3333333333333333)
        else :
            value = (7.787 * value) + (16/116)

        XYZ[num] = value
        num = num + 1

    Lab = [0, 0, 0]

    L = (116 * XYZ[1]) - 16
    a = 500 * (XYZ[0] - XYZ[1])
    b = 200 * (XYZ[1] - XYZ[2])

    Lab[0] = round(L, 4)
    Lab[1] = round(a, 4)
    Lab[2] = round(b, 4)

    return Lab
