from wattou.analysis.rules import low_credit_actions
from wattou.analysis.types import DeviceView
from wattou.contract import AcCmd, PlugCmd

DEVICES = [
    DeviceView("meter", "meter", False, {}),
    DeviceView("prise-fer", "plug", False, {"on": True, "p_w": 1000}),
    DeviceView("prise-tv", "plug", False, {"on": False, "p_w": 0}),
    DeviceView("prise-frigo", "plug", True, {"on": True, "p_w": 120}),
    DeviceView("clim", "ir_ac", False, {"mode": "cool", "setpoint_c": 22}),
]


def test_low_credit_cuts_non_essential():
    actions = dict(low_credit_actions(1.5, 2, DEVICES))
    assert actions["prise-fer"] == PlugCmd(on=False)
    assert "prise-tv" not in actions  # déjà éteinte


def test_low_credit_never_cuts_essential():
    assert "prise-frigo" not in dict(low_credit_actions(0.1, 2, DEVICES))


def test_ac_setpoint_raised_to_27():
    assert dict(low_credit_actions(1.5, 2, DEVICES))["clim"] == AcCmd(setpoint_c=27)


def test_ac_setpoint_never_lowered():
    devices = [DeviceView("clim", "ir_ac", False, {"mode": "cool", "setpoint_c": 29})]
    assert low_credit_actions(1.5, 2, devices) == []


def test_no_action_above_threshold():
    assert low_credit_actions(3, 2, DEVICES) == []
    assert low_credit_actions(None, 2, DEVICES) == []
