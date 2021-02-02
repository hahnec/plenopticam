import numpy as np
from scipy.optimize import leastsq


class GridFitter(object):

    def __init__(self, *args, **kwargs):
        super(GridFitter, self).__init__()

        # use config and status if passed
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else None
        self.sta = kwargs['sta'] if 'sta' in kwargs else None

        self._grid_fit = np.array([])

        # take coordinates as input argument
        if 'coords_list' in kwargs:
            self._coords_list = np.asarray(kwargs['coords_list'])
            self._ptc_mean = np.mean(np.abs(np.diff(self._coords_list[self._coords_list[:, 2] == 0][:, 1])))
        elif self.cfg.mic_list in self.cfg.calibs:
            self._coords_list = np.asarray(self.cfg.calibs[self.cfg.mic_list])
            self._ptc_mean = self.cfg.calibs[self.cfg.ptc_mean]
        else:
            raise BaseException('Coordinate list not provided.')

        if hasattr(self, '_coords_list'):
            self._MAX_Y = int(max(self._coords_list[:, 2])+1)   # add one to compensate for index zero
            self._MAX_X = int(max(self._coords_list[:, 3])+1)   # add one to compensate for index zero
            self._pat_type = self.cfg.calibs[self.cfg.pat_type] if self.cfg.pat_type in self.cfg.calibs else 'rec'
            self._arr_shape = np.array(kwargs['arr_shape']) if 'arr_shape' in kwargs else np.array([0, 0])
            self._hex_odd = self.estimate_hex_odd() if self._pat_type == 'hex' else 0

    def main(self):

        # check for minimum grid resolution
        if self._pat_type == 'rec' and self._MAX_Y > 3 and self._MAX_X > 3 or self._MAX_Y > 5 and self._MAX_X > 5:
            self.comp_grid_fit()
        else:
            print('Skip grid fitting as grid point number is too little')
            self._grid_fit = np.array(self._coords_list)

        return True

    def comp_grid_fit(self):
        """ perform fitting for two dimensional grid coordinates """

        # print status
        self.sta.status_msg('Grid fitting', self.cfg.params[self.cfg.opt_prnt])

        # initials fit parameters
        cy_s, cx_s = self._arr_shape/2 if hasattr(self, '_arr_shape') else [0, 0]
        sy_s, sx_s = [self._ptc_mean]*2 if hasattr(self, '_ptc_mean') else [1, 1]
        theta = 0

        # LMA fit: executes least-squares regression analysis to optimize initial parameters
        coeffs, _ = leastsq(self.obj_fun, [cy_s, cx_s, sy_s, sx_s, theta], args=(self._coords_list),
                            )#maxfev=5000, xtol=1e-19, gtol=1e-19, ftol=1e-19)
        print(coeffs)
        # obtain fitted grid
        self._grid_fit = self.adjust_grid(coeffs[0], coeffs[1], coeffs[2], coeffs[3], coeffs[4])

        return np.array(self._grid_fit)

    def obj_fun(self, p, centroids):

        grid = self.adjust_grid(p[0], p[1], p[2], p[3], p[4])
        if np.sum(centroids[:, 2:] - grid[:, 2:]) == 0:
            sqr_loss = np.sum((centroids[:, :2] - grid[:, :2]) ** 2, axis=1)
        else:
            err_msg = 'Grid fitting index mismatch'
            if self.sta is None:
                raise Exception(err_msg)
            else:
                self.sta.status_msg(err_msg, True)
                self.sta.error = True
                return False

        return sqr_loss

    def adjust_grid(self, cy=0, cx=0, sy=1, sx=1, theta=0):

        # generate
        grid = self.grid_gen()

        # scale
        grid[:, 0] *= sy
        grid[:, 1] *= sx

        # rotate
        grid = self.rotate_grid(grid=grid, rota_rad=theta)

        # translate
        grid[:, :2] += np.array([cy, cx])

        return grid

    def grid_gen(self):
        """ generate grid of points """

        if self._pat_type == 'rec' or self._pat_type == 'hex':

            # create point coordinates
            y_range = np.linspace(0, 1, self._MAX_Y)
            x_range = np.linspace(0, 1, self._MAX_X)
            y_grid, x_grid = np.meshgrid(y_range, x_range)

            # create point index labels
            y_idcs, x_idcs = np.meshgrid(np.linspace(0, self._MAX_Y-1, self._MAX_Y),
                                         np.linspace(0, self._MAX_X-1, self._MAX_X))

            # shift rows horizontally if grid is hexagonal
            if self._pat_type == 'hex':
                # vertical shrinkage
                y_grid *= np.sqrt(3) / 2
                # horizontal hex shifting
                x_grid[:, int(self._hex_odd)::2] += .5/(self._MAX_X-1)

            if True:
                # normalize grid to max-length 1
                norm_div = max(x_grid.max(), y_grid.max())
                y_grid /= norm_div
                x_grid /= norm_div

                # put grid to origin
                y_grid -= y_grid.max()/2
                x_grid -= x_grid.max()/2

            pts_arr = np.vstack(np.dstack([y_grid.T, x_grid.T, y_idcs.T, x_idcs.T]))

        else:
            err_msg = 'Grid pattern type not recognized.'
            if self.sta is None:
                raise Exception(err_msg)
            else:
                self.sta.status_msg(err_msg, True)
                self.sta.error = True
                return False

        if True:
            p = pts_arr[(pts_arr[:, 2] == 3) & (pts_arr[:, 3] == 3)]
            # same row
            n2 = pts_arr[(pts_arr[:, 2] == 3) & (pts_arr[:, 3] == 2)]
            n3 = pts_arr[(pts_arr[:, 2] == 3) & (pts_arr[:, 3] == 4)]
            # same column
            n1 = pts_arr[(pts_arr[:, 2] == 4) & (pts_arr[:, 3] == 3)]
            n4 = pts_arr[(pts_arr[:, 2] == 2) & (pts_arr[:, 3] == 3)]
            # different row and column
            n5 = pts_arr[(pts_arr[:, 2] == 2) & (pts_arr[:, 3] == 2)]
            n6 = pts_arr[(pts_arr[:, 2] == 2) & (pts_arr[:, 3] == 4)]

        return pts_arr

    def estimate_hex_odd(self):

        # take the most upper two points in hexagonal grid
        pt_00 = self._coords_list[(self._coords_list[:, 2] == 0) & (self._coords_list[:, 3] == 0)][0]
        pt_10 = self._coords_list[(self._coords_list[:, 2] == 1) & (self._coords_list[:, 3] == 0)][0]

        # compare x-coordinates to determine the direction of heaxgonal shift alternation
        hex_odd = 1 if pt_00[1] < pt_10[1] else 0

        return hex_odd

    @staticmethod
    def rotate_grid(grid, rota_rad=0):
        """ transformation of centroids via translation and rotation """

        # matrix for counter-clockwise rotation around z-axis
        Rz = np.array([[np.cos(rota_rad), -np.sin(rota_rad)], [np.sin(rota_rad), np.cos(rota_rad)]])
        # Rz = np.array([[np.cos(self._rad), np.sin(self._rad)], [-np.sin(self._rad), np.cos(self._rad)]]) #clock-wise

        # rotate data points around z-axis
        grid[:, :2] = np.dot(Rz, grid[:, :2].T).T

        return grid

    @property
    def grid_fit(self):

        # convert array indices to integer
        self._grid_fit[:, 2] = self._grid_fit[:, 2].astype('int')
        self._grid_fit[:, 3] = self._grid_fit[:, 3].astype('int')

        return self._grid_fit.tolist()
