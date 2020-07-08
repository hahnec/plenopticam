from tests.unit_test_custom import PlenoptiCamTesterCustom
from tests.unit_test_illum import PlenoptiCamTesterIllum
from tests.unit_test_cli import PlenoptiCamTesterCli
from tests.unit_test_gui import PlenoptiCamTesterGui

# test user interface
obj = PlenoptiCamTesterCli()
obj.setUp()
obj.test_all()
del obj

# test user interface
obj = PlenoptiCamTesterGui()
obj.setUp()
obj.test_all()
del obj

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
