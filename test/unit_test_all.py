from test.unit_test_custom import PlenoptiCamTesterCustom
from test.unit_test_illum import PlenoptiCamTesterIllum

# test custom data
ut_obj = PlenoptiCamTesterCustom()
ut_obj.setUp()
ut_obj.test_custom_cal()
ut_obj.test_custom_lfp()
del ut_obj

# test illum data
ut_obj = PlenoptiCamTesterIllum()
ut_obj.setUp()
ut_obj.test_illum()
del ut_obj