"""Règle « crédit bas » : couper le non essentiel, remonter la clim. Jamais le frigo."""

from ..contract import AcCmd, PlugCmd
from .types import DeviceView

AC_LOW_CREDIT_SETPOINT = 27


def low_credit_actions(days_left: float | None, threshold: float,
                       devices: list[DeviceView]) -> list[tuple[str, PlugCmd | AcCmd]]:
    if days_left is None or days_left >= threshold:
        return []
    out: list[tuple[str, PlugCmd | AcCmd]] = []
    for d in devices:
        if d.essential:
            continue
        if d.kind == "plug" and d.last_state.get("on"):
            out.append((d.id, PlugCmd(on=False)))
        elif (d.kind == "ir_ac" and d.last_state.get("mode") == "cool"
              and d.last_state.get("setpoint_c", 99) < AC_LOW_CREDIT_SETPOINT):
            out.append((d.id, AcCmd(setpoint_c=AC_LOW_CREDIT_SETPOINT)))
    return out
