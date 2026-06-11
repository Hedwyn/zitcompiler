# zitcompiler

JIT-like native extension compilation for Python using the Zig compiler. Write a Zig module, compile it at runtime, and load the result as a callable Python object — with optional comptime parameter injection so the same Zig source can be specialized differently on each call.

Requires the `ziglang` package (`pip install ziglang`).

## Usage

### Basic: compile and load a function

Write a Zig module that exports a standard CPython `PyCFunction`:

```zig
// my_ext.zig
extern fn Py_IncRef(obj: ?*PyObject) void;
extern var _Py_NoneStruct: PyObject;
const PyObject = extern struct { ob_refcnt: i64, ob_type: ?*anyopaque };

export fn greet(self: ?*PyObject, args: ?*PyObject) callconv(.c) ?*PyObject {
    _ = self; _ = args;
    @import("std").debug.print("Hello from Zig!\n", .{});
    Py_IncRef(&_Py_NoneStruct);
    return &_Py_NoneStruct;
}
```

Load it from Python with the high-level helper:

```python
from pathlib import Path
from zitcompiler import zitcompiled

greet = zitcompiled(Path("my_ext.zig"), "greet")
greet()  # Hello from Zig!
```

### Comptime parameters: specialize Zig code from Python

`ZigModuleDef` lets you inject Python dataclass values as Zig `comptime` constants. The Zig module imports them as a named module and the compiler eliminates all dead branches at build time.

```python
from dataclasses import dataclass
from pathlib import Path
from zitcompiler import ZigModuleDef, zitcompiled

@dataclass
class Params:
    multiplier: int = 7

module_def = ZigModuleDef(top_level=Params, structs=[], module_name="params")
get_multiplier = zitcompiled(Path("my_ext.zig"), "get_multiplier", module_def=module_def)
```

```zig
// my_ext.zig
const params = @import("params");  // injected at compile time
const PyObject = extern struct { ob_refcnt: i64, ob_type: ?*anyopaque };
extern fn PyLong_FromLong(v: c_long) ?*PyObject;

export fn get_multiplier(self: ?*PyObject, args: ?*PyObject) callconv(.c) ?*PyObject {
    _ = self; _ = args;
    return PyLong_FromLong(params.multiplier);  // 7, resolved at compile time
}
```

Structs defined in the dataclass are emitted as Zig `struct` types in the injected module, enabling comptime reflection (e.g. `@typeInfo(params.Point).@"struct".fields.len`).

### Low-level API

For finer control, use `zig_build_lib` directly and then `load_function` / `load_class`:

```python
import asyncio
from pathlib import Path
from zitcompiler import BuildLibOptions, load_function, zig_build_lib

opts = BuildLibOptions(
    module_path=Path("my_ext.zig"),
    link_python=True,
    output_path=Path("/tmp/my_ext.so"),
)
so_path = asyncio.run(zig_build_lib(opts))
greet = load_function(so_path, "greet")
greet()
```

`load_class` works the same way for exported `PyTypeObject` symbols.

## Zetaclasses

`zetaclass` is a drop-in replacement for `@dataclass` that compiles the class to a native Zig struct at decoration time. The resulting type behaves like a regular Python class but `__init__` and `__eq__` run as compiled C slots — no Python interpreter overhead.

### Usage

```python
from zitcompiler.zetaclasses import zetaclass

@zetaclass
class Point:
    x: int
    y: int

p1 = Point(1, 2)
p2 = Point(x=1, y=2)
assert p1 == p2
```

Supported field types: `int` (`i64`), `float` (`f64`), `str` (Python string object).

Default values work the same as with `@dataclass`:

```python
@zetaclass
class Config:
    host: str = "localhost"
    port: int = 8080
    timeout: float = 30.0

cfg = Config()            # all defaults
cfg2 = Config(port=9090)  # keyword override
assert cfg != cfg2
```

Positional, keyword, and mixed argument styles are all supported:

```python
Config("example.com", 443)       # positional
Config(host="example.com")       # keyword only
Config("example.com", timeout=5) # mixed
```

Attribute access works normally — fields are readable and writable:

```python
print(cfg.host)   # "localhost"
cfg.port = 9090
```

### Current limitations

- Supported field types: `int`, `float`, `str`. Other types raise `TypeError` at decoration time.
- `__repr__`, `__hash__`, ordering operators, and `frozen` are not yet implemented.
- Compilation runs synchronously at decoration time (same as other `zitcompiler` calls).

### Internal implementation

When `@zetaclass` is applied, the decorator:

1. Reads field names, types, and default values from the class annotations (following the MRO).
2. Generates a `params.zig` source file containing an `extern struct` with `ob_base: PyObject` as its first field — the layout CPython requires for all heap-allocated objects — followed by one field per annotation.
3. Generates a `Defaults` struct holding comptime constants for each field that has a default value. String defaults are stored as `[:0]const u8` (null-terminated slice); numeric defaults as `i64`/`f64`.
4. Compiles `params.zig` against `core.zig` (the static Zig library shipped with the package) using `zig build-lib`.
5. Loads the exported `PyTypeObject` symbol via `load_class`, which calls `PyType_Ready` to finalise the type.

`core.zig` provides the comptime slot generators:

| Slot | Generator | What it does |
|------|-----------|--------------|
| `tp_init` | `initFn(T, Defaults)` | Iterates struct fields at comptime; reads positional args, then kwargs, then comptime defaults. Stores values with ref-counting for `?*PyObject` fields. |
| `tp_richcompare` | `richCompareFn(T)` | Field-by-field equality via `!=` for numeric fields and `PyObject_RichCompareBool` for string fields. Returns `Py_NotImplemented` for non-EQ/NE ops or mismatched types. |
| `tp_members` | `membersArray(T)` | Comptime-generates a null-terminated `PyMemberDef[]` using `@offsetOf` for each field. Python's built-in member descriptor machinery handles all get/set at runtime — no Zig code runs on attribute access. |
| `tp_dealloc` | `deallocFn(T)` | Decrefs all `?*PyObject` fields then calls `PyObject_Free`. Only wired in when the struct contains object fields; otherwise null and CPython inherits the default from `object`. |

The `Defaults` struct approach avoids any Python-level wrapper class: defaults are resolved entirely in the compiled `tp_init` slot, so the loaded `PyTypeObject` is the final Python type with no subclassing or runtime indirection.

## JSON schema → native class

`zitcompiler.jsonschemas` can compile a native class directly from a JSON schema definition, without writing any Python class by hand.

### Quick start

```python
import json
from pathlib import Path
from zitcompiler.jsonschemas import zetaify

schema = json.loads(Path("person.json").read_text())
Person = zetaify(schema)

p = Person(name="Alice", age=30)
print(p)  # Person(name='Alice', age=30)
```

`zetaify` accepts a raw JSON-decoded dict or a pre-parsed `SchemaDef`. It returns a fully compiled `@zetaclass` type.

### Saving a type stub

Pass `stub_path` to write a `.pyi` file alongside your schema. The stub includes the `@zetaclass` decorator so it reads as a valid, annotated class definition:

```python
Person = zetaify(schema, stub_path=Path("person.pyi"))
```

Generated `person.pyi`:

```python
from zitcompiler.zetaclasses import zetaclass

@zetaclass
class Person:
    name: str
    age: int
    height: float | None
    active: bool | None
```

### Forwarding zetaclass options

Any keyword accepted by `@zetaclass` can be forwarded through `zetaify`:

```python
Person = zetaify(schema, frozen=True, kw_only=True)
```

### Lower-level API

Use `parse_schema` and `generate_stub` directly if you need the intermediate representations:

```python
from zitcompiler.jsonschemas import generate_stub, parse_schema

schema_def = parse_schema(raw)          # → SchemaDef
print(generate_stub(schema_def))        # plain class body
print(generate_stub(schema_def, with_decorator=True))  # with @zetaclass header
```

### Current limitations

- Only flat (non-nested) schemas are supported. Nested `object` properties are not yet handled.
- Optional fields (`T | None`, i.e. properties absent from `required`) are present in the written stub but **excluded from the compiled native struct**, since the Zig backend has no nullable scalar type mapping yet. Only required fields with types `string`, `integer`, or `number` become native struct fields.
- `boolean` and `null` JSON schema types appear in stubs as `bool` / `None` but are not currently supported as zetaclass field types; including them as required fields will raise a `TypeError` at compilation time.

## Tests

### Unit tests

```sh
uv run pytest tests/
```

Covers Zig module compilation (`zig_build_lib`), comptime parameter injection, and `load_function` / `load_class`.

### Build backend integration tests

```sh
nox -f tests/build_backend/noxfile.py
```

Tests the hatch build hook end-to-end. The session:

1. Installs `hatchling` and a local editable copy of `zitcompiler` into a fresh virtual environment.
2. Builds the `greetings` test package (`tests/build_backend/test_pkg/`) with `uv build --no-build-isolation`. During the wheel build, the hatch hook imports `greetings`, which triggers a `zitcompiled()` call, and the resulting `.so` is bundled into the wheel.
3. Installs the built wheel and runs `pytest tests/build_backend/test_aot.py`, which verifies that the pre-compiled `.so` is present inside the installed package and that all exported symbols (function and zetaclasses) work correctly.

The test package (`greetings`) contains one `zitcompiled()` Zig function (`hello_world`) and three `@zetaclass` types (`Greeter`, `Point`, `Color`). The `hello_world` function is the AoT target; zetaclasses compile at import time as usual.

## Known limitations

### Incremental compilation on Linux (ELF targets)

`BuildLibOptions.incremental = True` passes `-fincremental` to the Zig compiler, which activates the `elf2` linker backend. As of Zig 0.16, **elf2 does not implement saving linker state to disk**, so incremental `build-lib` always fails on ELF targets with:

```
error(compilation): TODO implement saving linker state for elf2
```

**Why this exists:** true incremental linking requires persisting the linker's internal data structures (symbol tables, section allocations, relocation records, virtual address assignments) between builds so subsequent builds can restore and patch only what changed. The elf2 linker tracks dirty sections in memory via a `ZigObject` structure but cannot yet serialize that state to disk.

**This is independent of what you link against** — the error occurs even for a minimal Zig module with no external dependencies.

**Roadmap:** tracked in [ziglang/zig#21165](https://github.com/ziglang/zig/issues/21165). Incremental compilation works today for pure Zig executables and (as of April 2026) the LLVM backend; `build-lib` on ELF is the remaining gap. Once Zig lands linker state serialization, `incremental = True` will work transparently.

`zitcompiler` emits a `logging.WARNING` when `incremental = True` is requested on a non-Windows, non-macOS platform.

## Examples

### hello_world

```sh
zig build-lib examples/hello_world.zig
```

### hello_world_ext (Python C extension, module-level function)

```sh
zig build-lib -dynamic -lc examples/hello_world_ext.zig -femit-bin=hello_world.so $(python3-config --ldflags --embed)
```

```python
import sys; sys.path.insert(0, ".")
import hello_world
hello_world.hello_world()  # prints: Hello from zig!
```

### greeter_ext (Python C extension, class with method)

```sh
zig build-lib -dynamic -lc examples/greeter_ext.zig -femit-bin=greeter.so $(python3-config --ldflags --embed)
```

```python
import sys; sys.path.insert(0, ".")
import greeter
g = greeter.Greeter()
g.hello_world()  # prints: Hello from zig!
```
