// Minimal Python C API ABI declarations — no @cInclude needed
const Py_ssize_t = isize;

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

const PyModuleDef_Base = extern struct {
    ob_base: PyObject,
    m_init: ?*const fn () callconv(.c) ?*PyObject,
    m_index: Py_ssize_t,
    m_copy: ?*PyObject,
};

const PyModuleDef = extern struct {
    m_base: PyModuleDef_Base,
    m_name: ?[*:0]const u8,
    m_doc: ?[*:0]const u8,
    m_size: Py_ssize_t,
    m_methods: ?[*]PyMethodDef,
    m_slots: ?*anyopaque,
    m_traverse: ?*anyopaque,
    m_clear: ?*anyopaque,
    m_free: ?*anyopaque,
};

extern fn PyModule_Create2(def: *PyModuleDef, apiver: c_int) ?*PyObject;
extern fn Py_IncRef(obj: ?*PyObject) void;
extern var _Py_NoneStruct: PyObject;

export fn hello_world(self: ?*PyObject, args: ?*PyObject) callconv(.c) ?*PyObject {
    _ = self;
    _ = args;
    @import("std").debug.print("Hello from zig!\n", .{});
    Py_IncRef(&_Py_NoneStruct);
    return &_Py_NoneStruct;
}

var methods = [_]PyMethodDef{
    .{
        .ml_name = "hello_world",
        .ml_meth = hello_world,
        .ml_flags = METH_NOARGS,
        .ml_doc = null,
    },
    .{
        .ml_name = null,
        .ml_meth = null,
        .ml_flags = 0,
        .ml_doc = null,
    },
};

var module_def = PyModuleDef{
    .m_base = .{
        .ob_base = .{ .ob_refcnt = 1, .ob_type = null },
        .m_init = null,
        .m_index = 0,
        .m_copy = null,
    },
    .m_name = "hello_world",
    .m_doc = null,
    .m_size = -1,
    .m_methods = &methods,
    .m_slots = null,
    .m_traverse = null,
    .m_clear = null,
    .m_free = null,
};

pub export fn PyInit_hello_world() ?*PyObject {
    return PyModule_Create2(&module_def, 1013);
}
