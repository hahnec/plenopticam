from test.unit_test_custom import PlenoptiCamTesterCustom
from test.unit_test_illum import PlenoptiCamTesterIllum
from test.unit_test_ui import PlenoptiCamTesterUI

# test custom data
obj = PlenoptiCamTesterCustom()
obj.setUp()
obj.test_custom_cal()
obj.test_custom_lfp()
del obj

# test illum data
obj = PlenoptiCamTesterIllum()
obj.setUp()
obj.test_illum()
del obj

# test user interface
obj = PlenoptiCamTesterUI()
obj.setUp()
obj.test_cli_help()
del obj
