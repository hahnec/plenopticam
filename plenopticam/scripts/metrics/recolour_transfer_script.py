import os
import color_matcher as cm
import imageio
import numpy as np
import ot

lf_path = os.path.join('/Users', 'Admin', 'Pictures', 'Plenoptic', 'INRIA_SIROCCO')
dirs = [item for item in os.listdir(lf_path) if os.path.isdir(os.path.join(lf_path, item))]
methods = ['POT']#['mvgd', 'mkl', 'hm', 'hm-mkl-hm', 'hm-mvgd-hm']#
target_dir = os.path.join(lf_path, '..', 'color_transfer_eval')
os.makedirs(target_dir, exist_ok=True)


def uint8_norm(img):
    return np.uint8(np.round((img-img.min())/(img.max()-img.min())*255))


def float_norm(img):
    return (img.astype(np.float64)-img.min())/(img.max()-img.min())


def im2mat(img):
    """Converts and image to matrix (one pixel per line)"""
    return img.reshape((img.shape[0] * img.shape[1], img.shape[2]))


for dir in dirs:
    fname_src = os.path.join(lf_path, dir, 'viewpoints_15px', '2_7.png')
    fname_ref = os.path.join(lf_path, dir, 'viewpoints_15px', '7_7.png')
    src = imageio.imread(uri=fname_src)
    ref = imageio.imread(uri=fname_ref)
    for m in methods:
        if m != 'POT':
            matcher = cm.ColorMatcher(src, ref, method=m)
            res = matcher.main()
        else:
            src, ref = float_norm(src), float_norm(ref)
            X1 = im2mat(src)
            X2 = im2mat(ref)

            # training samples
            nb = 1000
            r = np.random.RandomState(42)
            idx1 = r.randint(X1.shape[0], size=(nb,))
            idx2 = r.randint(X2.shape[0], size=(nb,))

            Xs = X1[idx1, :]
            Xt = X2[idx2, :]
            #ot_obj = ot.da.EMDTransport()
            ot_obj = ot.da.MappingTransport(mu=1e0, eta=1e-2, sigma=1, bias=False, max_iter=10, verbose=1)
            ot_obj.fit(Xs=Xs, Xt=Xt)
            X1tn = ot_obj.transform(Xs=im2mat(src))  # use the estimated mapping
            res = X1tn.reshape(src.shape)

        res = uint8_norm(res)
        os.makedirs(os.path.join(target_dir, m), exist_ok=True)
        imageio.imwrite(uri=os.path.join(target_dir, m, os.path.basename(dir)+'.png'), im=res)
