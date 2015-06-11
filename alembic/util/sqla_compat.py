import re
from sqlalchemy import __version__


def _safe_int(value):
    try:
        return int(value)
    except:
        return value
_vers = tuple(
    [_safe_int(x) for x in re.findall(r'(\d+|[abc]\d)', __version__)])
sqla_07 = _vers > (0, 7, 2)
sqla_079 = _vers >= (0, 7, 9)
sqla_08 = _vers >= (0, 8, 0)
sqla_083 = _vers >= (0, 8, 3)
sqla_084 = _vers >= (0, 8, 4)
sqla_09 = _vers >= (0, 9, 0)
sqla_092 = _vers >= (0, 9, 2)
sqla_094 = _vers >= (0, 9, 4)
sqla_094 = _vers >= (0, 9, 4)
sqla_099 = _vers >= (0, 9, 9)
sqla_100 = _vers >= (1, 0, 0)
sqla_105 = _vers >= (1, 0, 5)

