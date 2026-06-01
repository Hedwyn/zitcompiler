const std = @import("std");
const params = @import("params");

const Py_ssize_t = isize;

const PyObject = extern struct {
    ob_refcnt: i64,
    ob_type: ?*anyopaque,
};

const PyVarObject = extern struct {
    ob_base: PyObject,
    ob_size: Py_ssize_t,
};

const PyCFunction = *const fn (?*PyObject, ?*PyObject) callconv(.c) ?*PyObject;
const METH_NOARGS: c_int = 4;

const PyMethodDef = extern struct {
    ml_name: ?[*:0]const u8,
    ml_meth: ?PyCFunction,
    ml_flags: c_int,
    ml_doc: ?[*:0]const u8,
};

// newfunc: PyObject *(*)(PyTypeObject *, PyObject *, PyObject *)
const NewFunc = *const fn (*PyTypeObject, ?*PyObject, ?*PyObject) callconv(.c) ?*PyObject;

const PyTypeObject = extern struct {
    ob_base: PyVarObject,
    tp_name: ?[*:0]const u8,
    tp_basicsize: Py_ssize_t,
    tp_itemsize: Py_ssize_t,
    tp_dealloc: ?*anyopaque,
    tp_vectorcall_offset: Py_ssize_t,
    tp_getattr: ?*anyopaque,
    tp_setattr: ?*anyopaque,
    tp_as_async: ?*anyopaque,
    tp_repr: ?*anyopaque,
    tp_as_number: ?*anyopaque,
    tp_as_sequence: ?*anyopaque,
    tp_as_mapping: ?*anyopaque,
    tp_hash: ?*anyopaque,
    tp_call: ?*anyopaque,
    tp_str: ?*anyopaque,
    tp_getattro: ?*anyopaque,
    tp_setattro: ?*anyopaque,
    tp_as_buffer: ?*anyopaque,
    tp_flags: c_ulong,
    tp_doc: ?[*:0]const u8,
    tp_traverse: ?*anyopaque,
    tp_clear: ?*anyopaque,
    tp_richcompare: ?*anyopaque,
    tp_weaklistoffset: Py_ssize_t,
    tp_iter: ?*anyopaque,
    tp_iternext: ?*anyopaque,
    tp_methods: ?[*]PyMethodDef,
    tp_members: ?*anyopaque,
    tp_getset: ?*anyopaque,
    tp_base: ?*PyTypeObject,
    tp_dict: ?*PyObject,
    tp_descr_get: ?*anyopaque,
    tp_descr_set: ?*anyopaque,
    tp_dictoffset: Py_ssize_t,
    tp_init: ?*anyopaque,
    tp_alloc: ?*anyopaque,
    tp_new: ?NewFunc,
    tp_free: ?*anyopaque,
    tp_is_gc: ?*anyopaque,
    tp_bases: ?*PyObject,
    tp_mro: ?*PyObject,
    tp_cache: ?*PyObject,
    tp_subclasses: ?*anyopaque,
    tp_weaklist: ?*PyObject,
    tp_del: ?*anyopaque,
    tp_version_tag: c_uint,
    tp_finalize: ?*anyopaque,
    tp_vectorcall: ?*anyopaque,
    tp_watched: u8,
    tp_versions_used: u16,
};

comptime {
    std.debug.assert(@sizeOf(PyTypeObject) == 416);
}

const GreeterObject = extern struct {
    ob_base: PyObject,
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
extern fn PyModule_AddObjectRef(mod: ?*PyObject, name: [*:0]const u8, value: ?*PyObject) c_int;
extern fn PyType_Ready(tp: *PyTypeObject) c_int;
extern fn PyType_GenericNew(tp: *PyTypeObject, args: ?*PyObject, kwds: ?*PyObject) ?*PyObject;
extern fn Py_IncRef(obj: ?*PyObject) void;
extern fn Py_DecRef(obj: ?*PyObject) void;
extern var _Py_NoneStruct: PyObject;

fn greeter_hello_world(self: ?*PyObject, args: ?*PyObject) callconv(.c) ?*PyObject {
    _ = self;
    _ = args;
    std.debug.print("{s}\n", .{params.hello});
    Py_IncRef(&_Py_NoneStruct);
    return &_Py_NoneStruct;
}

var greeter_methods = [_]PyMethodDef{
    .{ .ml_name = "hello_world", .ml_meth = greeter_hello_world, .ml_flags = METH_NOARGS, .ml_doc = null },
    .{ .ml_name = null, .ml_meth = null, .ml_flags = 0, .ml_doc = null },
};

export var GreeterType = PyTypeObject{
    .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
    .tp_name = "greeter.Greeter",
    .tp_basicsize = @sizeOf(GreeterObject),
    .tp_itemsize = 0,
    .tp_dealloc = null,
    .tp_vectorcall_offset = 0,
    .tp_getattr = null,
    .tp_setattr = null,
    .tp_as_async = null,
    .tp_repr = null,
    .tp_as_number = null,
    .tp_as_sequence = null,
    .tp_as_mapping = null,
    .tp_hash = null,
    .tp_call = null,
    .tp_str = null,
    .tp_getattro = null,
    .tp_setattro = null,
    .tp_as_buffer = null,
    .tp_flags = 0,
    .tp_doc = "Greeter class",
    .tp_traverse = null,
    .tp_clear = null,
    .tp_richcompare = null,
    .tp_weaklistoffset = 0,
    .tp_iter = null,
    .tp_iternext = null,
    .tp_methods = &greeter_methods,
    .tp_members = null,
    .tp_getset = null,
    .tp_base = null,
    .tp_dict = null,
    .tp_descr_get = null,
    .tp_descr_set = null,
    .tp_dictoffset = 0,
    .tp_init = null,
    .tp_alloc = null,
    .tp_new = &PyType_GenericNew,
    .tp_free = null,
    .tp_is_gc = null,
    .tp_bases = null,
    .tp_mro = null,
    .tp_cache = null,
    .tp_subclasses = null,
    .tp_weaklist = null,
    .tp_del = null,
    .tp_version_tag = 0,
    .tp_finalize = null,
    .tp_vectorcall = null,
    .tp_watched = 0,
    .tp_versions_used = 0,
};

var module_def = PyModuleDef{
    .m_base = .{
        .ob_base = .{ .ob_refcnt = 1, .ob_type = null },
        .m_init = null,
        .m_index = 0,
        .m_copy = null,
    },
    .m_name = "greeter",
    .m_doc = null,
    .m_size = -1,
    .m_methods = null,
    .m_slots = null,
    .m_traverse = null,
    .m_clear = null,
    .m_free = null,
};

pub export fn PyInit_greeter() ?*PyObject {
    if (PyType_Ready(&GreeterType) < 0) return null;

    const mod = PyModule_Create2(&module_def, 1013) orelse return null;
    if (PyModule_AddObjectRef(mod, "Greeter", @ptrCast(&GreeterType)) < 0) {
        Py_DecRef(mod);
        return null;
    }
    return mod;
}
