import os
from shutil import copyfile, rmtree


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        pass


path = r'C:\Users\chahne\Pictures\Dataset_INRIA_SIROCCO\Data' #os.getcwd()

# create folder for thumbnails
dst = os.path.join(os.path.dirname(path), 'thumb_collection')
rmtree(dst) if os.path.exists(dst) else None
mkdir_p(dst)
mkdir_p(os.path.join(dst, 'other_views'))       # sub-folder for marginal sub-aperture images

# filter folders (exclude previously generated thumb collection)
dirs = [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x)) and x != 'thumb_collection']

for dir in dirs:

    # copy central sub-aperture image
    fp = os.path.join(path, dir, 'thumbnail.png')
    copyfile(fp, os.path.join(dst, dir+".png"))
    print(fp)

    # copy marginal sub-aperture image
    j, i = 2, 7
    path_marginal_views = os.path.join(path, dir, 'viewpoints_%spx' % 15)
    if os.path.exists(path_marginal_views):
        fp = os.path.join(path_marginal_views, '%s_%s.png' % (j, i))
        copyfile(fp, os.path.join(dst, 'other_views', dir+'_%s_%s.png' % (j, i)))
