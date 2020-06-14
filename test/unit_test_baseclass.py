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

import unittest
import os
import requests
from zipfile import ZipFile

from plenopticam.misc import mkdir_p


class PlenoptiCamTester(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(PlenoptiCamTester, self).__init__(*args, **kwargs)

        # refer to folder where data will be stored
        self.fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        mkdir_p(self.fp) if not os.path.exists(self.fp) else None

    def download_data(self, url):
        """ download plenoptic image data """

        print('Downloading file %s' % os.path.basename(url))

        # establish internet connection for test data download
        try:
            r = requests.get(url)
        except requests.exceptions.ConnectionError:
            raise (Exception('Check your internet connection, which is required for downloading test data.'))

        with open(os.path.join(self.fp, os.path.basename(url)), 'wb') as f:
            f.write(r.content)

        print('Finished download of %s' % os.path.basename(url))

        return True

    @staticmethod
    def extract_archive(archive_fn, fname_list):
        """ extract content from downloaded data """

        with ZipFile(archive_fn) as z:
            for fn in z.namelist():
                if fn in fname_list:
                    z.extract(fn, os.path.dirname(archive_fn))

        return True
