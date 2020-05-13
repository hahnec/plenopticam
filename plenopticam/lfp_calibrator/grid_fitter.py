import numpy as np

from plenopticam.lfp_aligner.lfp_microlenses import LfpMicroLenses


class GridFitter(object):

    def __init__(self, *args, **kwargs):
        super(GridFitter, self).__init__()  #*args, **kwargs

        # use config and status if passed
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else None
        self.sta = kwargs['sta'] if 'sta' in kwargs else None

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
            self._grid_fit = self._coords_list.copy()
            self._pat_type = self.cfg.calibs[self.cfg.pat_type] if self.cfg.pat_type in self.cfg.calibs else 'rec'

    def main(self):

        self.comp_grid_fit(deg=1)

        return True

    def comp_grid_fit(self, deg=1):
        """ perform fitting for two dimensional grid coordinates """

        # print status
        self.sta.status_msg('Grid fitting', self.cfg.params[self.cfg.opt_prnt])

        # coordinate list index
        i = 0

        # hexagonal shift direction
        odd = LfpMicroLenses.get_hex_direction(centroids=self._coords_list) if self._pat_type == 'hex' else 0

        # iterate through rows
        for ly in range(self._MAX_Y):

            # check interrupt status
            if self.sta.interrupt:
                return False

            # fit line of all coordinates in current row
            coords_row = self._coords_list[self._coords_list[:, 2] == ly]
            coeffs_hor = self.line_fitter(coords_row, deg=deg)

            # iterate through column
            for lx in range(self._MAX_X):

                # select coordinates
                coords_col = self._coords_list[self._coords_list[:, 3] == lx]

                # consider hexagonal pattern
                if self._pat_type == 'hex':

                    # fit line of current column coordinates (omit every other coordinate pair)
                    coeffs_ver = self.line_fitter(coords_col[odd::2], deg=deg)

                else:
                    # fit line of current column coordinates
                    coeffs_ver = self.line_fitter(coords_col, deg=deg)

                # compute intersection of row and column line and put result to new coordinate list
                self._grid_fit[i][:2] = self.line_intersect(coeffs_hor, coeffs_ver)
                i += 1

            # switch hexagonal shift direction
            odd = not odd if self._pat_type == 'hex' else odd

            # print progress status
            percentage = (ly + 1) / self._MAX_Y * 100
            self.sta.progress(percentage, opt=self.cfg.params[self.cfg.opt_prnt]) if self.sta else None

        return self._grid_fit

    def line_intersect(self, coeffs_hor, coeffs_ver):
        """ compute line intersection based on Vandermonde algebra """

        deg = len(coeffs_hor)-1 if len(coeffs_hor) == len(coeffs_ver) else 0

        if deg == 1:
            # intersection of linear functions
            matrix = np.array([[1, -coeffs_hor[1]], [1, -coeffs_ver[1]]])
            vector = np.array([coeffs_hor[0], coeffs_ver[0]])
        else:
            # intersection of non-linear functions
            raise BaseException('Function with degree %s is not supported' % deg)

        return np.dot(np.linalg.pinv(matrix), vector)

    def line_fitter(self, coords, deg=1):
        """ estimate equation fit of 2-D coordinates belonging to the same row or column via least squares method """

        # feed into system of equations
        A = self.compose_vandermonde_1d(coords[:, 1], deg=deg)
        b = coords[:, 0]

        # solve for a least squares estimate via pseudo inverse and coefficients in b
        coeffs = np.dot(np.linalg.pinv(A), b)

        return coeffs

    def compose_vandermonde_1d(self, x, deg=1):
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
