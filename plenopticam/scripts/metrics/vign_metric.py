import numpy as np
from plenopticam.misc import load_img_file


def psnr(img1=None, img2=None, quant_steps=2**8-1):

    img1 = np.asarray(img1, dtype=np.float64)/img1.max()
    img2 = np.asarray(img2, dtype=np.float64)/img2.max()

    mse = np.mean((img1-img2)**2)
    if mse == 0:
        return 100
    return 20*np.log10(quant_steps/np.sqrt(mse))


if __name__ == "__main__":

    img_ref = load_img_file('/Users/Admin/Unterlagen/PhD/07 publications/18_plenopticam/IEEEtran_1st-revision/img/vign/build-sigd0.png')
    img_div = load_img_file('/Users/Admin/Unterlagen/PhD/07 publications/18_plenopticam/IEEEtran_1st-revision/img/vign/build-div-sigd15.png')
    img_fit = load_img_file('/Users/Admin/Unterlagen/PhD/07 publications/18_plenopticam/IEEEtran_1st-revision/img/vign/build-fit-sigd15.png')

    print(psnr(img_ref, img_div))
    print(psnr(img_ref, img_fit))
