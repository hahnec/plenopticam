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
from os.path import abspath, dirname, basename
import requests
from zipfile import ZipFile

from plenopticam.misc import mkdir_p, PlenopticamStatus
from plenopticam.cfg import PlenopticamConfig


class DataDownloader(object):

    def __init__(self, *args, **kwargs):

        # instantiate config and status objects
        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else PlenopticamConfig()
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()

        # path handling: refer to folder where data will be stored
        path = kwargs['path'] if 'path' in kwargs else os.path.dirname(os.path.abspath(__file__))
        self._fp = os.path.join(path, 'data')
        self.root_path = dirname(abspath('.')) if basename((abspath('.'))) == 'tests' else abspath('.')

        # data urls
        self.host_eu_url = 'http://wp12283669.server-he.de/Xchange/illum_test_data.zip'
        self.opex_url = 'https://ndownloader.figshare.com/files/5201452'
        self.opex_fnames_wht = ['f197with4m11pxf16Final.bmp', 'f197Inf9pxFinalShift12.7cmf22.bmp']
        self.opex_fnames_lfp = ['f197with4m11pxFinal.bmp', 'f197Inf9pxFinalShift12.7cm.bmp']

    def download_data(self, url, fp=None):
        """ download data form provided url string """

        # path handling
        self.fp = fp if fp is not None else self.fp
        mkdir_p(self.fp) if not os.path.exists(self.fp) else None

        # skip download if file exists
        if os.path.exists(os.path.join(self.fp, os.path.basename(url))):
            print('Download skipped as %s already exists' % os.path.basename(url))
            return None

        print('Downloading file %s to %s' % os.path.basename(url), self.fp)

        with open(os.path.join(self.fp, os.path.basename(url)), 'wb') as f:
            # establish internet connection for data download
            try:
                r = requests.get(url, stream=True)
                total_length = r.headers.get('content-length')
            except requests.exceptions.ConnectionError:
                raise (Exception('Check your internet connection, which is required for downloading test data.'))

            if total_length is None:  # no content length header
                f.write(r.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in r.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    self.sta.progress(dl//total_length * 100, self.cfg.params[self.cfg.opt_prnt])

        print('\n Finished download of %s' % os.path.basename(url))

    def extract_archive(self, archive_fn=None, fname_list=None, fp=None):
        """ extract content from downloaded data """

        # look for archives in file path
        self.fp = fp if fp is not None else self.fp
        if archive_fn is None and fp:
            archive_fns = [os.path.join(self.fp, f) for f in os.listdir(self.fp) if f.endswith('zip')]
        else:
            archive_fns = [archive_fn]

        for archive_fn in archive_fns:

            # choose from filenames inside archive
            fname_list = self.find_archive_fnames(archive_fn) if fname_list is None else fname_list

            # extract chosen files
            with ZipFile(archive_fn) as z:
                for fn in z.namelist():
                    if fn in fname_list and not os.path.exists(os.path.join(self.fp, fn)):
                        z.extract(fn, os.path.dirname(archive_fn))
                        print('Extracted file %s' % fn)

    @staticmethod
    def find_archive_fnames(archive_fn):
        return [f for f in ZipFile(archive_fn).namelist() if f.startswith('caldata') or f.endswith('lfr')]

    @property
    def fp(self):
        return self._fp

    @fp.setter
    def fp(self, fp):
        self._fp = fp
        mkdir_p(self._fp) if not os.path.exists(self._fp) else None
