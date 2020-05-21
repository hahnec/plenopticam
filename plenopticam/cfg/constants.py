# dictionary keys for configuration parameters in json file
PARAMS_KEYS = (
    # strings
    'lfp_path',
    'cal_path',
    'cal_meta',
    'cal_meth',
    # integers
    'ptc_leng',
    # lists
    'ran_refo',
    # booleans
    'opt_cali',
    'opt_vign',
    'opt_lier',
    'opt_cont',
    'opt_colo',
    'opt_awb_',
    'opt_sat_',
    'opt_view',
    'opt_refo',
    'opt_refi',
    'opt_pflu',
    'opt_arti',
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
    '',
    # integers
    7,
    # lists
    [0, 2],
    # booleans
    False,
    False,
    False,
    False,
    True,
    False,
    False,
    True,
    True,
    False,
    False,
    False,
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
    'sel',
    # integers
    'sel',
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
    'bool',
    'bool',
    'bool',
    'bool',
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
    'Calibration method',
    # integers
    'Micro image patch size',
    # lists
    'Refocusing range',
    # booleans
    'Redo calibration',
    'De-Vignetting',
    'Pixel outlier removal',
    'Contrast automation',
    'Color equalization',
    'Automatic white balance',
    'Automatic saturation',
    'Viewpoint image extraction',
    'Refocused image extraction',
    'Refocus refinement',
    'Scheimpflug focus',
    'Fringe artifact removal',
    'Rotation of light field',
    'Debug option',
    'Status print option',
    'Remove output folder'
)

# dictionary keys for calibration parameters names in json file
CALIBS_KEYS = (
   # calibs dict keys
   'pat_type',
   'ptc_mean',
   'mic_list'
)

# value ranges
PFLU_VALS = ('vertical', 'horizontal', 'skew up', 'skew down')
PTCH_SIZE = list(range(3, 99, 2))
CALI_METH = ('area', 'peak', 'grid-fit')
