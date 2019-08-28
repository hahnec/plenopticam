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
    'opt_vign',
    'opt_hotp',
    'opt_cont',
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
    [0, 2],
    # booleans
    False,
    True,
    False,
    True,
    False,
    True,
    True,
    False,
    'off',
    True,
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
    'De-Vignetting',
    'Hot pixel correction',
    'Contrast automation',
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

PFLU_VALS = ('off', 'vertical', 'horizontal', 'skew up', 'skew down')