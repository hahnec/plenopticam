import numpy as np

from plenopticam import misc


class HistogramEqualizer(object):

    def __init__(self, img=None, bin_num=None, ch=None):

        self._ref_img = None if img is None else img
        self._bin_num = 2**16-1 if bin_num is None else bin_num
        self._ch = 0 if ch is None else ch

    def set_histeq_params(self, ch=None):

        # color conversion
        #img = misc.yuv_conv(self._ref_img)

        # channel selection
        self._ch = self._ch if ch is None else ch
        img_ch = self._ref_img[..., self._ch]

        # get image histogram
        imhist, self._bins = np.histogram(img_ch.flatten(), np.arange(self._bin_num))   #, normed=True
        self._cdf = imhist.cumsum()  # cumulative distribution
        self._cdf = self._bin_num * self._cdf / self._cdf[-1]  # normalize

        return True

    def correct_histeq(self, ch=None):

        # color conversion
        #img = misc.yuv_conv(self._ref_img)

        # channel selection
        self._ch = self._ch if ch is None else ch
        img_ch = self._ref_img[..., self._ch]

        # use linear interpolation of cdf to find new pixel values
        new_img = np.interp(img_ch.flatten(), self._bins[:-1], self._cdf)

        # reconstruct new image
        new_img = new_img.reshape(self._ref_img[..., self._ch].shape)
        self._ref_img[..., self._ch] = new_img

        return True

    def main(self):


        self._ref_img = misc.yuv_conv(self._ref_img)

        self.set_histeq_params()

        # self.proc_vp_arr(self.correct_histeq, self.vp_img_arr)
        self.correct_histeq()

        return misc.yuv_conv(self._ref_img, inverse=True)
