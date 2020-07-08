#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2020 Christopher Hahne <inbox@christopherhahne.de>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import os
import unittest

from plenopticam.misc import PlenopticamError
from plenopticam.misc import PlenopticamStatus
from plenopticam.cfg import PlenopticamConfig
from plenopticam.lfp_reader import LfpReader
from plenopticam.misc import rm_file, rmdir_p


class PlenoptiCamErrorTester(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamErrorTester, self).__init__(*args, **kwargs)

    def setUp(self):

        self.cfg = PlenopticamConfig()
        self.sta = PlenopticamStatus()

    def test_read_error(self):

        # folder and path handling
        fp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'examples', 'data')
        os.makedirs(fp) if not os.path.exists(fp) else None

        # create dummy file with wrong file format
        self.cfg.params[self.cfg.lfp_path] = os.path.join(fp, 'test_dummy.lfp')
        with open(self.cfg.params[self.cfg.lfp_path], 'a'):
            os.utime(self.cfg.params[self.cfg.lfp_path], None)

        with self.assertRaises(PlenopticamError) as exc:
            reader = LfpReader(cfg=self.cfg, sta=self.sta)
            reader.main()

        self.assertEqual("'dict' object has no attribute 'startswith'", str(exc.exception))

        # remove dummy data after test
        rm_file(self.cfg.params[self.cfg.lfp_path])
        rmdir_p(self.cfg.exp_path)

    def test_all(self):

        self.test_read_error()


if __name__ == '__main__':
    unittest.main()
