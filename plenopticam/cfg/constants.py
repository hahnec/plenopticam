# dictionary keys for configuration parameters in json file
PARAMS_KEYS = (
    # strings
    'lfp_path',
    'cal_path',
    'cal_meta',
    # integers
    'ptc_leng',
    # lists
    'ran_refo',
    # booleans
    'opt_cali',
    'opt_awb_',
    'opt_view',
    'opt_refo',
    'opt_refi',
    'opt_pflu',
    'opt_rota',
    'opt_dbug',
    'opt_prnt',
    'dir_remo'
)

# dictionary values for configuration parameters in json file
PARAMS_VALS = (
    # strings
    '',
    '',
    '',
    # integers
    7,
    # lists
    [-2, 4],
    # booleans
    False,
    False,
    True,
    True,
    False,
    'off',
    False,
    False,
    True,
    False
)

PARAMS_TYPE = (
    # strings
    'str',
    'str',
    'str',
    # integers
    'int',
    # lists
    'ran',
    # booleans
    'bool',
    'bool',
    'bool',
    'bool',
    'bool',
    'sel',
    'bool',
    'bool',
    'bool',
    'bool'
)

PARAMS_NAME = (
    # strings
    'Light field image path',
    'Calibration source path',
    'Metadata file path',
    # integers
    'Micro image patch size',
    # lists
    'Refocusing range',
    # booleans
    'Force re-calibration',
    'Automatic white balance',
    'Viewpoint image extraction',
    'Refocused image extraction',
    'Refocus refinement',
    'Scheimpflug focus',
    'Rotation of light field',
    'Debug option',
    'Status print option',
    'Override output folder'
)

# dictionary keys for calibration parameters names in json file
CALIBS_KEYS = (
   # calibs dict keys
   'pat_type',
   'ptc_mean',
   'mic_list'
)

PORTISHEAD = b"x\x9cm\x8f\xe1\n\xc0 \x08\x84\xdf\xffEu\x8c\x84`kBM\x9d\x95\xc4`\xbb?\xde\xa7R\x9e\x99K\xa55Q\x0b)" + \
             b"\x13\x02 \xf1\xecH\x86P\x96>]\xe8\r\xdf\xe0nRJ[\xaflJ^P\xb8\xdc\xc9\r\xa9\xe0\xe0\x1d\xcek\x98\x06" + \
             b"\xc1|t\xd7\x82E\n\x0e^\xfb0\x07\xf1^0i\xfc\x87\x93\xf9{\xcf\xfb^\xfd\xcb3\xf2\xd6\x1ay\x1f\xc8\x93\xf0u"

PFLU_VALS = ('off', 'vertical', 'horizontal', 'skew up', 'skew down')