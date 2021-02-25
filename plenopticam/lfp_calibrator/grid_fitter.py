import numpy as np
from scipy.optimize import leastsq


class GridFitter(object):

    def __init__(self, *args, **kwargs):
        super(GridFitter, self).__init__()

        # use config and status if passed
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else None
        self.sta = kwargs['sta'] if 'sta' in kwargs else None

        self._grid_fit = np.array([])
        self._sub_fit_opt = False

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
            self._hex_odd = self.estimate_hex_odd(self._coords_list) if self._pat_type == 'hex' else 0
            self._coords_parx = list()

    def main(self):

        # check for minimum grid resolution
        elif self._pat_type == 'rec' and self._MAX_Y > 3 and self._MAX_X > 3 or self._MAX_Y > 5 and self._MAX_X > 5:
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

        # initials fit parameters
        cy_s, cx_s = self._arr_shape/2 if hasattr(self, '_arr_shape') else [0, 0]
        sy_s, sx_s = [self._ptc_mean]*2 if hasattr(self, '_ptc_mean') else [1, 1]
        theta = 0

        # LMA fit: executes least-squares regression analysis to optimize initial parameters
        coeffs, _ = leastsq(self.obj_fun, [cy_s, cx_s, sy_s, sx_s, theta], args=(self._coords_list))

        # obtain fitted grid from final estimates
        self._grid_fit = self.adjust_grid(coeffs[0], coeffs[1], coeffs[2], coeffs[3], coeffs[4])

        # print status
        self.sta.progress(100, opt=self.cfg.params[self.cfg.opt_prnt]) if self.sta else None

        return np.array(self._grid_fit)

    def obj_fun(self, p, centroids):

        grid = self.adjust_grid(cy=p[0], cx=p[1], sy=p[2], sx=p[3], theta=p[4])
        try:
            sqr_loss = np.sum((centroids[:, :2] - grid[:, :2]) ** 2, axis=1)
        except ValueError:
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
