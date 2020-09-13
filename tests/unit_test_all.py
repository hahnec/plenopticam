from tests.unit_test_custom import PlenoptiCamTesterCustom
from tests.unit_test_illum import PlenoptiCamTesterIllum
from tests.unit_test_cli import PlenoptiCamTesterCli
from tests.unit_test_gui import PlenoptiCamTesterGui
from tests.unit_test_err import PlenoptiCamErrorTester
from tests.unit_test_plt import PlenopticamTesterPlt

test_classes = [PlenoptiCamTesterCli, PlenoptiCamErrorTester, PlenoptiCamTesterCustom, PlenoptiCamTesterIllum,
                PlenoptiCamTesterGui, PlenopticamTesterPlt]

for test_class in test_classes:
    obj = test_class()
    obj.setUp()
    obj.test_all()
    del obj
