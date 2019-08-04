import os, time, datetime
from plenopticam import misc

class PlenopticamError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args)

        sta = kwargs['sta'] if 'sta' in kwargs is not None else misc.PlenopticamStatus()

        if 'cfg' in kwargs:
            cfg = kwargs['cfg']
            fp = os.path.join(cfg.params[cfg.lfp_path].split('.')[0], 'log.txt')
            sta.status_msg('Error! See log file in %s.' % fp)
        else:
            fp = None
            sta.status_msg(*args)

        if fp:
            with open(fp, 'a') as f:
                f.writelines(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                f.writelines('\nOpen issue at https://github.com/hahnec/plenopticam/issues/new and paste below traceback.\n')
                f.writelines(args.__str__())
                f.writelines('\n\n\n')

class LfpTypeError(PlenopticamError):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class LfpAttributeError(PlenopticamError):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)