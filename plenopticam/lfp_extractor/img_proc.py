# external libs
import numpy as np
from plenopticam import misc

try:
    from scipy.signal import medfilt
    from scipy.ndimage import median_filter
except ImportError:
    raise ImportError('Please install scipy package.')

def auto_contrast(img_arr, p_lo=0.001, p_hi=0.999, ch=0):
    ''' according to Adi Shavit on https://stackoverflow.com/questions/9744255/instagram-lux-effect/9761841#9761841 '''

    # estimate contrast und brightness parameters (by default: achromatic "luma" channel only)
    val_lim = 2**16-1
    img_yuv = misc.yuv_conv(img_arr)
    h = np.histogram(img_yuv[..., ch], bins=np.arange(val_lim))[0]
    H = np.cumsum(h)/float(np.sum(h))
    try:
        px_lo = find_x_given_y(p_lo, np.arange(val_lim), H)
        px_hi = find_x_given_y(p_hi, np.arange(val_lim), H)
    except:
        px_lo = 0
        px_hi = 1
    A = np.array([[px_lo, 1], [px_hi, 1]])
    b = np.array([0, val_lim])
    contrast, brightness = np.dot(np.linalg.inv(A), b)

    return contrast, brightness

def find_x_given_y(value, x, y, tolerance=1e-3):
    return np.mean(np.array([(xi, yi) for (xi, yi) in zip(x, y) if abs(yi - value) <= tolerance]).T[0])

def correct_contrast(img_arr, contrast=1, brightness=0, ch=0):

    # color model conversion
    img_yuv = misc.yuv_conv(img_arr)

    # convert to float
    f = img_yuv[..., ch].astype(np.float32)

    # perform auto contrast (by default: "value" channel only)
    img_yuv[..., ch] = contrast * f + brightness

    # clip to input extrema to remove contrast outliers
    img_yuv[..., ch][img_yuv[..., ch] < img_arr.min()] = img_arr.min()
    img_yuv[..., ch][img_yuv[..., ch] > img_arr.max()] = img_arr.max()

    # color model conversion
    img = misc.yuv_conv(img_yuv, inverse=True)

    return img

def contrast_per_channel(img, sat_perc=0.1):
    # sat_perc is the saturation percentile which will be cut-off at the lower and higher end in each color channel

    q = [sat_perc/100, 1-sat_perc/100]

    for ch in range(img.shape[2]):

        # compute histogram quantiles
        tiles = np.quantile(img[..., ch], q)

        # clip histogram quantiles
        img[..., ch][img[..., ch] < tiles[0]] = tiles[0]
        img[..., ch][img[..., ch] > tiles[1]] = tiles[1]

    return img

# def correct_hotpixels(img):
#
#     if len(img.shape) == 3:
#         for i, channel in enumerate(img.swapaxes(0, 2)):
#             img[:, :, i] = correct_outliers(channel).swapaxes(0, 1)
#     elif len(img.shape) == 2:
#         img = correct_outliers(img)
#
#     return img
#
# def correct_outliers(channel):
#
#     # create copy of channel for filtering
#     arr = channel.copy()
#
#     # perform median filter convolution
#     #med_img = medfilt(arr, kernel_size=(3, 3))
#     med_img = median_filter(arr, size=2)
#
#     # compute absolute differences per pixel
#     diff_img = abs(arr-med_img)
#     del arr
#
#     # obtain intensity threshold for pixels that have to be replaced
#     threshold = np.std(diff_img)*10#np.max(diff_img-np.mean(diff_img)) * .4
#
#     # replace pixels above threshold by median filtered pixels while ignoring image borders (due to 3x3 kernel)
#     channel[1:-1, 1:-1][diff_img[1:-1, 1:-1] > threshold] = med_img[1:-1, 1:-1][diff_img[1:-1, 1:-1] > threshold]
#
#     return channel

def correct_luma_outliers(img, n=2, perc=.2):

    # luma channel conversion
    luma = misc.yuv_conv(img.copy())[..., 0]

    for i in range(n, luma.shape[0]-n):
        for j in range(n, luma.shape[1]-n):
            win = luma[i-n:i+n+1, j-n:j+n+1]

            # hot pixel detection
            num_hi = len(win[win > luma[i, j]*(1-perc)])

            # dead pixel detection
            num_lo = len(win[win < luma[i, j]*(1+perc)])

            if num_hi < win.size/5 or num_lo < win.size/5:
                # replace outlier by average of all directly adjacent pixels
                img[i, j, :] = (sum(sum(img[i-1:i+2, j-1:j+2, :]))-img[i, j, :])/8.

    return img

def proc_vp_arr(fun, vp_img_arr, *args):
    ''' process viewpoint images based on provided function handle and argument data '''

    for j in range(vp_img_arr.shape[0]):
        for i in range(vp_img_arr.shape[1]):
            vp_img_arr[j, i, :, :, :] = fun(vp_img_arr[j, i, :, :, :], *args)

    return vp_img_arr

def proc_img(fun, img):
    ''' process image along third dimension given a function handle '''

    for i in range(img.shape[2]):
            img[..., i] = fun(img[..., i])

    return img

def robust_awb(img, t=0.3, max_iter=1000):
    ''' inspired by Jun-yan Huo et al. and http://web.stanford.edu/~sujason/ColorBalancing/Code/robustAWB.m '''

    img = misc.type_norm(img, dtype='float16', lim_min=0, lim_max=1.0)
    ref_pixel = img[0, 0, :].copy()

    u = .01     # gain step size
    a = .8      # double step threshold
    b = .001    # convergence threshold

    gains_adj = np.array([1., 1., 1.])

    #sRGBtoXYZ = [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]]
    sRGBtoXYZ = [[0.4124564, 0.2126729, 0.0193339], [0.3575761, 0.7151522, 0.0193339], [0.1804375, 0.0721750, 0.9503041]]

    for i in range(max_iter):
        img_yuv = misc.yuv_conv(img)
        f = (abs(img_yuv[..., 1]) + abs(img_yuv[..., 2])) / img_yuv[..., 0]
        grays = np.zeros(img_yuv.shape)
        grays[f<t] = img_yuv[f<t]
        if np.sum(f<t) == 0:
            print('No valid gray pixels found.')
            break

        u_bar = np.mean(grays[..., 1])  #estimate
        v_bar = np.mean(grays[..., 2])  #estimate

        #rgb_est = misc.yuv_conv(np.array([100, u_bar, v_bar]), inverse=True)    # convert average gray from YUV to RGB

        # U > V: blue needs adjustment otherwise red is treated
        err, ch = (u_bar, 2) if abs(u_bar) > abs(v_bar) else (v_bar, 0)

        if abs(err) >= a:
            delta = 2*np.sign(err)*u   # accelerate gain adjustment if far off
        elif abs(err) < b:  #converged
            delta = 0
            print(('Converged. U_bar and V_bar < {0} in magnitude.').format(str(b)))
            break
        else:
            delta = err*u

        gains_adj[ch] -= delta   # negative fdbk loop

        img = np.dot(img, np.diag(gains_adj))

    gains = img[0, 0, :]/ref_pixel

    return gains

def correct_awb(img, gains):

    return np.dot(img, np.diag(gains))