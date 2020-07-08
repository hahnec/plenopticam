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

import sys
import unittest
import subprocess
import time


class ExecutableTester(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ExecutableTester, self).__init__(*args, **kwargs)

    def setUp(self):
        pass

    def run_app(self):

        if sys.platform == 'linux':
            cmd = 'dist/plenopticam'
        elif sys.platform == 'darwin':
            cmd = 'open dist/plenopticam.app'
        elif sys.platform == 'win32':
            cmd = 'dist\plenopticam.exe'
        else:
            cmd = 'dist/plenopticam'

        process = subprocess.Popen("exec " + cmd, stdout=subprocess.PIPE, shell=True)   # , preexec_fn=os.setsid
        time.sleep(20)
        process.kill()

        result, error = process.communicate()
        self.assertEqual(b'', result)
        self.assertEqual(None, error)

    def test_all(self):

        self.run_app()


if __name__ == '__main__':
    unittest.main()
