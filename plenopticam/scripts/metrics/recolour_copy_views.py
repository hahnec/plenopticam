import os
import shutil

lf_path = '/Users/Admin/Pictures/Plenoptic/INRIA_SIROCCO'
dirs = [item for item in os.listdir(lf_path) if os.path.isdir(os.path.join(lf_path, item))]
target_dir = os.path.join(lf_path, '..', 'color_transfer_eval', 'central_views')
os.makedirs(target_dir, exist_ok=True)


for dir in dirs:
    fname_src = os.path.join(lf_path, dir, 'viewpoints_15px', '2_7.png')
    fname_ref = os.path.join(lf_path, dir, 'viewpoints_15px', '7_7.png')
    shutil.copyfile(fname_ref, os.path.join(target_dir, os.path.basename(dir))+'.png')
