"""
Implements the zetaclass decorator.
Populates the dataclass-like methods with native code.

@date: 04.06.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import TypedDict, Unpack, get_type_hints

from zitcompiler import BuildLibOptions, load_class, zig_build_lib


class DataclassKwargs(TypedDict, total=False):
    init: bool
    repr: bool
    eq: bool
    order: bool
    unsafe_hash: bool
    frozen: bool
    match_args: bool
    kw_only: bool
    slots: bool
    weakref_slot: bool


_CORE_ZIG = Path(__file__).parent / "core.zig"

_ZIG_FIELD_TYPES: dict[type, str] = {
    int: "i64",
    float: "f64",
    str: "?*core.PyObject",
}


def _zig_default_line[T](fname: str, ftype: type[T], value: T) -> str:
    if ftype is int:
        return f"    pub const {fname}: i64 = {int(value)};"
    elif ftype is float:
        return f"    pub const {fname}: f64 = {float(value)!r};"
    elif ftype is str:
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        return f'    pub const {fname}: [:0]const u8 = "{escaped}";'
    else:
        raise TypeError(f"unsupported default type {ftype!r}")


def _generate_params_zig(
    class_name: str,
    field_pairs: list[tuple[str, type]],
    defaults: dict[str, object],
) -> str:
    lines = ['const core = @import("core");', ""]

    lines.append(f"pub const {class_name}Object = extern struct {{")
    lines.append("    ob_base: core.PyObject,")
    for fname, ftype in field_pairs:
        lines.append(f"    {fname}: {_ZIG_FIELD_TYPES[ftype]},")
    lines.append("};")
    lines.append("")

    if defaults:
        lines.append(f"const {class_name}Defaults = struct {{")
        for fname, ftype in field_pairs:
            if fname in defaults:
                lines.append(_zig_default_line(fname, ftype, defaults[fname]))
        lines.append("};")
        defaults_arg = f"{class_name}Defaults"
    else:
        defaults_arg = "core.NoDefaults"

    lines.append("")
    lines.append(
        f"pub export var {class_name}Type: core.PyTypeObject = "
        f'core.makeTypeObject({class_name}Object, {defaults_arg}, "{class_name}");',
    )
    return "\n".join(lines)


def zetaclass(cls: type, **kwargs: Unpack[DataclassKwargs]) -> type:
    """Compile and load a native dataclass-compatible type backed by Zig.

    Inspects annotations from cls and its bases, compiles a Zig struct with
    native __init__ (including defaults) and __eq__ slots.

    Accepts the same keyword arguments as @dataclass. Any argument other than
    the defaults raises NotImplementedError until the corresponding feature is
    implemented.
    """
    if kwargs:
        raise NotImplementedError(
            f"zetaclass: keyword arguments not yet supported: {', '.join(kwargs)}"
        )
    hints = get_type_hints(cls)
    field_names = list(hints.keys())
    field_pairs = [(n, hints[n]) for n in field_names]

    for _, ftype in field_pairs:
        if ftype not in _ZIG_FIELD_TYPES:
            raise TypeError(f"zetaclass: unsupported field type {ftype!r}")

    # Collect defaults by walking MRO (closest definition wins)
    defaults: dict[str, object] = {}
    for name in field_names:
        for base in cls.__mro__:
            if name in vars(base) and not isinstance(vars(base)[name], type):
                defaults[name] = vars(base)[name]
                break

    class_name = cls.__name__
    params_src = _generate_params_zig(class_name, field_pairs, defaults)

    with tempfile.TemporaryDirectory() as tmp:
        params_path = Path(tmp) / "params.zig"
        params_path.write_text(params_src)
        out_path = Path(tmp) / f"{class_name}.so"

        opts = BuildLibOptions(
            module_path=params_path,
            link_python=True,
            output_path=out_path,
            extra_deps={"core": _CORE_ZIG},
        )
        so_path = asyncio.run(zig_build_lib(opts))
        return load_class(so_path, f"{class_name}Type")
