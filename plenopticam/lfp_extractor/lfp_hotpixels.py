from plenopticam import misc
from plenopticam.lfp_extractor import LfpViewpoints

class LfpHotPixels(LfpViewpoints):

    def __init__(self, *args, **kwargs):
        super(LfpHotPixels, self).__init__(*args, **kwargs)

    def main(self):

        self.proc_vp_arr(self.correct_outliers, msg='Remove pixel outliers')

    def correct_outliers(self, img, n=2, perc=.2):

        for j in range(n, img.shape[0]-n):
            for i in range(n, img.shape[1]-n):
                win = img[j-n:j+n+1, i-n:i+n+1]

                # hot pixel detection
                num_hi = len(win[win > img[j, i]*(1-perc)])

                # dead pixel detection
                num_lo = len(win[win < img[j, i]*perc])

                if num_hi < win.size/5 or num_lo > win.size/5:
                    # replace outlier by average of all directly adjacent pixels
                    img[j, i] = (sum(sum(img[j-1:j+2, i-1:i+2]))-img[j, i])/8.

        return img

    def correct_luma_outliers(self, img, n=2, perc=.2):

        # luma channel conversion
        luma = misc.yuv_conv(img.copy())[..., 0]

        for j in range(n, luma.shape[0]-n):
            for i in range(n, luma.shape[1]-n):
                win = luma[j-n:j+n+1, i-n:i+n+1]

                # hot pixel detection
                num_hi = len(win[win > luma[j, i]*(1-perc)])

                # dead pixel detection
                num_lo = len(win[win < luma[j, i]*(1+perc)])

                if num_hi < win.size/5 or num_lo < win.size/5:
                    # replace outlier by average of all directly adjacent pixels
                    img[j, i, :] = (sum(sum(img[j-1:j+2, i-1:i+2, :]))-img[j, i, :])/8.

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