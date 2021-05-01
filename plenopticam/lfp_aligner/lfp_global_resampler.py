# local imports
from plenopticam.lfp_aligner.lfp_microlenses import LfpMicroLenses
from plenopticam.lfp_calibrator.grid_fitter import GridFitter
from plenopticam import misc

# external libs
import numpy as np
from skimage import transform
import copy


class LfpGlobalResampler(LfpMicroLenses):

    def __init__(self, *args, **kwargs):
        super(LfpGlobalResampler, self).__init__(*args, **kwargs)

        # internal variables
        self._lfp_prj = self._lfp_img.copy()

    def global_resampling(self):

        # check interrupt status
        if self.sta.interrupt:
            return False

        # global light-field image rectification
        self.projective_alignment()

        # global rectification of hexagonal micro image array
        self.hexagonal_alignment()

    def projective_alignment(self):

        # get projective matrix from centroids
        gfxy = GridFitter(self._CENTROIDS.copy(), flip_xy=True)
        gfxy.main()
        pmat_cent = gfxy.pmat.copy()
        R, K, t = gfxy.decompose(pmat_cent)
        del gfxy

        # get target micro image size
        target_pitch = np.array([np.floor(K[1, 1]), np.floor(K[0, 0])])
        if self.cfg.calibs[self.cfg.pat_type] == 'rec':
            target_pitch += np.mod(target_pitch+1, 2)

        self._limg_pitch = target_pitch.astype('int')
        scales = np.array([self._limg_pitch[0]/K[1, 1], self._limg_pitch[1]/K[0, 0]])
        oshape = np.round(np.array(self._lfp_img.shape[:2])*scales).astype('int')

        Kpts = np.diag([self._limg_pitch[0], self._limg_pitch[1], K[2, 2]])
        Kpts[0, 0] = Kpts[0, 0]*2/np.sqrt(3) if self.cfg.calibs[self.cfg.pat_type] == 'hex' else Kpts[0, 0]

        # create projective matrix of desired grid
        dims = [int(max(self._CENTROIDS[:, 2])+1), int(max(self._CENTROIDS[:, 3])+1)]
        grid = GridFitter.grid_gen(dims, pat_type=self.cfg.calibs[self.cfg.pat_type], hex_odd=self._hex_odd)
        grid = GridFitter.apply_transform(Kpts, grid)

        # shift grid
        shifts = np.zeros(2)
        cropsets = self._limg_pitch // 2
        shifts[0] = min(grid[:, 0]) - cropsets[0] if min(grid[:, 0]) - cropsets[0] < 0 else 0
        shifts[1] = min(grid[:, 1]) - cropsets[1] if min(grid[:, 1]) - cropsets[1] < 0 else 0
        grid[:, :2] = grid[:, :2] - shifts

        grxy = GridFitter(grid.copy(), flip_xy=True)
        grxy.main()
        pmat_grid = grxy.pmat.copy()
        del grxy

        # compute transfer matrix
        aff_mat = np.dot(pmat_grid, np.linalg.pinv(pmat_cent))

        # transform light-field image
        tform = transform.ProjectiveTransform(matrix=aff_mat)
        self._lfp_prj = transform.warp(self._lfp_img, tform.inverse, output_shape=oshape)

    def hexagonal_alignment(self):

        if self._lfp_prj is None or not isinstance(self._lfp_prj, np.ndarray):
            return False

        if 0 in self._limg_pitch:
            raise Exception('Micro image size cannot be zero.')

        if self.cfg.calibs[self.cfg.pat_type] == 'rec':
            self._lfp_img_align = self._lfp_prj
            return True

        dims = self._lfp_prj.shape
        lens_new_x = int(round(self._LENS_X_MAX*2/np.sqrt(3)))
        pad_zro = np.zeros([*self._limg_pitch, dims[2]])
        pad_hlf = np.zeros([self._limg_pitch[0], self._limg_pitch[1]//2, dims[2]])
        hex_switch = copy.copy(self._hex_odd)
        lnew_pitch = self._limg_pitch + np.mod(self._limg_pitch+1, 2)

        # add one in micro image size for odd
        self._lfp_img_align = np.zeros([int((self._LENS_Y_MAX-1)*(self._limg_pitch[0]+1)),
                                        int(lens_new_x*(self._limg_pitch[1]+1)),
                                        dims[2]])

        for ly in range(self._LENS_Y_MAX-1):

            # print progress status for on console
            self.sta.progress((ly+1)/self._LENS_Y_MAX*100, self.cfg.params[self.cfg.opt_prnt])

            if hex_switch == 1:
                row_a = np.hstack(
                    [pad_hlf,
                     self._lfp_prj[ly*self._limg_pitch[0]:(ly+1)*self._limg_pitch[0], :-self._limg_pitch[1]//2, :]])
                row_b = self._lfp_prj[(ly+1)*self._limg_pitch[0]:(ly+2)*self._limg_pitch[0], ...]
                row_c = np.hstack([row_a[:, self._limg_pitch[1]:, :], pad_zro])
            else:
                row_a = self._lfp_prj[ly*self._limg_pitch[0]:(ly+1)*self._limg_pitch[0], ...]
                row_b = np.hstack(
                    [pad_hlf,
                     self._lfp_prj[(ly+1)*self._limg_pitch[0]:(ly+2)*self._limg_pitch[0], :-self._limg_pitch[1]//2, :]])
                row_c = np.hstack([row_b[:, self._limg_pitch[1]:, :], pad_zro])

            row_tensor = np.concatenate([row_a[..., None], row_b[..., None], row_c[..., None]], axis=-1)
            row_interp = np.mean(row_tensor, axis=-1)

            # elongation to compensate for hexagonal aspect ratio
            row_string = self.hex_stretch(row_interp)

            # resize row for odd micro image pitch
            row_string = misc.img_resize(row_string,
                                         x_scale=lnew_pitch[1] / self._limg_pitch[1],
                                         y_scale=lnew_pitch[0] / self._limg_pitch[0])

            # place micro image row into aligned image
            self._lfp_img_align[ly*(self._limg_pitch[0]+1):(ly+1)*(self._limg_pitch[0]+1), ...] = row_string

            # flip hexagonal shift orientation every other micro lens row
            hex_switch = not hex_switch

        # re-evaluate new odd micro image size
        self._limg_pitch = lnew_pitch

        # skip first and last column of half micro images
        self._lfp_img_align = self._lfp_img_align[:, self._limg_pitch[1]//2+1:-self._limg_pitch[1]//2, :]

        return self._lfp_img_align

    def hex_stretch(self, lf_row):

        dims = lf_row.shape
        lens_new_x = int(round(self._LENS_X_MAX * 2 / np.sqrt(3)))
        interp_stack = np.zeros([dims[0], lens_new_x * self._limg_pitch[1], dims[2]])

        # image stretch interpolation in x-direction to compensate for hex-alignment
        for y in range(self._limg_pitch[0]):
            for x in range(self._limg_pitch[1]):
                lf_row_pos = lf_row[y, x::self._limg_pitch[1], :]
                for p in range(dims[2]):
                    # stack of micro images elongated in x-direction
                    interp_coords = np.linspace(0, self._LENS_X_MAX, lens_new_x)
                    interp_string = np.interp(interp_coords, range(self._LENS_X_MAX), lf_row_pos[:self._LENS_X_MAX, p])
                    interp_stack[y, x::self._limg_pitch[1], p] = interp_string

        return interp_stack
