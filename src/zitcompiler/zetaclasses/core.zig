//! Comptime slot generators for zetaclass native dataclasses.
//!
//! Expected usage in generated params.zig:
//!
//!   const core = @import("core");
//!
//!   pub const PointObject = extern struct {
//!       ob_base: core.PyObject,
//!       x: i64,
//!       y: i64,
//!   };
//!
//!   pub export var PointType: core.PyTypeObject =
//!       core.makeTypeObject(PointObject, core.NoDefaults, "Point");
//!
//! For default values, pass a struct with pub const fields matching field names:
//!
//!   const PersonDefaults = struct {
//!       pub const name: [:0]const u8 = "John";  // str fields use C-string slice
//!       pub const age: i64 = 35;
//!       pub const height: f64 = 1.77;
//!   };
//!   pub export var PersonType: core.PyTypeObject =
//!       core.makeTypeObject(PersonObject, PersonDefaults, "Person");
//!
//! The struct must have `ob_base: core.PyObject` as its first field.
//! Supported field types: i64, f64, ?*PyObject (for Python str/object fields).
//! @date: 04.06.2026
//! @author: Baptiste Pestourie

const std = @import("std");

// ── Python C API ──────────────────────────────────────────────────────────────

pub const Py_ssize_t = isize;

pub const PyObject = extern struct {
    ob_refcnt: i64,
    ob_type: ?*anyopaque,
};

const PyVarObject = extern struct {
    ob_base: PyObject,
    ob_size: Py_ssize_t,
};

const PyMethodDef = extern struct {
    ml_name: ?[*:0]const u8,
    ml_meth: ?*anyopaque,
    ml_flags: c_int,
    ml_doc: ?[*:0]const u8,
};

// Matches C struct PyMemberDef from structmember.h.
// The `type` field is renamed `member_type` to avoid Zig keyword clash;
// layout is identical (extern struct ignores field names).
pub const PyMemberDef = extern struct {
    name: ?[*:0]const u8,
    member_type: c_int,
    offset: Py_ssize_t,
    flags: c_int,
    doc: ?[*:0]const u8,
};

const NewFunc = *const fn (*PyTypeObject, ?*PyObject, ?*PyObject) callconv(.c) ?*PyObject;

pub const PyTypeObject = extern struct {
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
    tp_members: ?[*]PyMemberDef,
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

extern fn PyType_GenericNew(tp: *PyTypeObject, args: ?*PyObject, kwds: ?*PyObject) ?*PyObject;
extern fn PyLong_AsLongLong(obj: ?*PyObject) c_longlong;
extern fn PyFloat_AsDouble(obj: ?*PyObject) f64;
extern fn PyTuple_Size(obj: ?*PyObject) Py_ssize_t;
extern fn PyTuple_GetItem(obj: ?*PyObject, i: Py_ssize_t) ?*PyObject;
extern fn PyDict_GetItemString(dict: ?*PyObject, key: [*:0]const u8) ?*PyObject;
extern fn PyErr_SetString(exc: ?*PyObject, msg: [*:0]const u8) void;
extern fn PyErr_Occurred() ?*PyObject;
extern fn PyObject_RichCompareBool(a: ?*PyObject, b: ?*PyObject, op: c_int) c_int;
extern fn PyObject_Free(ptr: ?*anyopaque) void;
extern fn PyUnicode_FromString(s: [*:0]const u8) ?*PyObject;
extern var PyExc_TypeError: *PyObject;
extern fn Py_IncRef(obj: ?*PyObject) void;
extern fn Py_DecRef(obj: ?*PyObject) void;
extern var _Py_TrueStruct: PyObject;
extern var _Py_FalseStruct: PyObject;
extern var _Py_NotImplementedStruct: PyObject;

const Py_EQ: c_int = 2;
const Py_NE: c_int = 3;

// PyMemberDef type codes (descrobject.h, Python 3.12+; structmember.h aliases these)
const Py_T_DOUBLE: c_int = 4;
const Py_T_OBJECT_EX: c_int = 16;
const Py_T_LONGLONG: c_int = 17;

/// Pass as Defaults when the class has no default field values.
pub const NoDefaults = struct {};

// ── Comptime helpers ──────────────────────────────────────────────────────────

fn assertObBase(comptime T: type) void {
    const flds = @typeInfo(T).@"struct".fields;
    if (flds.len == 0 or !std.mem.eql(u8, flds[0].name, "ob_base"))
        @compileError(@typeName(T) ++ ": first field must be `ob_base: PyObject`");
}

fn memberTypeCode(comptime FieldType: type) c_int {
    return switch (FieldType) {
        i64 => Py_T_LONGLONG,
        f64 => Py_T_DOUBLE,
        ?*PyObject => Py_T_OBJECT_EX,
        else => @compileError("unsupported zetaclass field type: " ++ @typeName(FieldType)),
    };
}

fn hasObjectFields(comptime T: type) bool {
    inline for (@typeInfo(T).@"struct".fields[1..]) |field| {
        if (field.type == ?*PyObject) return true;
    }
    return false;
}

// Store a Python arg into a struct field, handling ref counting for object fields.
// Decrefs the current value first (handles re-initialization).
fn storeField(comptime FieldType: type, dest: *FieldType, arg: ?*PyObject) void {
    switch (FieldType) {
        i64 => dest.* = @as(i64, @intCast(PyLong_AsLongLong(arg))),
        f64 => dest.* = PyFloat_AsDouble(arg),
        ?*PyObject => {
            if (dest.*) |old| Py_DecRef(old);
            Py_IncRef(arg);
            dest.* = arg;
        },
        else => @compileError("unsupported zetaclass field type: " ++ @typeName(FieldType)),
    }
}

// ── tp_members array ──────────────────────────────────────────────────────────

/// Returns a namespace with a static `array: [N+1]PyMemberDef` for struct T.
/// The array is null-sentinel terminated and can be passed directly to tp_members.
pub fn MembersArray(comptime T: type) type {
    comptime assertObBase(T);
    const data_fields = @typeInfo(T).@"struct".fields[1..];
    const N = data_fields.len;
    comptime var init_array = std.mem.zeroes([N + 1]PyMemberDef);
    inline for (data_fields, 0..) |field, i| {
        init_array[i] = .{
            .name = @ptrCast(field.name.ptr),
            .member_type = memberTypeCode(field.type),
            .offset = @intCast(@offsetOf(T, field.name)),
            .flags = 0,
            .doc = null,
        };
    }
    const members_init = init_array;
    return struct {
        pub var array: [N + 1]PyMemberDef = members_init;
    };
}

// ── tp_init ───────────────────────────────────────────────────────────────────

/// Returns a namespace containing `call`, suitable for use as tp_init.
///
/// Fields are populated in declaration order from positional args, then keyword
/// args by field name, then comptime defaults from Defaults (if declared).
/// Use core.NoDefaults when no defaults are needed.
pub fn InitFn(comptime T: type, comptime Defaults: type) type {
    comptime assertObBase(T);
    return struct {
        pub fn call(
            self_obj: ?*PyObject,
            args: ?*PyObject,
            kwargs: ?*PyObject,
        ) callconv(.c) c_int {
            const self: *T = @ptrCast(@alignCast(self_obj.?));
            const nargs: usize = if (args != null) @intCast(PyTuple_Size(args)) else 0;
            inline for (@typeInfo(T).@"struct".fields[1..], 0..) |field, i| {
                const arg: ?*PyObject = if (i < nargs)
                    PyTuple_GetItem(args, @intCast(i))
                else if (kwargs != null)
                    PyDict_GetItemString(kwargs, @as([*:0]const u8, @ptrCast(field.name.ptr)))
                else
                    null;

                if (arg != null) {
                    storeField(field.type, &@field(self, field.name), arg);
                    if (PyErr_Occurred() != null) return -1;
                } else if (@hasDecl(Defaults, field.name)) {
                    const dval = @field(Defaults, field.name);
                    switch (field.type) {
                        i64 => @field(self, field.name) = @as(i64, dval),
                        f64 => @field(self, field.name) = @as(f64, dval),
                        ?*PyObject => {
                            const py_str = PyUnicode_FromString(dval.ptr) orelse return -1;
                            if (@field(self, field.name)) |old| Py_DecRef(old);
                            @field(self, field.name) = py_str;
                        },
                        else => @compileError("unsupported default field type: " ++ @typeName(field.type)),
                    }
                } else {
                    PyErr_SetString(PyExc_TypeError, "zetaclass __init__: missing required argument");
                    return -1;
                }
            }
            return 0;
        }
    };
}

// ── tp_richcompare ────────────────────────────────────────────────────────────

/// Returns a namespace containing `call`, suitable for use as tp_richcompare.
///
/// Handles Py_EQ and Py_NE via field-by-field comparison.
/// Returns Py_NotImplemented for other ops or when operand types differ.
pub fn RichCompareFn(comptime T: type) type {
    comptime assertObBase(T);
    return struct {
        pub fn call(
            a_obj: ?*PyObject,
            b_obj: ?*PyObject,
            op: c_int,
        ) callconv(.c) ?*PyObject {
            if (a_obj == null or b_obj == null) {
                Py_IncRef(&_Py_NotImplementedStruct);
                return &_Py_NotImplementedStruct;
            }
            const a_hdr: *PyObject = @ptrCast(@alignCast(a_obj));
            const b_hdr: *PyObject = @ptrCast(@alignCast(b_obj));
            if (a_hdr.ob_type != b_hdr.ob_type) {
                Py_IncRef(&_Py_NotImplementedStruct);
                return &_Py_NotImplementedStruct;
            }
            if (op != Py_EQ and op != Py_NE) {
                Py_IncRef(&_Py_NotImplementedStruct);
                return &_Py_NotImplementedStruct;
            }
            const a: *const T = @ptrCast(@alignCast(a_obj));
            const b: *const T = @ptrCast(@alignCast(b_obj));
            var equal = true;
            inline for (@typeInfo(T).@"struct".fields[1..]) |field| {
                switch (field.type) {
                    i64, f64 => {
                        if (@field(a, field.name) != @field(b, field.name)) equal = false;
                    },
                    ?*PyObject => {
                        const cmp = PyObject_RichCompareBool(
                            @field(a, field.name),
                            @field(b, field.name),
                            Py_EQ,
                        );
                        if (cmp < 0) return null;
                        if (cmp == 0) equal = false;
                    },
                    else => @compileError("unsupported field type: " ++ @typeName(field.type)),
                }
            }
            const result = if (op == Py_EQ) equal else !equal;
            const ret: *PyObject = if (result) &_Py_TrueStruct else &_Py_FalseStruct;
            Py_IncRef(ret);
            return ret;
        }
    };
}

// ── tp_dealloc ────────────────────────────────────────────────────────────────

/// Returns a namespace containing `call` for tp_dealloc.
/// Decrefs all ?*PyObject fields, then frees the object memory.
/// Only used for types that have object fields; otherwise tp_dealloc is left null
/// and PyType_Ready inherits the default from object.
pub fn DeallocFn(comptime T: type) type {
    return struct {
        pub fn call(self_obj: ?*PyObject) callconv(.c) void {
            const self: *T = @ptrCast(@alignCast(self_obj.?));
            inline for (@typeInfo(T).@"struct".fields[1..]) |field| {
                if (field.type == ?*PyObject) {
                    if (@field(self, field.name)) |obj| Py_DecRef(obj);
                }
            }
            PyObject_Free(self_obj);
        }
    };
}

// ── makeTypeObject ────────────────────────────────────────────────────────────

/// Build a PyTypeObject for extern struct T.
/// Assign to an `export var` in generated params.zig, then load via load_class().
///
/// Defaults: a struct with pub const fields for each field that has a default.
/// Use core.NoDefaults when no defaults are needed.
pub fn makeTypeObject(
    comptime T: type,
    comptime Defaults: type,
    comptime name: [:0]const u8,
) PyTypeObject {
    return PyTypeObject{
        .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
        .tp_name = name.ptr,
        .tp_basicsize = @sizeOf(T),
        .tp_itemsize = 0,
        .tp_dealloc = if (hasObjectFields(T))
            @ptrCast(@constCast(&DeallocFn(T).call))
        else
            null,
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
        .tp_doc = null,
        .tp_traverse = null,
        .tp_clear = null,
        .tp_richcompare = @ptrCast(@constCast(&RichCompareFn(T).call)),
        .tp_weaklistoffset = 0,
        .tp_iter = null,
        .tp_iternext = null,
        .tp_methods = null,
        .tp_members = &MembersArray(T).array,
        .tp_getset = null,
        .tp_base = null,
        .tp_dict = null,
        .tp_descr_get = null,
        .tp_descr_set = null,
        .tp_dictoffset = 0,
        .tp_init = @ptrCast(@constCast(&InitFn(T, Defaults).call)),
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
}
