from inspect import ArgSpec
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from alembic.util.exc import CommandError

# Python 3 only:
from io import StringIO
import builtins as compat_builtins
import collections.abc as collections_abc

exec_ = getattr(compat_builtins, "exec")
string_types = (str,)

def callable(fn: Optional[Union[Callable, bool]]) -> bool: ...
def get_current_bytecode_suffixes() -> List[str]: ...
def has_pep3147() -> bool: ...
def inspect_formatargspec(
    args: List[str],
    varargs: Optional[str] = ...,
    varkw: Optional[str] = ...,
    defaults: Optional[Any] = ...,
    kwonlyargs: Tuple = ...,
    kwonlydefaults: Dict[Any, Any] = ...,
    annotations: Dict[Any, Any] = ...,
    formatarg: Type[str] = ...,
    formatvarargs: Callable = ...,
    formatvarkw: Callable = ...,
    formatvalue: Callable = ...,
    formatreturns: Callable = ...,
    formatannotation: Callable = ...,
) -> str: ...
def inspect_getargspec(func: Callable) -> ArgSpec: ...
def load_module_py(module_id: str, path: str): ...
def raise_from_cause(exception: CommandError, exc_info: None = ...): ...
def u(s: str) -> str: ...
def ue(s: str) -> str: ...

class EncodedIO:
    def close(self) -> None: ...
