# external libs
import numpy as np

def pitch_eval(centroids, patch_size, cfg=None, sta=None):
    ''' provide odd patch size that is safe to use '''

    centroids = np.asarray(centroids) # needed?

    # estimate maximum patch size
    central_row_idx = int(centroids[:, 3].max()/2)
    mean_pitch = int(np.round(np.mean(np.diff(centroids[centroids[:, 3] == central_row_idx, 0]))))

    # ensure patch size and mean patch size are odd
    patch_size += np.mod(patch_size, 2)-1
    mean_pitch += np.mod(mean_pitch, 2)-1

    # comparison of patch size and mean size
    msg_str = None
    if patch_size > mean_pitch:
        patch_size = mean_pitch
        msg_str = 'Patch size ({0} px) is larger than micro image size and reduced to {1} pixels.'
    elif patch_size < 3 and mean_pitch > 3:
        patch_size = mean_pitch
        msg_str = 'Patch size ({0} px) is too small and increased to {1} pixels.'
    elif patch_size < 3 and mean_pitch < 3:
        raise Exception('Micro image dimensions are too small for light field computation.')

    if msg_str:
        # status update
        sta.status_msg(msg_str.format(patch_size, mean_pitch), cfg.params[cfg.opt_prnt])

    return patch_size