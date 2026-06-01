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
from zitcompiler import zit_compiled

greet = zit_compiled(Path("my_ext.zig"), "greet")
greet()  # Hello from Zig!
```

### Comptime parameters: specialize Zig code from Python

`ZigModuleDef` lets you inject Python dataclass values as Zig `comptime` constants. The Zig module imports them as a named module and the compiler eliminates all dead branches at build time.

```python
from dataclasses import dataclass
from pathlib import Path
from zitcompiler import ZigModuleDef, zit_compiled

@dataclass
class Params:
    multiplier: int = 7

module_def = ZigModuleDef(top_level=Params, structs=[], module_name="params")
get_multiplier = zit_compiled(Path("my_ext.zig"), "get_multiplier", module_def=module_def)
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
