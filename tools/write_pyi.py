from __future__ import annotations

from abc import abstractmethod
from argparse import ArgumentParser
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
import textwrap
import typing

sys.path.append(str(Path(__file__).parent.parent))


if True:  # avoid flake/zimports messing with the order
    from alembic.autogenerate.api import AutogenContext
    from alembic.ddl.impl import DefaultImpl
    from alembic.runtime.migration import MigrationInfo
    from alembic.operations.base import BatchOperations
    from alembic.operations.base import Operations
    from alembic.runtime.environment import EnvironmentContext
    from alembic.runtime.migration import MigrationContext
    from alembic.script.write_hooks import console_scripts
    from alembic.util.compat import inspect_formatargspec
    from alembic.util.compat import inspect_getfullargspec
    from alembic.operations import ops
    import sqlalchemy as sa

TRIM_MODULE = [
    "alembic.autogenerate.api.",
    "alembic.operations.base.",
    "alembic.operations.ops.",
    "alembic.runtime.migration.",
    "sqlalchemy.engine.base.",
    "sqlalchemy.engine.url.",
    "sqlalchemy.sql.base.",
    "sqlalchemy.sql.dml.",
    "sqlalchemy.sql.elements.",
    "sqlalchemy.sql.functions.",
    "sqlalchemy.sql.schema.",
    "sqlalchemy.sql.selectable.",
    "sqlalchemy.sql.type_api.",
    "typing.",
]
ADDITIONAL_ENV = {
    "MigrationContext": MigrationContext,
    "AutogenContext": AutogenContext,
    "DefaultImpl": DefaultImpl,
    "MigrationInfo": MigrationInfo,
}


def generate_pyi_for_proxy(
    file_info: FileInfo, destination_path: Path, ignore_output: bool
):
    if sys.version_info < (3, 11):
        raise RuntimeError(
            "This script must be run with Python 3.11 or higher"
        )

    progname = Path(sys.argv[0]).as_posix()
    # When using an absolute path on windows, this will generate the correct
    # relative path that shall be written to the top comment of the pyi file.
    if Path(progname).is_absolute():
        progname = Path(progname).relative_to(Path().cwd()).as_posix()

    file_info.read_file()

    cls = file_info.target
    with open(destination_path, "w") as buf:
        file_info.write_before(buf, progname)

        module = sys.modules[cls.__module__]
        env = {
            **typing.__dict__,
            **sa.schema.__dict__,
            **sa.__dict__,
            **sa.types.__dict__,
            **ADDITIONAL_ENV,
            **ops.__dict__,
            **module.__dict__,
        }

        for name in dir(cls):
            if name.startswith("_") or name in file_info.ignore_items:
                continue
            meth = getattr(cls, name, None)
            if callable(meth):
                # If there are overloads, generate only those
                # Do not generate the base implementation to avoid mypy errors
                overloads = typing.get_overloads(meth)
                is_context_manager = name in file_info.context_managers
                if overloads:
                    # use enumerate so we can generate docs on the
                    # last overload
                    for i, ovl in enumerate(overloads, 1):
                        text = _generate_stub_for_meth(
                            ovl,
                            cls,
                            file_info,
                            env,
                            is_context_manager=is_context_manager,
                            is_overload=True,
                            base_method=meth,
                            gen_docs=(i == len(overloads)),
                        )
                        file_info.write(buf, text)
                else:
                    text = _generate_stub_for_meth(
                        meth,
                        cls,
                        file_info,
                        env,
                        is_context_manager=is_context_manager,
                    )
                    file_info.write(buf, text)
            else:
                text = _generate_stub_for_attr(cls, name, env)
                file_info.write(buf, text)

        file_info.write_after(buf)

    console_scripts(
        str(destination_path),
        {"entrypoint": "zimports", "options": "-e"},
        ignore_output=ignore_output,
    )

    console_scripts(
        str(destination_path),
        {"entrypoint": "black", "options": "-l79 --target-version py39"},
        ignore_output=ignore_output,
    )


def _generate_stub_for_attr(cls, name, env):
    try:
        annotations = typing.get_type_hints(cls, env)
    except NameError:
        annotations = cls.__annotations__
    type_ = annotations.get(name, "Any")
    if isinstance(type_, str) and type_[0] in "'\"":
        type_ = type_[1:-1]
    return f"{name}: {type_}"


def _generate_stub_for_meth(
    fn,
    cls,
    file_info,
    env,
    is_context_manager,
    is_overload=False,
    base_method=None,
    gen_docs=True,
):
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__

    name = fn.__name__
    spec = inspect_getfullargspec(fn)
    try:
        annotations = typing.get_type_hints(fn, env)
        spec.annotations.update(annotations)
    except NameError as e:
        print(f"{cls.__name__}.{name} NameError: {e}", file=sys.stderr)

    name_args = spec[0]
    assert name_args[0:1] == ["self"] or name_args[0:1] == ["cls"]

    if file_info.RemoveFirstArg:
        name_args[0:1] = []

    def _formatannotation(annotation, base_module=None):
        if getattr(annotation, "__module__", None) == "typing":
            retval = repr(annotation).replace("typing.", "")
        elif isinstance(annotation, type):
            retval = annotation.__qualname__
        elif isinstance(annotation, typing.TypeVar):
            retval = annotation.__name__
        elif hasattr(annotation, "__args__") and hasattr(
            annotation, "__origin__"
        ):
            # generic class
            retval = str(annotation)
        else:
            retval = annotation

        retval = re.sub(r"TypeEngine\b", "TypeEngine[Any]", retval)

        retval = retval.replace("~", "")  # typevar repr as "~T"
        for trim in TRIM_MODULE:
            retval = retval.replace(trim, "")

        retval = re.sub(
            r'ForwardRef\(([\'"].+?[\'"])\)', lambda m: m.group(1), retval
        )
        retval = re.sub("NoneType", "None", retval)
        return retval

    def _formatvalue(value):
        return "=" + ("..." if value is Ellipsis else repr(value))

    argspec = inspect_formatargspec(
        *spec,
        formatannotation=_formatannotation,
        formatvalue=_formatvalue,
        formatreturns=lambda val: f"-> {_formatannotation(val)}",
    )

    overload = "@overload" if is_overload else ""
    contextmanager = "@contextmanager" if is_context_manager else ""

    fn_doc = base_method.__doc__ if base_method else fn.__doc__
    has_docs = gen_docs and fn_doc is not None
    string_prefix = "r" if has_docs and chr(92) in fn_doc else ""
    if has_docs:
        noqua = " # noqa: E501" if file_info.docs_noqa_E501 else ""

        if sys.version_info >= (3, 13):
            # python 3.13 seems to remove the leading spaces from docs,
            # but the following needs them, so re-add it
            # https://docs.python.org/3/whatsnew/3.13.html#other-language-changes
            indent = "        "
            fn_doc = textwrap.indent(fn_doc, indent)[len(indent) :]
            if fn_doc[-1] == "\n":
                fn_doc += indent

        docs = f'{string_prefix}"""{fn_doc}"""{noqua}'
    else:
        docs = ""

    suffix = "..." if file_info.AddEllipsis and docs else ""

    func_text = textwrap.dedent(
        f"""
    {overload}
    {contextmanager}
    def {name}{argspec}: {"..." if not docs else ""}
        {docs}
        {suffix}
    """
    )

    return func_text


def run_file(finfo: FileInfo, stdout: bool):
    if not stdout:
        generate_pyi_for_proxy(
            finfo, destination_path=finfo.path, ignore_output=False
        )
    else:
        with NamedTemporaryFile(delete=False, suffix=finfo.path.suffix) as f:
            f.close()
            f_path = Path(f.name)
            generate_pyi_for_proxy(
                finfo, destination_path=f_path, ignore_output=True
            )
            sys.stdout.write(f_path.read_text())
        f_path.unlink()


def main(args):
    for case in cases:
        if args.name == "all" or args.name == case.name:
            run_file(case, args.stdout)


@dataclass
class FileInfo:
    RemoveFirstArg: typing.ClassVar[bool]
    AddEllipsis: typing.ClassVar[bool]

    name: str
    path: Path
    target: type
    ignore_items: set[str] = field(default_factory=set)
    context_managers: set[str] = field(default_factory=set)
    docs_noqa_E501: bool = field(default=False)

    @abstractmethod
    def read_file(self):
        pass

    @abstractmethod
    def write_before(self, out: typing.IO[str], progname: str):
        pass

    @abstractmethod
    def write(self, out: typing.IO[str], text: str):
        pass

    def write_after(self, out: typing.IO[str]):
        pass


@dataclass
class StubFileInfo(FileInfo):
    RemoveFirstArg = True
    AddEllipsis = False
    imports: list[str] = field(init=False)

    def read_file(self):
        imports = []
        read_imports = False
        with open(self.path) as read_file:
            for line in read_file:
                if line.startswith("# ### this file stubs are generated by"):
                    read_imports = True
                elif line.startswith("### end imports ###"):
                    read_imports = False
                    break
                elif read_imports:
                    imports.append(line.rstrip())
        self.imports = imports

    def write_before(self, out: typing.IO[str], progname: str):
        self.write(
            out,
            f"# ### this file stubs are generated by {progname} "
            "- do not edit ###",
        )
        for line in self.imports:
            self.write(out, line)
        self.write(out, "### end imports ###\n")

    def write(self, out: typing.IO[str], text: str):
        out.write(text)
        out.write("\n")


@dataclass
class PyFileInfo(FileInfo):
    RemoveFirstArg = False
    AddEllipsis = True
    indent: str = field(init=False)
    before: list[str] = field(init=False)
    after: list[str] = field(init=False)

    def read_file(self):
        self.before = []
        self.after = []
        state = "before"
        start_text = rf"^(\s*)# START STUB FUNCTIONS: {self.name}"
        end_text = rf"^\s*# END STUB FUNCTIONS: {self.name}"
        with open(self.path) as read_file:
            for line in read_file:
                if m := re.match(start_text, line):
                    assert state == "before"
                    self.indent = m.group(1)
                    self.before.append(line)
                    state = "stubs"
                elif m := re.match(end_text, line):
                    assert state == "stubs"
                    state = "after"
                if state == "before":
                    self.before.append(line)
                if state == "after":
                    self.after.append(line)
        assert state == "after", state

    def write_before(self, out: typing.IO[str], progname: str):
        out.writelines(self.before)
        self.write(
            out, f"# ### the following stubs are generated by {progname} ###"
        )
        self.write(out, "# ### do not edit ###")

    def write(self, out: typing.IO[str], text: str):
        out.write(textwrap.indent(text, self.indent))
        out.write("\n")

    def write_after(self, out: typing.IO[str]):
        out.writelines(self.after)


location = Path(__file__).parent.parent / "alembic"

cls_ignore = {
    "batch_alter_table",
    "context",
    "create_module_class_proxy",
    "f",
    "get_bind",
    "get_context",
    "implementation_for",
    "inline_literal",
    "invoke",
    "register_operation",
    "run_async",
}

cases = [
    StubFileInfo(
        "op",
        location / "op.pyi",
        Operations,
        ignore_items={"context", "create_module_class_proxy"},
        context_managers={"batch_alter_table"},
    ),
    StubFileInfo(
        "context",
        location / "context.pyi",
        EnvironmentContext,
        ignore_items={
            "create_module_class_proxy",
            "get_impl",
            "requires_connection",
        },
    ),
    PyFileInfo(
        "batch_op",
        location / "operations/base.py",
        BatchOperations,
        ignore_items=cls_ignore,
        docs_noqa_E501=True,
    ),
    PyFileInfo(
        "op_cls",
        location / "operations/base.py",
        Operations,
        ignore_items=cls_ignore,
        docs_noqa_E501=True,
    ),
]

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--name",
        choices=[fi.name for fi in cases] + ["all"],
        default="all",
        help="Which name to generate. Default is to regenerate all names",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Write to stdout instead of saving to file",
    )
    args = parser.parse_args()
    main(args)
