import numpy as np
from scipy.optimize import leastsq
import warnings

l2_norm = lambda c_meas, c_grid: np.sqrt(np.sum((c_meas - c_grid)**2, axis=1))
l1_norm = lambda c_meas, c_grid: np.sum(np.abs(c_meas - c_grid), axis=1)


class GridFitter(object):

    def __init__(self, *args, **kwargs):
        super(GridFitter, self).__init__()

        # use config and status if passed
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else None
        self.sta = kwargs['sta'] if 'sta' in kwargs else None

        # internal variables
        self._grid_fit = np.array([])
        self._pat_type = kwargs['pat_type'] if 'pat_type' in kwargs else 'rec'
        self._ptc_mean = kwargs['ptc_mean'] if 'ptc_mean' in kwargs else [1, 1]
        self._hex_odd = kwargs['hex_odd'] if 'hex_odd' in kwargs else 0
        self._arr_shape = np.array(kwargs['arr_shape'])[:2] if 'arr_shape' in kwargs else np.array([0, 0])

        # regression settings
        self.penalty_enable = kwargs['penalty_enable'] if 'penalty_enable' in kwargs else False

        # take coordinates as input argument
        if 'cfg' in kwargs and self.cfg.mic_list in self.cfg.calibs:
            self._coords_list = np.asarray(self.cfg.calibs[self.cfg.mic_list])
            self._pat_type = self.cfg.calibs[self.cfg.pat_type] if self.cfg.pat_type in self.cfg.calibs else 'rec'
            self._ptc_mean = self.cfg.calibs[self.cfg.ptc_mean] if self.cfg.ptc_mean in self.cfg.calibs else [1, 1]
            self._hex_odd = self.estimate_hex_odd(self._coords_list) if self._pat_type == 'hex' else self._hex_odd
        if 'coords_list' in kwargs:
            self._coords_list = np.asarray(kwargs['coords_list'])
            if self._coords_list.shape[1] == 4:
                self._ptc_mean = np.mean(np.abs(np.diff(self._coords_list[self._coords_list[:, 2] == 0][:, 1])))

        if hasattr(self, '_coords_list'):
            self._MAX_Y = int(max(self._coords_list[:, 2])+1)   # add one to compensate for index zero
            self._MAX_X = int(max(self._coords_list[:, 3])+1)   # add one to compensate for index zero

    def main(self):

        # check for minimum grid resolution
        if self._MAX_Y > 3 and self._MAX_X > 3 or self._MAX_Y > 5 and self._MAX_X > 5:
            self.comp_grid_fit()
        else:
            print('Skip grid fitting as grid point number is too little')
            self._grid_fit = np.array(self._coords_list)

        if hasattr(self, 'cfg') and hasattr(self.cfg, 'calibs'):
            self.cfg.calibs[self.cfg.mic_list] = self._grid_fit

        return True

    def comp_grid_fit(self):
        """ perform fitting for two dimensional grid coordinates """

        # print status
        self.sta.status_msg('Grid fitting', self.cfg.params[self.cfg.opt_prnt]) if self.sta else None

        # initial fit parameters
        cy_s, cx_s = self._arr_shape/2 if hasattr(self, '_arr_shape') else [0, 0]
        sy_s, sx_s = [self._ptc_mean]*2 if hasattr(self, '_ptc_mean') else [1, 1]
        p_init = np.diag([sy_s, sx_s, 0])
        p_init[:2, -1] = np.array([cy_s, cx_s])
        beta = 1 if self.penalty_enable else 0

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')

            # LMA fit: executes least-squares regression analysis to optimize initial parameters
            coeffs, _ = leastsq(self.obj_fun, p_init, args=(self._coords_list, beta))

        # generate normalized grid
        grid_norm = self.grid_gen(dims=[self._MAX_Y, self._MAX_X], pat_type=self._pat_type, hex_odd=self._hex_odd)

        # project grid from final estimates
        self._grid_fit = self.projective_transform(coeffs, grid_norm)

        # print status
        self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt]) if self.sta else None

        return np.array(self._grid_fit)

    def obj_fun(self, p, centroids, beta=0):

        # generate grid points
        grid_norm = self.grid_gen(dims=[self._MAX_Y, self._MAX_X], pat_type=self._pat_type, hex_odd=self._hex_odd)

        # transform grid points
        grid = self.projective_transform(p, grid_norm)

        # compute loss
        try:
            loss = l2_norm(centroids[:, :2], grid[:, :2])
            loss += beta * self._regularizer(centroids.copy(), grid) if beta > 0 else 0
        except ValueError:
            err_msg = 'Grid index mismatch'
            if self.sta is None:
                raise Exception(err_msg)
            else:
                self.sta.status_msg(err_msg, True)
                self.sta.error = True
                return False

        return loss

    @staticmethod
    def projective_transform(p, grid: np.ndarray, compose: bool = False, affine: bool = False):
        """ projective transformation """

        if compose:
            # compose parameters to set scale, rotation and translation in projective matrix
            sim_mat = np.array([[np.cos(-p[1]), -np.sin(-p[1]), 0], [np.sin(-p[1]), np.cos(-p[1]), 0], [0, 0, 1]])
            scl_mat = np.array([[p[0], 0, p[2]], [0, p[4], p[5]], [p[6], p[7], 1]])
            prj_mat = np.dot(sim_mat, scl_mat)
        else:
            # reshape vector to 3x3 matrix
            prj_mat = np.array(p).reshape(3, 3)

        # affine transformation constraint
        prj_mat[-1, :] = np.array([0, 0, 1]) if affine else np.array([*prj_mat[-1, :2], 1])

        # form points matrix adding vector of ones
        pts = np.concatenate((grid[:, :2].T, np.ones(len(grid))[np.newaxis, :]), axis=0)

        # transform points
        prj = np.dot(prj_mat, pts)

        # project z values (if available)
        grid[:, :2] = np.divide(prj[:2, :], prj[2, :], out=np.zeros(prj[:2, :].shape), where=prj[2, :] != 0).T[:, :2]

        return grid

    @staticmethod
    def _regularizer(c_meas, c_grid, sig_div=22):

        assert c_meas.shape[-1] == 4, 'Regularizer requires 4 columns in the list'

        dim = int(np.max(c_meas[:, 3]))
        pitch = np.mean(np.diff(c_meas[:dim, 1]))

        c_meas[:, 0] -= np.mean(c_meas[:, 0])
        c_meas[:, 1] -= np.mean(c_meas[:, 1])
        c_grid[:, 0] -= np.mean(c_grid[:, 0])
        c_grid[:, 1] -= np.mean(c_grid[:, 1])

        diff = np.abs(c_meas) - np.abs(c_grid)

        # penalty boundary is further pushed by additional fraction
        diff += pitch / sig_div

        diff[:, 0][diff[:, 0] < 0] = 0
        diff[:, 1][diff[:, 1] < 0] = 0
        diff = np.sum(diff, axis=1)

        return diff

    @staticmethod
    def grid_gen(dims: [int, int] = None, pat_type: str = None, hex_odd: bool = None, normalize: bool = False):
        """ generate grid of points """

        assert pat_type == 'rec' or pat_type == 'hex', 'Grid pattern type not recognized.'

        # create point coordinates
        y_range = np.linspace(0, dims[0]-1, dims[0])
        x_range = np.linspace(0, dims[1]-1, dims[1])
        y_grid, x_grid = np.meshgrid(y_range, x_range)

        # create point index labels
        y_idcs, x_idcs = np.meshgrid(np.linspace(0, dims[0]-1, dims[0]),
                                     np.linspace(0, dims[1]-1, dims[1]))

        # shift rows horizontally if grid is hexagonal
        if pat_type == 'hex':
            # vertical shrinkage
            y_grid *= np.sqrt(3) / 2
            # horizontal hex shifting
            x_grid[:, int(hex_odd)::2] += .5/(dims[1]-1)

        # normalize grid to max-length 1 (pixel unit w/o normalization)
        if normalize:
            norm_div = max(x_grid.max(), y_grid.max())
            y_grid /= norm_div
            x_grid /= norm_div

        # put grid to origin
        y_grid -= y_grid.max()/2
        x_grid -= x_grid.max()/2

        pts_arr = np.vstack(np.dstack([y_grid.T, x_grid.T, y_idcs.T, x_idcs.T]))

        return pts_arr

    @staticmethod
    def estimate_hex_odd(coords_list):

        # find smallest lens indices (more robust than finding lens index zero)
        min_idx_y, min_idx_x = min(coords_list[:, 2]), min(coords_list[:, 3])

        # take the most upper two points in hexagonal grid
        pt_00 = coords_list[(coords_list[:, 3] == min_idx_x) & (coords_list[:, 2] == min_idx_y)][0]
        pt_10 = coords_list[(coords_list[:, 3] == min_idx_x) & (coords_list[:, 2] == min_idx_y + 1)][0]

        # compare x-coordinates to determine the direction of heaxgonal shift alternation
        hex_odd = 1 if pt_00[1] < pt_10[1] else 0

        return hex_odd

    @staticmethod
    def rotate_grid(grid, rota_rad=0):
        """ transformation of centroids via translation and rotation """

        # matrix for counter-clockwise rotation around z-axis
        rota_mat_z = np.array([[np.cos(rota_rad), -np.sin(rota_rad)], [np.sin(rota_rad), np.cos(rota_rad)]])

        # rotate data points around z-axis
        grid[:, :2] = np.dot(rota_mat_z, grid[:, :2].T).T

        return grid

    @staticmethod
    def decompose_mat(mat, scale=True):
        """

        https://www.robots.ox.ac.uk/~vgg/hzbook/code/vgg_multiview/vgg_KR_from_P.m

        """

        n = mat.shape[0] if len(mat.shape) == 2 else np.sqrt(mat.size)
        K, R = np.linalg.qr(mat.reshape(n, -1))

        if scale:
            K = K / K[n-1, n-1]
            if K[0, 0] < 0:
                D = np.diag([-1, -1, *np.ones(n-2)])
                K = np.dot(K, D)
                R = np.dot(D, R)

        t = -1*np.linalg.lstsq(mat[:, :n], mat[:, -1]) if len(mat.shape) == 2 and mat.shape[1] == 4 else np.zeros(n)

        return K, R, t

    @property
    def grid_fit(self):

        # convert array indices to integer
        self._grid_fit[:, 2] = self._grid_fit[:, 2].astype('int')
        self._grid_fit[:, 3] = self._grid_fit[:, 3].astype('int')

        return self._grid_fit.tolist()
