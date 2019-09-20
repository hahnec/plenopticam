import numpy as np

from plenopticam import misc


class HistogramEqualizer(object):

    def __init__(self, img=None, bin_num=None, ch=None):

        self._ref_img = None if img is None else img
        self._bin_num = self.set_bin_num() if bin_num is None else bin_num
        self._ch = 0 if ch is None else ch

    def set_bin_num(self):

        dtype = self._ref_img.dtype.__str__()
        if dtype.startswith('float'):
            lim_max = np.finfo(np.dtype(dtype)).max
        elif dtype.startswith(('int', 'uint')):
            lim_max = np.iinfo(np.dtype(dtype)).max
        else:
            lim_max = 1.0

        return lim_max if lim_max is not None and lim_max < 2**16-1 else 2**16-1

    def set_histeq_params(self, ch=None):

        # channel selection
        self._ch = self._ch if ch is None else ch
        img_ch = self._ref_img[..., self._ch]

        # get image histogram
        imhist, self._bins = np.histogram(img_ch.flatten(), np.arange(self._bin_num))
        self._cdf = imhist.cumsum()  # cumulative distribution
        self._cdf = self._bin_num * self._cdf / self._cdf[-1]  # normalize

        return True

    def hist_spec(self, type='linear', param=1., flip=False):

        # set linear function as default
        des_hist = np.linspace(0, 1, self._bin_num)

        # modify function shape according to provided parameters
        if type == 'linear':
            des_hist *= param
            des_hist -= (param-1)/2 if param != 1 and param != 0 else 0
            # clip range below 0 and above 1
            des_hist[des_hist < 0] = 0
            des_hist[des_hist > 1] = 1
        elif type == 'exp' or type == 's-curve':
            des_hist **= param
            if flip:
                des_hist = 1-des_hist[::-1]
            if type == 's-curve':
                lower_pt = (des_hist[::2]/2)[:-1]
                des_hist = np.concatenate((lower_pt, 1-lower_pt[::-1]))
                des_hist = np.append(des_hist, 1) if len(des_hist)+1 == len(self._bins) else des_hist

        # normalize to maximum value of data type
        des_hist *= self._bin_num

        # convert to integer if required
        if self._ref_img.dtype.__str__().startswith(('int', 'uint')):
            des_hist = np.round(des_hist).astype(self._ref_img.dtype)

        return des_hist

    def correct_histeq(self, ch=None):

        # channel selection
        self._ch = self._ch if ch is None else ch
        img_ch = self._ref_img[..., self._ch]

        # use specified histogram and cdf to generate desired histogram
        des_hist = self.hist_spec(type='s-curve', param=1.5, flip=False)
        new_img = np.interp(img_ch.flatten(), des_hist[:-1], self._cdf)

        # reconstruct new image
        new_img = new_img.reshape(self._ref_img[..., self._ch].shape)
        self._ref_img[..., self._ch] = new_img

        return True

    def lum_eq(self):

        # RGB/YUV color conversion
        self._ref_img = misc.yuv_conv(self._ref_img)

        # create cumulative distribution function of reference image
        self.set_histeq_params()

        # histogram mapping using cumulative distribution function
        self.correct_histeq()

        # YUV/RGB color conversion
        return misc.yuv_conv(self._ref_img, inverse=True)

    def uv_eq(self):

        # RGB/YUV color conversion
        self._ref_img = misc.yuv_conv(self._ref_img)

        for i in range(1, self._ref_img.shape[-1]):

            # create cumulative distribution function of reference image
            self.set_histeq_params(ch=i)

            # histogram mapping using cumulative distribution function
            self.correct_histeq(ch=i)

        # YUV/RGB color conversion
        return misc.yuv_conv(self._ref_img, inverse=True)

    def awb_eq(self):

        # iterate through all colour channels
        for i in range(self._ref_img.shape[-1]):

            # create cumulative distribution function of reference image
            self.set_histeq_params(ch=i)

            # histogram mapping using cumulative distribution function
            self.correct_histeq(ch=i)

        return self._ref_img
