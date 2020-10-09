from alembic.config import Config
from alembic.script.base import Script
from typing import (
    Callable,
    List,
    Optional,
    Tuple,
    Union,
)

def current(
    config: Config, verbose: bool = ..., head_only: bool = ...
) -> None: ...
def downgrade(
    config: Config, revision: str, sql: bool = ..., tag: Optional[str] = ...
) -> None: ...
def edit(config: Config, rev: str) -> None: ...
def history(
    config: Config,
    rev_range: Optional[str] = ...,
    verbose: bool = ...,
    indicate_current: bool = ...,
) -> None: ...
def init(
    config: Config, directory: str, template: str = ..., package: bool = ...
) -> None: ...
def merge(
    config: Config,
    revisions: str,
    message: None = ...,
    branch_label: None = ...,
    rev_id: None = ...,
) -> Script: ...
def revision(
    config: Config,
    message: Optional[str] = ...,
    autogenerate: bool = ...,
    sql: bool = ...,
    head: str = ...,
    splice: bool = ...,
    branch_label: Optional[str] = ...,
    version_path: Optional[str] = ...,
    rev_id: Optional[str] = ...,
    depends_on: Optional[Union[str, List[str]]] = ...,
    process_revision_directives: Optional[Callable] = ...,
) -> Union[Script, List[Script]]: ...
def stamp(
    config: Config,
    revision: Union[Tuple[str], List[str], str, Tuple[str, str]],
    sql: bool = ...,
    tag: None = ...,
    purge: bool = ...,
) -> None: ...
def upgrade(
    config: Config, revision: str, sql: bool = ..., tag: Optional[str] = ...
) -> None: ...
