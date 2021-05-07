#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "inbox@christopherhahne.de"
__license__ = """
    Copyright (c) 2019 Christopher Hahne <inbox@christopherhahne.de>

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

from plenopticam.bin.cli_script import main, parse_options
from plenopticam.cfg import PlenopticamConfig, PARAMS_KEYS, USER_CMDS
from plenopticam.misc import PlenopticamStatus


class PlenoptiCamTesterCli(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTesterCli, self).__init__(*args, **kwargs)

    def setUp(self):

        # set config for unit test purposes
        self.sta = PlenopticamStatus()
        self.cfg = PlenopticamConfig()
        self.cfg.reset_values()
        self.cfg.params[self.cfg.opt_dbug] = True
        self.cfg.params[self.cfg.opt_prnt] = True

    def test_cli_help(self):

        for kw in ['-h', '--help']:
            # print help message
            sys.argv.append(kw)
            try:
                ret = main()
            except SystemExit:
                ret = True
            sys.argv.pop()

            self.assertEqual(True, ret)

    def test_cli_cmd_opts(self):

        # get rid of potential arguments from previous usage
        sys.argv = sys.argv[:1]
        exp_vals = ['dummy.ext', 'wht.ext', '', 'area', 'global', 9, [0, 2]] + [True, ]*6 + [False] + [True, ]*5
        usr_cmds = ['--' + cmd for cmd in USER_CMDS[2:]]

        for cmd, kw, exp_val in zip(usr_cmds, PARAMS_KEYS, exp_vals):

            # pass CLI argument
            exp_str = '"' + exp_val + '"' if isinstance(exp_val, str) else exp_val
            cli_str = cmd + str(exp_str) if type(exp_val) in (str, int, list) else cmd
            sys.argv.append(cli_str)
            print(kw, cli_str)
            try:
                self.cfg = parse_options(sys.argv[1:], self.cfg)
            except SystemExit:
                pass
            val = self.cfg.params[kw]
            sys.argv.pop()

            self.assertEqual(exp_val, val)

    def test_all(self):

        self.test_cli_help()
        self.test_cli_cmd_opts()


if __name__ == '__main__':
    unittest.main()
