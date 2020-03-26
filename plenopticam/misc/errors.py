#!/usr/bin/env python

__author__ = "Christopher Hahne"
__email__ = "info@christopherhahne.de"
__license__ = """
    Copyright (c) 2019 Christopher Hahne <info@christopherhahne.de>

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

import os, time, datetime
from plenopticam.misc.status import PlenopticamStatus


class PlenopticamError(Exception):

    URL_ISSUE = 'https://github.com/hahnec/plenopticam/issues/new'

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args)

        self.cfg = kwargs['cfg'] if 'cfg' in kwargs else None
        self.sta = kwargs['sta'] if 'sta' in kwargs else PlenopticamStatus()

        self.args = args
        try:
            self.write_log()
        except PermissionError as e:
            self.sta.status_msg(msg=e, opt=True)
            raise e

    def write_log(self):

        if self.cfg:
            if self.cfg.params[self.cfg.lfp_path]:
                fp = self.cfg.params[self.cfg.lfp_path].split('.')[0]   # export folder path
                fn = os.path.join(fp, 'err_log.txt')                    # absolute log file name
                self.sta.status_msg('Error! See log file in %s.' %
                                    os.path.join(os.pardir, os.path.basename(fp), 'err_log.txt'))
            else:
                fp, fn = None, None
                self.sta.status_msg(*self.args)

            if fn and os.path.exists(fp):
                with open(fn, 'a') as f:
                    f.writelines(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                    f.writelines('\nOpen issue at %s and paste below traceback.\n\n' % self.URL_ISSUE)
                    f.writelines(self.args.__str__())
                    f.writelines('\n\n\n')

#from requests import session
#from bs4 import BeautifulSoup as bs
#
#class GithubReporter(PlenopticamError):
#
#    USER = 'PlenopticamReporter'
#    PASSWORD = 'u9?KX2+y'
#
#    def __init__(self, *args, **kwargs):
#        PlenopticamError.__init__(self, *args)
#
#        self.url = 'https://github.com/session'
#        self.url_query = self.URL_ISSUE + '?labels=auto&title=Automatic+issue+report&assignees=hahnec'
#
#        self.s = session()
#
#    def alt_submit(self):
#
#        from requests.auth import HTTPBasicAuth
#        self.s.get(self.url_query, auth=HTTPBasicAuth(self.USER, self.PASSWORD))
#
#    def logout(self):
#        pass
#
#    def login(self):
#
#        req = self.s.get(self.url).text
#        html = bs(req)
#        token = html.find("input", {"name": "authenticity_token"}).attrs['value']
#        com_val = html.find("input", {"name": "commit"}).attrs['value']
#
#        login_data = {'login': self.USER,
#                      'password': self.PASSWORD,
#                      'commit': com_val,
#                      'authenticity_token': token
#        }
#
#        self.s.post(self.url, data=login_data)
#
#        return True
#
#    def issue(self):
#
#        site = self.s.get(self.url_query).text
#        html = bs(site)
#
#        token = html.find("input", {"name": "authenticity_token"}).attrs['value']
#        #com_val = html.find("button", {"name": "commit"}).attrs['value']
#
#        issue_data = {
#            'issue': [{
#                "title": 'Plenopticam Error Report',
#                "body": 'Test'
#            }]
#            #'issue[body]': 'Test'#,
#            #'commit': com_val,
#            #'authenticity_token': token
#        }
#
#        self.s.post(self.url_query, data=issue_data)
#
#    def __del__(self):
#
#        # logout from helper account
#        self.logout()
#
#        # close session
#        self.s.close()


class LfpTypeError(PlenopticamError):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class LfpAttributeError(PlenopticamError):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
