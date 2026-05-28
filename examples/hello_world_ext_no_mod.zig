// A Python Native extension that does NOT expose an actual module
// Thus needs our custom loader to expose a single `hello_world` function
const Py_ssize_t = isize;

extern fn Py_IncRef(obj: ?*PyObject) void;
extern var _Py_NoneStruct: PyObject;

const PyObject = extern struct {
    ob_refcnt: i64,
    ob_type: ?*anyopaque,
};

const PyCFunction = *const fn (?*PyObject, ?*PyObject) callconv(.c) ?*PyObject;

const METH_NOARGS: c_int = 4;

const PyMethodDef = extern struct {
    ml_name: ?[*:0]const u8,
    ml_meth: ?PyCFunction,
    ml_flags: c_int,
    ml_doc: ?[*:0]const u8,
};

export fn hello_world(self: ?*PyObject, args: ?*PyObject) callconv(.c) ?*PyObject {
    _ = self;
    _ = args;
    @import("std").debug.print("Hello from zig!\n", .{});
    Py_IncRef(&_Py_NoneStruct);
    return &_Py_NoneStruct;
}
