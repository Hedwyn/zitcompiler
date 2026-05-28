# zitcompiler

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
