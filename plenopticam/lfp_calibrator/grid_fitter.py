import numpy as np


class GridFitter(object):

    def __init__(self, *args, **kwargs):
        super(GridFitter, self).__init__()

        # use config and status if passed
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else None
        self.sta = kwargs['sta'] if 'sta' in kwargs else None

        self._grid_fit = list()

        # take coordinates as input argument
        if 'coords_list' in kwargs:
            self._coords_list = np.asarray(kwargs['coords_list'])
        elif self.cfg.mic_list in self.cfg.calibs:
            self._coords_list = np.asarray(self.cfg.calibs[self.cfg.mic_list])
        else:
            raise BaseException('Coordinate list not provided.')

        if hasattr(self, '_coords_list'):
            self._MAX_Y = int(max(self._coords_list[:, 2])+1)   # add one to compensate for index zero
            self._MAX_X = int(max(self._coords_list[:, 3])+1)   # add one to compensate for index zero
            self._pat_type = self.cfg.calibs[self.cfg.pat_type] if self.cfg.pat_type in self.cfg.calibs else 'rec'

    def main(self, deg=1):

        #
        if self._pat_type == 'rec' and self._MAX_Y > 3 and self._MAX_X > 3 or self._MAX_Y > 5 and self._MAX_X > 5:
            self.comp_grid_fit(deg=deg)
        else:
            print('Skip grid fitting as number of micro lens number too little')
            self._grid_fit = np.array(self._coords_list)

        return True

    def comp_grid_fit(self, deg=1):
        """ perform fitting for two dimensional grid coordinates """

        # print status
        self.sta.status_msg('Grid fitting', self.cfg.params[self.cfg.opt_prnt])

        odd = 0     # hexagonal shift direction

        # iterate through rows
        for ly in range(self._MAX_Y):

            # check interrupt status
            if self.sta.interrupt:
                return False

            # fit line of all coordinates in current row
            coords_row = self._coords_list[self._coords_list[:, 2] == ly][:, :2]
            coeffs_hor = self.line_fitter(coords_row, axis=1, deg=deg)

            # iterate through column
            for lx in range(self._MAX_X):

                # select coordinates
                coords_col = self._coords_list[self._coords_list[:, 3] == lx][:, :2]

                # consider hexagonal pattern
                if self._pat_type == 'hex':
                    # fit line of current column coordinates (omit every other coordinate pair)
                    coeffs_ver = self.line_fitter(coords_col[odd::2], axis=1, deg=deg)

                else:
                    # fit line of current column coordinates
                    coeffs_ver = self.line_fitter(coords_col, axis=1, deg=deg)

                # compute intersection of row and column line
                new_coords = list(self.line_intersect(coeffs_hor, coeffs_ver))

                # original reference coordinate
                ref_coords = self._coords_list[(self._coords_list[:, 2] == ly) & (self._coords_list[:, 3] == lx)]

                # put result to new coordinate list (if reference exists)
                self._grid_fit.append(new_coords + [ly, lx]) if ref_coords.size != 0 else None

            # switch hexagonal shift direction
            odd = not odd if self._pat_type == 'hex' else odd

            # print progress status
            percentage = (ly + 1) / self._MAX_Y * 100
            self.sta.progress(percentage, opt=self.cfg.params[self.cfg.opt_prnt]) if self.sta else None

        self._grid_fit = np.array(self._grid_fit)

        return self._grid_fit

    @staticmethod
    def line_intersect(coeffs_hor, coeffs_ver):
        """ compute line intersection based on Vandermonde algebra """

        deg = len(coeffs_hor)-1 if len(coeffs_hor) == len(coeffs_ver) else 0

        if deg < 3:
            # intersection of linear functions
            matrix = np.array([[1, *-coeffs_hor[1:]], [1, *-coeffs_ver[1:]]])
            vector = np.array([coeffs_hor[0], coeffs_ver[0]])
        else:
            # intersection of non-linear functions
            raise BaseException('Function with degree %s is not supported' % deg)

        return np.dot(np.linalg.pinv(matrix), vector)

    def line_fitter(self, coords, axis=0, deg=1):
        """ estimate equation fit of 2-D coordinates belonging to the same row or column via least squares method """

        # feed into system of equations
        A = self.compose_vandermonde_1d(coords[:, axis], deg=deg)
        b = coords[:, 1-axis]

        # solve for a least squares estimate via pseudo inverse and coefficients in b
        coeffs = np.dot(np.linalg.pinv(A), b)

        return coeffs

    @staticmethod
    def compose_vandermonde_1d(x, deg=1):
        if deg == 1:
            return np.array([np.ones(len(x)), x]).T
        elif deg == 2:
            return np.array([np.ones(len(x)), x, x ** 2]).T
        elif deg == 3:
            return np.array([np.ones(len(x)), x, x ** 2, x ** 3]).T

    @property
    def grid_fit(self):

        # convert array indices to integer
        self._grid_fit[:, 2] = self._grid_fit[:, 2].astype('int')
        self._grid_fit[:, 3] = self._grid_fit[:, 3].astype('int')

        return self._grid_fit.tolist()
