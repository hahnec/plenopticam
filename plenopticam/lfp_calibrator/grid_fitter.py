import numpy as np
from scipy.optimize import leastsq, least_squares
from typing import Union

l2_norm_eucl = lambda c_meas, c_grid: np.sqrt(np.sum((c_meas - c_grid) ** 2, axis=1))
l1_norm_eucl = lambda c_meas, c_grid: np.sum(np.abs(c_meas - c_grid), axis=1)
l2_norm_elem = lambda c_meas, c_grid: np.square(c_meas - c_grid)
l1_norm_elem = lambda c_meas, c_grid: np.abs(c_meas - c_grid)


class GridFitter(object):

    def __init__(self, *args, **kwargs):
        super(GridFitter, self).__init__()

        # use config and status if passed
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else None
        self.sta = kwargs['sta'] if 'sta' in kwargs else None

        # internal variables
        self._grid_fit = np.array([])
        self._coeffs = np.identity(3).flatten()
        self._pat_type = kwargs['pat_type'] if 'pat_type' in kwargs else 'rec'
        self._ptc_mean = kwargs['ptc_mean'] if 'ptc_mean' in kwargs else np.array([1, 1])
        self._hex_odd = kwargs['hex_odd'] if 'hex_odd' in kwargs else 0
        self._arr_shape = np.array(kwargs['arr_shape'])[:2] if 'arr_shape' in kwargs else np.array([0, 0])
        self._affine = kwargs['affine'] if 'affine' in kwargs else False
        self._compose = kwargs['compose'] if 'compose' in kwargs else False
        self._flip_yx = kwargs['flip_xy'] if 'flip_xy' in kwargs else False
        self._normalize = kwargs['normalize'] if 'normalize' in kwargs else False
        self.z_dist = kwargs['z_dist'] if 'z_dist' in kwargs else 1.0

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
        elif len(args) > 0:
            self._coords_list = np.asarray(args[0])

        if hasattr(self, '_coords_list'):
            self._MAX_Y = int(max(self._coords_list[:, 2])+1)   # add one to compensate for index zero
            self._MAX_X = int(max(self._coords_list[:, 3])+1)   # add one to compensate for index zero
        else:
            self._MAX_Y, self._MAX_X = 2, 2

        self._ptc_mean = [self._ptc_mean]*2 if isinstance(self._ptc_mean, (int, float, np.float64)) else self._ptc_mean

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

    def coeff_fit(self, coords_list=None, euclid_opt=True):
        """ perform two dimensional grid regression """

        self._coords_list = coords_list if coords_list is not None else self._coords_list

        # initial fit parameters
        cy_s, cx_s = self._arr_shape/2 if hasattr(self, '_arr_shape') else [0, 0]
        sy_s, sx_s = self._ptc_mean if hasattr(self, '_ptc_mean') else [1, 1]
        p_init = np.diag([sy_s, sx_s, 1])
        p_init[:2, -1] = np.array([cy_s, cx_s])
        p_init = p_init.flatten()[:8]
        beta = 1 if self.penalty_enable else 0

        # LMA fit: executes least-squares regression for optimization of initial parameters
        try:
            self._coeffs = leastsq(self.cost_fun, p_init, args=(self._coords_list, beta, euclid_opt))[0]
        except:
            # newer interface for LMA
            self._coeffs = least_squares(self.cost_fun, p_init.flatten(),
                                            jac='2-point', args=(self._coords_list, beta, euclid_opt), method='lm').x

    def comp_grid_fit(self):
        """ perform two dimensional grid regression and return fitted grid """

        # print status
        self.sta.status_msg('Grid fitting', self.cfg.params[self.cfg.opt_prnt]) if self.sta else None

        # perform the grid regression
        self.coeff_fit()

        # generate initial grid
        grid_init = self.grid_gen(dims=[self._MAX_Y, self._MAX_X],
                                  pat_type=self._pat_type,
                                  hex_odd=self._hex_odd,
                                  normalize=self._normalize
                                  )

        # project grid from final estimates
        self._grid_fit = self.apply_transform(self._coeffs, grid_init, self._affine, self._flip_yx, self.z_dist)

        # print status
        self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt]) if self.sta else None

        return np.array(self._grid_fit)

    def cost_fun(self, p, centroids, beta=0, euclid_opt=True):

        # generate grid points
        grid_pts = self.grid_gen(dims=[self._MAX_Y, self._MAX_X],
                                 pat_type=self._pat_type,
                                 hex_odd=self._hex_odd,
                                 normalize=self._normalize
                                 )

        # generate projection parameters
        p = self.compose_p(p) if self._compose else p

        # transform grid points
        grid = self.apply_transform(p, grid_pts, self._affine, self._flip_yx, self.z_dist)

        # choose euclidian or element-wise norm (the latter yields twice as many points)
        norm_fun = l2_norm_eucl if euclid_opt else l2_norm_elem

        # mask non-existing points
        idxs = np.ones(grid.shape[0], dtype='bool')
        if centroids.shape[0] != grid.shape[0]:
            # 4 corner fitting
            if centroids.shape[0] == 4:
                idxs = np.where((grid[:, 2] == 0) & (grid[:, 3] == 0) |
                                (grid[:, 2] == 0) & (grid[:, 3] == self._MAX_X-1) |
                                (grid[:, 2] == self._MAX_Y-1) & (grid[:, 3] == 0) |
                                (grid[:, 2] == self._MAX_Y-1) & (grid[:, 3] == self._MAX_X-1)
                                )

        # compute loss
        try:
            loss = norm_fun(centroids[:, :2], grid[:, :2][idxs])
            loss += beta * self._regularizer(centroids.copy(), grid) if beta > 0 else 0
        except ValueError:
            err_msg = 'Grid index mismatch'
            if self.sta is None:
                raise Exception(err_msg)
            else:
                self.sta.status_msg(err_msg, True)
                self.sta.error = True
                return False

        return loss.flatten()
    
    @staticmethod
    def apply_transform(p, grid: np.ndarray, affine: bool = False, flip_xy: bool = False, z_dist: float = 1.):
        """ transformation """

        # append 1 to 8 DOF vector
        p = np.array([*p, 1]) if len(p) == 8 else np.array(p)

        # reshape vector to 3x3 matrix
        pmat = p.reshape(3, 3) if len(p) == 9 else p

        # transformation constraint
        pmat[-1, :] = np.array([0, 0, 1]) if affine else np.array([*pmat[-1, :2], 1])

        # form points matrix adding vector of ones
        pts = np.concatenate((grid[:, :2].T, z_dist*np.ones(len(grid))[np.newaxis, :]), axis=0)

        # flip x and y coordinates
        pts[:2, :] = pts[:2, :][::-1] if flip_xy else pts[:2, :]

        # transform points
        prj = np.dot(pmat, pts)

        # flip y and x coordinates
        prj[:2, :] = prj[:2, :][::-1] if flip_xy else prj[:2, :]

        # project z values (if available)
        grid[:, :2] = np.divide(prj[:2, :], prj[2, :], out=np.zeros(prj[:2, :].shape), where=prj[2, :] != 0).T[:, :2]

        return grid

    @staticmethod
    def _regularizer(c_meas, c_grid, div=22):

        assert c_meas.shape[-1] == 4, 'Regularizer requires 4 columns in the list'

        dim = int(np.max(c_meas[:, 3]))
        pitch = np.mean(np.diff(c_meas[:dim, 1]))

        c_meas[:, 0] -= np.mean(c_meas[:, 0])
        c_meas[:, 1] -= np.mean(c_meas[:, 1])
        c_grid[:, 0] -= np.mean(c_grid[:, 0])
        c_grid[:, 1] -= np.mean(c_grid[:, 1])

        diff = np.abs(c_meas) - np.abs(c_grid)

        # penalty boundary is further pushed by additional fraction
        diff += pitch / div

        diff[:, 0][diff[:, 0] < 0] = 0
        diff[:, 1][diff[:, 1] < 0] = 0
        diff = np.sum(diff, axis=1)

        return diff

    @staticmethod
    def grid_gen(dims: Union[int, int] = None, pat_type: str = None, hex_odd: bool = None, normalize: int = 0):
        """ generate grid of points """

        # set default values
        dims = [5, 5] if dims is None else dims
        pat_type = 'rec' if pat_type is None else pat_type
        hex_odd = 0 if hex_odd is None else hex_odd

        assert pat_type == 'rec' or pat_type == 'hex' or pat_type == 'pseudo-hex', 'Grid pattern type not recognized.'

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
            x_grid[:, int(hex_odd)::2] += .5
        elif pat_type == 'pseudo-hex':
            # horizontal hex shifting
            x_grid[:, int(hex_odd)::2] += .5

        # normalize grid
        if normalize > 0:
            norm_div = (max(x_grid.max(), y_grid.max()),)*2 if normalize == 1 else (x_grid.max(), y_grid.max())
            y_grid, x_grid = y_grid / norm_div[0], x_grid / norm_div[1]

        # put grid to origin
        y_grid -= y_grid.max()/2
        x_grid -= x_grid.max()/2

        pts_arr = np.vstack(np.dstack([y_grid.T, x_grid.T, y_idcs.T, x_idcs.T]))

        return pts_arr

    @staticmethod
    def compose_p(p):

        p = p.flatten()
        rmat = GridFitter.euler2mat(theta_x=p[7], theta_y=p[6], theta_z=p[3])
        kmat = np.diag([p[0], p[4], 1])
        kmat[:2, -1] = np.array([p[2], p[5]])
        p = np.dot(rmat, kmat).flatten()

        return p

    @staticmethod
    def estimate_hex_odd(coords_list):

        # find smallest lens indices (more robust than finding lens index zero)
        min_idx_y, min_idx_x = min(coords_list[:, 2]), min(coords_list[:, 3])

        # take the most upper two points in hexagonal grid
        pt_00 = coords_list[(coords_list[:, 3] == min_idx_x) & (coords_list[:, 2] == min_idx_y)][0]
        pt_10 = coords_list[(coords_list[:, 3] == min_idx_x) & (coords_list[:, 2] == min_idx_y + 1)][0]

        # compare x-coordinates to determine the direction of hexagonal shift alternation
        hex_odd = 1 if pt_00[1] < pt_10[1] else 0

        return hex_odd

    @staticmethod
    def euler2mat(theta_x: float = 0, theta_y: float = 0, theta_z: float = 0):
        """
        Creation of a rotation matrix from three angles in radians
        """

        # matrix for counter-clockwise rotation around x-y-z axes
        rmat_z = np.array([[np.cos(theta_z), -np.sin(theta_z), 0],
                           [np.sin(theta_z), np.cos(theta_z), 0],
                           [0, 0, 1]]
                          )

        rmat_y = np.array([[np.cos(theta_y), 0, np.sin(theta_y)],
                           [0, 1, 0],
                           [-np.sin(theta_y), 0, np.cos(theta_y)]]
                          )

        rmat_x = np.array([[1, 0, 0],
                           [0, np.cos(theta_x), -np.sin(theta_x)],
                           [0, np.sin(theta_x), np.cos(theta_x)]]
                          )

        rmat_3 = np.dot(np.dot(rmat_x, rmat_y), rmat_z)

        return rmat_3

    @staticmethod
    def decompose(pmat, scale=True):
        """
        https://www.robots.ox.ac.uk/~vgg/hzbook/code/vgg_multiview/vgg_KR_from_P.m
        """

        # reshape potential vector to 3x3 matrix
        pmat = np.array(pmat).reshape(3, 3) if len(pmat.shape) == 1 and np.array(pmat).size == 9 else pmat

        n = pmat.shape[0] if len(pmat.shape) == 2 else np.sqrt(pmat.size)
        rmat, kmat = np.linalg.qr(pmat.reshape(n, -1), mode='reduced')

        if scale:
            kmat = kmat / kmat[n-1, n-1]
            if kmat[0, 0] < 0:
                D = np.diag([-1, -1, *np.ones(n-2)])
                kmat = np.dot(D, kmat)
                rmat = np.dot(rmat, D)

        tvec = -1*np.linalg.lstsq(pmat[:, :n], pmat[:, -1]) if pmat.shape[1] == 4 else np.zeros(n)

        return rmat, kmat, tvec

    @staticmethod
    def mat2euler(rmat):
        """
        https://www.geometrictools.com/Documentation/EulerAngles.pdf
        """

        if rmat[0, 2] < 1:
            if rmat[0, 2] > -1:
                theta_y = np.arcsin(rmat[0, 2])
                theta_x = np.arctan2(-rmat[1, 2], rmat[2, 2])
                theta_z = np.arctan2(-rmat[0, 1], rmat[0, 0])
            else:
                theta_y = -np.pi / 2
                theta_x = -np.arctan2(rmat[1, 0], rmat[1, 1])
                theta_z = 0
        else:
            theta_y = np.pi / 2
            theta_x = np.arctan2(rmat[1, 0], rmat[1, 1])
            theta_z = 0

        return np.array([theta_x, theta_y, theta_z])

    @property
    def grid_fit(self):

        # convert array indices to integer
        self._grid_fit[:, 2] = self._grid_fit[:, 2].astype('int')
        self._grid_fit[:, 3] = self._grid_fit[:, 3].astype('int')

        return self._grid_fit.tolist()

    @property
    def pmat(self):
        self._coeffs = np.array([*self._coeffs, 1]) if len(self._coeffs) == 8 else self._coeffs
        if self._compose:
            return self.compose_p(self._coeffs).reshape(3, 3)
        else:
            return self._coeffs.reshape(3, 3)

    @pmat.setter
    def pmat(self, pmat: np.ndarray):
        if pmat.size == 9:
            self._coeffs = pmat.flatten()
        else:
            raise Exception('Only a 9-vector or 3x3 matrix is accepted')

    @property
    def rmat(self):
        return self.decompose(self.pmat)[0]

    @property
    def kmat(self):
        return self.decompose(self.pmat)[1]

    @property
    def tvec(self):
        return self.decompose(self.pmat)[2]
