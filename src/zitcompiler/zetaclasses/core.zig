//! Comptime slot generators for zetaclass native dataclasses.
//!
//! Expected usage in generated params.zig:
//!
//!   const core = @import("core");
//!
//!   const PersonData = struct {
//!       name: [:0]const u8 = "John",
//!       age: i64 = 35,
//!       height: f64 = 1.77,
//!   };
//!
//!   pub const PersonObject = core.wrapAsPythonObject(PersonData);
//!
//!   pub export var PersonType: core.PyTypeObject =
//!       core.makeTypeObject(PersonObject, "Person", .{});
//!
//! All defaults use Zig inline field syntax. [:0]const u8 string defaults are
//! heap-copied on init to maintain the ownership invariant (every non-empty
//! string field is heap-allocated and owned by the struct instance).
//! Fields with no default simply omit the declaration; missing arguments at
//! init time will raise TypeError.
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

pub const PyGetSetDef = extern struct {
    name: ?[*:0]const u8,
    get: ?*anyopaque,
    set: ?*anyopaque,
    doc: ?[*:0]const u8,
    closure: ?*anyopaque,
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
    tp_getset: ?[*]PyGetSetDef,
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
extern fn PyDict_Size(dict: ?*PyObject) Py_ssize_t;
extern fn PyErr_SetString(exc: ?*PyObject, msg: [*:0]const u8) void;
extern fn PyErr_Occurred() ?*PyObject;
extern fn PyObject_RichCompareBool(a: ?*PyObject, b: ?*PyObject, op: c_int) c_int;
extern fn PyObject_Free(ptr: ?*anyopaque) void;
extern fn PyObject_Repr(obj: ?*PyObject) ?*PyObject;
extern fn PyUnicode_Concat(left: ?*PyObject, right: ?*PyObject) ?*PyObject;
extern fn PyLong_FromLongLong(v: c_longlong) ?*PyObject;
extern fn PyFloat_FromDouble(v: f64) ?*PyObject;
extern fn PyObject_GC_UnTrack(op: ?*anyopaque) void;
extern fn PyObject_ClearManagedDict(op: ?*PyObject) void;
extern fn PyObject_ClearWeakRefs(op: ?*PyObject) void;
extern fn PyUnicode_AsUTF8AndSize(unicode: ?*PyObject, size: *Py_ssize_t) ?[*]const u8;
extern fn PyUnicode_FromStringAndSize(u: ?[*]const u8, size: Py_ssize_t) ?*PyObject;
extern fn PyMem_Malloc(n: usize) ?*anyopaque;
extern fn PyMem_Free(p: ?*anyopaque) void;
extern var PyExc_TypeError: *PyObject;
extern var PyExc_AttributeError: *PyObject;
extern var PyExc_MemoryError: *PyObject;
extern var _Py_TrueStruct: PyObject;
extern var _Py_FalseStruct: PyObject;
extern var _Py_NotImplementedStruct: PyObject;

const Py_LT: c_int = 0;
const Py_LE: c_int = 1;
const Py_EQ: c_int = 2;
const Py_NE: c_int = 3;
const Py_GT: c_int = 4;
const Py_GE: c_int = 5;
const Py_TPFLAGS_BASETYPE: c_ulong = 1 << 10;
const Py_TPFLAGS_MANAGED_WEAKREF: c_ulong = 1 << 3;
const Py_TPFLAGS_MANAGED_DICT: c_ulong = 1 << 4;
const Py_TPFLAGS_HEAPTYPE: c_ulong = 1 << 9;
const Py_TPFLAGS_HAVE_GC: c_ulong = 1 << 14;

// PyMemberDef type codes (descrobject.h, Python 3.12+; structmember.h aliases these)
const Py_T_DOUBLE: c_int = 4;
const Py_T_LONGLONG: c_int = 17;

// ── Public comptime helpers ───────────────────────────────────────────────────

/// Wraps a data struct as a Python object struct by prepending `ob_base: PyObject`.
/// The returned type is suitable for use as the Object struct in makeTypeObject.
pub fn wrapAsPythonObject(comptime DataType: type) type {
    const T = struct {
        ob_base: PyObject,
        data: DataType,
    };
    comptime std.debug.assert(@offsetOf(T, "ob_base") == 0);
    return T;
}

// ── Internal comptime helpers ─────────────────────────────────────────────────

fn assertObBase(comptime T: type) void {
    const flds = @typeInfo(T).@"struct".fields;
    if (flds.len == 0 or !std.mem.eql(u8, flds[0].name, "ob_base"))
        @compileError(@typeName(T) ++ ": first field must be `ob_base: PyObject`");
}

/// Returns the type of the `data` field (second field of the Object struct).
fn getDataType(comptime T: type) type {
    const flds = @typeInfo(T).@"struct".fields;
    if (flds.len < 2 or !std.mem.eql(u8, flds[1].name, "data"))
        @compileError(@typeName(T) ++ ": expected second field `data`");
    return flds[1].type;
}

fn memberTypeCode(comptime FieldType: type) c_int {
    return switch (FieldType) {
        i64 => Py_T_LONGLONG,
        f64 => Py_T_DOUBLE,
        else => @compileError("unsupported zetaclass field type for tp_members: " ++ @typeName(FieldType)),
    };
}

fn hasStringFields(comptime T: type) bool {
    const DataType = getDataType(T);
    inline for (@typeInfo(DataType).@"struct".fields) |field| {
        if (field.type == [:0]const u8) return true;
    }
    return false;
}

// Store a Python arg into a struct field.
// For [:0]const u8: extracts UTF-8 bytes, frees the previous allocation, copies to new heap buffer.
fn storeField(comptime FieldType: type, dest: *FieldType, arg: ?*PyObject) void {
    switch (FieldType) {
        i64 => dest.* = @as(i64, @intCast(PyLong_AsLongLong(arg))),
        f64 => dest.* = PyFloat_AsDouble(arg),
        [:0]const u8 => {
            var size: Py_ssize_t = 0;
            const ptr = PyUnicode_AsUTF8AndSize(arg, &size) orelse return;
            const n: usize = @intCast(size);
            const old = dest.*;
            if (old.len > 0) PyMem_Free(@ptrCast(@constCast(old.ptr)));
            if (n == 0) {
                dest.* = "";
                return;
            }
            const buf: [*]u8 = @ptrCast(PyMem_Malloc(n + 1) orelse {
                PyErr_SetString(PyExc_MemoryError, "zetaclass: out of memory for string field");
                return;
            });
            @memcpy(buf[0..n], ptr[0..n]);
            buf[n] = 0;
            dest.* = buf[0..n :0];
        },
        else => @compileError("unsupported zetaclass field type: " ++ @typeName(FieldType)),
    }
}

// ── tp_members array ──────────────────────────────────────────────────────────

/// Returns a namespace with a static `array: [N+1]PyMemberDef` for numeric fields.
/// [:0]const u8 (string) fields are excluded — they are exposed via tp_getset instead.
pub fn membersArray(comptime T: type) type {
    comptime assertObBase(T);
    const DataType = getDataType(T);
    const data_fields = @typeInfo(DataType).@"struct".fields;
    const data_offset = @offsetOf(T, "data");

    comptime var N: usize = 0;
    inline for (data_fields) |field| {
        if (field.type != [:0]const u8) N += 1;
    }

    comptime var init_array: [N + 1]PyMemberDef = std.mem.zeroes([N + 1]PyMemberDef);
    comptime var idx: usize = 0;
    inline for (data_fields) |field| {
        if (field.type != [:0]const u8) {
            init_array[idx] = .{
                .name = @ptrCast(field.name.ptr),
                .member_type = memberTypeCode(field.type),
                .offset = @intCast(data_offset + @offsetOf(DataType, field.name)),
                .flags = 0,
                .doc = null,
            };
            idx += 1;
        }
    }
    const members_init = init_array;
    return struct {
        pub var array: [N + 1]PyMemberDef = members_init;
    };
}

// ── tp_getset array ───────────────────────────────────────────────────────────

/// Returns a namespace with a static `array: [N+1]PyGetSetDef` for [:0]const u8 fields.
/// The getter returns a new Python str from the stored bytes.
/// The setter extracts UTF-8 bytes, frees the old buffer, copies the new bytes.
/// When frozen=true the set pointer is null (making the field read-only at the descriptor level).
pub fn getsetArray(comptime T: type, comptime frozen: bool) type {
    comptime assertObBase(T);
    const DataType = getDataType(T);
    const data_fields = @typeInfo(DataType).@"struct".fields;

    comptime var N: usize = 0;
    inline for (data_fields) |field| {
        if (field.type == [:0]const u8) N += 1;
    }

    comptime var init_array: [N + 1]PyGetSetDef = std.mem.zeroes([N + 1]PyGetSetDef);
    comptime var idx: usize = 0;
    inline for (data_fields) |field| {
        if (field.type == [:0]const u8) {
            const FieldAccessor = struct {
                fn get(self_obj: ?*PyObject, _: ?*anyopaque) callconv(.c) ?*PyObject {
                    const self: *T = @ptrCast(@alignCast(self_obj.?));
                    const s = @field(self.data, field.name);
                    return PyUnicode_FromStringAndSize(s.ptr, @intCast(s.len));
                }
                fn set(self_obj: ?*PyObject, value: ?*PyObject, _: ?*anyopaque) callconv(.c) c_int {
                    const self: *T = @ptrCast(@alignCast(self_obj.?));
                    var size: Py_ssize_t = 0;
                    const ptr = PyUnicode_AsUTF8AndSize(value, &size) orelse return -1;
                    const n: usize = @intCast(size);
                    const old = @field(self.data, field.name);
                    if (old.len > 0) PyMem_Free(@ptrCast(@constCast(old.ptr)));
                    if (n == 0) {
                        @field(self.data, field.name) = "";
                        return 0;
                    }
                    const buf: [*]u8 = @ptrCast(PyMem_Malloc(n + 1) orelse {
                        PyErr_SetString(PyExc_MemoryError, "zetaclass: out of memory for string setter");
                        return -1;
                    });
                    @memcpy(buf[0..n], ptr[0..n]);
                    buf[n] = 0;
                    @field(self.data, field.name) = buf[0..n :0];
                    return 0;
                }
            };
            init_array[idx] = .{
                .name = @ptrCast(field.name.ptr),
                .get = @ptrCast(@constCast(&FieldAccessor.get)),
                .set = if (frozen) null else @ptrCast(@constCast(&FieldAccessor.set)),
                .doc = null,
                .closure = null,
            };
            idx += 1;
        }
    }
    const getset_init = init_array;
    return struct {
        pub var array: [N + 1]PyGetSetDef = getset_init;
    };
}

// ── tp_init ───────────────────────────────────────────────────────────────────

/// Returns a namespace containing `call`, suitable for use as tp_init.
///
/// Fields are populated in declaration order from positional args, then keyword
/// args by field name, then inline struct field defaults via field.defaultValue().
/// [:0]const u8 defaults are heap-copied to maintain the ownership invariant.
pub fn initFn(comptime T: type, comptime kw_only: bool) type {
    comptime assertObBase(T);
    const DataType = getDataType(T);
    return struct {
        pub fn call(
            self_obj: ?*PyObject,
            args: ?*PyObject,
            kwargs: ?*PyObject,
        ) callconv(.c) c_int {
            const self: *T = @ptrCast(@alignCast(self_obj.?));
            const nargs: usize = if (args != null) @intCast(PyTuple_Size(args)) else 0;
            if (kw_only and nargs > 0) {
                PyErr_SetString(PyExc_TypeError, "zetaclass __init__() takes 0 positional arguments (kw_only=True)");
                return -1;
            }
            inline for (@typeInfo(DataType).@"struct".fields, 0..) |field, i| {
                const arg: ?*PyObject = if (!kw_only and i < nargs)
                    PyTuple_GetItem(args, @intCast(i))
                else if (kwargs != null)
                    PyDict_GetItemString(kwargs, @as([*:0]const u8, @ptrCast(field.name.ptr)))
                else
                    null;

                if (arg != null) {
                    storeField(field.type, &@field(self.data, field.name), arg);
                    if (PyErr_Occurred() != null) return -1;
                } else if (field.defaultValue()) |dv| {
                    if (field.type == [:0]const u8) {
                        const n = dv.len;
                        const old = @field(self.data, field.name);
                        if (old.len > 0) PyMem_Free(@ptrCast(@constCast(old.ptr)));
                        if (n == 0) {
                            @field(self.data, field.name) = "";
                        } else {
                            const buf: [*]u8 = @ptrCast(PyMem_Malloc(n + 1) orelse {
                                PyErr_SetString(PyExc_MemoryError, "zetaclass __init__: out of memory for string default");
                                return -1;
                            });
                            @memcpy(buf[0..n], dv[0..n]);
                            buf[n] = 0;
                            @field(self.data, field.name) = buf[0..n :0];
                        }
                    } else {
                        @field(self.data, field.name) = dv;
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

// ── tp_init (init=False) ──────────────────────────────────────────────────────

/// tp_init slot used when init=False: accepts no arguments, mirrors object.__init__
/// behavior on a type that has a custom tp_new (PyType_GenericNew doesn't suppress
/// the check that object_init would otherwise do).
pub fn noInitFn() type {
    return struct {
        pub fn call(
            self_obj: ?*PyObject,
            args: ?*PyObject,
            kwargs: ?*PyObject,
        ) callconv(.c) c_int {
            _ = self_obj;
            const nargs: usize = if (args != null) @intCast(PyTuple_Size(args)) else 0;
            const has_kwargs = kwargs != null and PyDict_Size(kwargs) > 0;
            if (nargs > 0 or has_kwargs) {
                PyErr_SetString(PyExc_TypeError, "zetaclass with init=False takes no arguments");
                return -1;
            }
            return 0;
        }
    };
}

// ── tp_richcompare ────────────────────────────────────────────────────────────

/// Lexicographic ordering result over fields: .lt, .eq, or .gt.
const FieldOrder = enum { lt, eq, gt };

fn compareFields(comptime T: type, a: *const T, b: *const T) FieldOrder {
    const DataType = getDataType(T);
    inline for (@typeInfo(DataType).@"struct".fields) |field| {
        switch (field.type) {
            i64, f64 => {
                const av = @field(a.data, field.name);
                const bv = @field(b.data, field.name);
                if (av < bv) return .lt;
                if (av > bv) return .gt;
            },
            [:0]const u8 => {
                const ord = std.mem.order(u8, @field(a.data, field.name), @field(b.data, field.name));
                switch (ord) {
                    .lt => return .lt,
                    .gt => return .gt,
                    .eq => {},
                }
            },
            else => @compileError("unsupported field type: " ++ @typeName(field.type)),
        }
    }
    return .eq;
}

/// Returns a namespace containing `call`, suitable for use as tp_richcompare.
///
/// When order=false only Py_EQ/Py_NE are handled; other ops return NotImplemented.
/// When order=true all six comparison ops are handled via lexicographic field comparison.
pub fn richCompareFn(comptime T: type, comptime order: bool) type {
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
            if (!order and op != Py_EQ and op != Py_NE) {
                Py_IncRef(&_Py_NotImplementedStruct);
                return &_Py_NotImplementedStruct;
            }
            const a: *const T = @ptrCast(@alignCast(a_obj));
            const b: *const T = @ptrCast(@alignCast(b_obj));
            const ord = compareFields(T, a, b);
            const result = switch (op) {
                Py_EQ => ord == .eq,
                Py_NE => ord != .eq,
                Py_LT => ord == .lt,
                Py_LE => ord == .lt or ord == .eq,
                Py_GT => ord == .gt,
                Py_GE => ord == .gt or ord == .eq,
                else => {
                    Py_IncRef(&_Py_NotImplementedStruct);
                    return &_Py_NotImplementedStruct;
                },
            };
            const ret: *PyObject = if (result) &_Py_TrueStruct else &_Py_FalseStruct;
            Py_IncRef(ret);
            return ret;
        }
    };
}

// ── string builder helper ─────────────────────────────────────────────────────

/// Appends `piece` onto `*acc` via PyUnicode_Concat, consuming both references.
/// If either is null (a prior operation failed), propagates null through `*acc`.
fn appendConcat(acc: *?*PyObject, piece: ?*PyObject) void {
    if (acc.* == null) {
        if (piece) |p| Py_DecRef(p);
        return;
    }
    if (piece == null) {
        Py_DecRef(acc.*);
        acc.* = null;
        return;
    }
    const next = PyUnicode_Concat(acc.*, piece);
    Py_DecRef(acc.*);
    Py_DecRef(piece);
    acc.* = next;
}

// ── tp_repr ───────────────────────────────────────────────────────────────────

/// Returns a namespace containing `call`, suitable for use as tp_repr.
/// Produces "ClassName(field1=repr(val1), field2=repr(val2), ...)".
pub fn reprFn(comptime T: type, comptime class_name: [:0]const u8) type {
    comptime assertObBase(T);
    const DataType = getDataType(T);
    return struct {
        pub fn call(self_obj: ?*PyObject) callconv(.c) ?*PyObject {
            const self: *const T = @ptrCast(@alignCast(self_obj.?));
            var result: ?*PyObject = PyUnicode_FromStringAndSize(class_name.ptr, @intCast(class_name.len));
            appendConcat(&result, PyUnicode_FromStringAndSize("(", 1));
            inline for (@typeInfo(DataType).@"struct".fields, 0..) |field, i| {
                if (i > 0) appendConcat(&result, PyUnicode_FromStringAndSize(", ", 2));
                appendConcat(&result, PyUnicode_FromStringAndSize(field.name.ptr, @intCast(field.name.len)));
                appendConcat(&result, PyUnicode_FromStringAndSize("=", 1));
                const val_repr: ?*PyObject = blk: {
                    const val_obj: ?*PyObject = switch (field.type) {
                        i64 => PyLong_FromLongLong(@as(c_longlong, @intCast(@field(self.data, field.name)))),
                        f64 => PyFloat_FromDouble(@field(self.data, field.name)),
                        [:0]const u8 => PyUnicode_FromStringAndSize(
                            @field(self.data, field.name).ptr,
                            @intCast(@field(self.data, field.name).len),
                        ),
                        else => @compileError("unsupported field type: " ++ @typeName(field.type)),
                    };
                    if (val_obj) |vo| {
                        defer Py_DecRef(vo);
                        break :blk PyObject_Repr(vo);
                    }
                    break :blk null;
                };
                if (val_repr == null) {
                    if (result) |r| Py_DecRef(r);
                    return null;
                }
                appendConcat(&result, val_repr);
            }
            appendConcat(&result, PyUnicode_FromStringAndSize(")", 1));
            return result;
        }
    };
}

// ── tp_dealloc ────────────────────────────────────────────────────────────────

/// Returns a namespace containing `call` for tp_dealloc.
/// Frees heap-allocated [:0]const u8 fields, then frees the object memory.
/// Only used for types that have string fields; otherwise tp_dealloc is left null
/// and PyType_Ready inherits the default from object.
///
/// This deallocator is inherited by Python-level subclasses created via
/// `type(name, (NativeType,), ...)` (which is how @zetaclass produces the final
/// type). Such subclasses are heap types: they add a managed __dict__ and the
/// Py_TPFLAGS_HAVE_GC flag, so their instances are GC-tracked and allocated with a
/// gc_head prefix. It must therefore mirror CPython's subtype_dealloc: untrack from
/// the GC list, release the managed dict/weakrefs, free via the type's own tp_free
/// (PyObject_GC_Del for GC types — NOT PyObject_Free, which would free the wrong
/// block), and drop the instance's reference to its heap type.
pub fn deallocFn(comptime T: type) type {
    const DataType = getDataType(T);
    return struct {
        pub fn call(self_obj: ?*PyObject) callconv(.c) void {
            const self: *T = @ptrCast(@alignCast(self_obj.?));
            const hdr: *PyObject = @ptrCast(@alignCast(self_obj.?));
            const tp: *PyTypeObject = @ptrCast(@alignCast(hdr.ob_type.?));

            // Remove from the GC list before freeing, or the next collection
            // walks a dangling gc_head and crashes.
            if ((tp.tp_flags & Py_TPFLAGS_HAVE_GC) != 0) {
                PyObject_GC_UnTrack(@ptrCast(self_obj));
            }
            if ((tp.tp_flags & Py_TPFLAGS_MANAGED_WEAKREF) != 0) {
                PyObject_ClearWeakRefs(self_obj);
            }

            inline for (@typeInfo(DataType).@"struct".fields) |field| {
                if (field.type == [:0]const u8) {
                    const s = @field(self.data, field.name);
                    if (s.len > 0) PyMem_Free(@ptrCast(@constCast(s.ptr)));
                }
            }

            // Subclasses created from Python carry a managed __dict__ that the
            // base type's deallocator owns the release of.
            if ((tp.tp_flags & Py_TPFLAGS_MANAGED_DICT) != 0) {
                PyObject_ClearManagedDict(self_obj);
            }

            const free_fn: *const fn (?*anyopaque) callconv(.c) void = @ptrCast(tp.tp_free.?);
            free_fn(self_obj);

            // Instances of a heap type hold a strong reference to that type.
            if ((tp.tp_flags & Py_TPFLAGS_HEAPTYPE) != 0) {
                Py_DecRef(@ptrCast(tp));
            }
        }
    };
}

// These are kept for use by custom Zig code that may reference PyObject fields directly.
extern fn Py_IncRef(obj: ?*PyObject) void;
extern fn Py_DecRef(obj: ?*PyObject) void;

// ── tp_hash ───────────────────────────────────────────────────────────────────

/// Returns a namespace containing `call`, suitable for use as tp_hash.
/// Hashes the data struct using Wyhash over all fields' raw bytes / string contents.
/// -1 is mapped to -2 (Python uses -1 as the error sentinel for tp_hash).
pub fn hashFn(comptime T: type) type {
    comptime assertObBase(T);
    const DataType = getDataType(T);
    return struct {
        pub fn call(self_obj: ?*PyObject) callconv(.c) Py_ssize_t {
            const self: *const T = @ptrCast(@alignCast(self_obj.?));
            var hasher = std.hash.Wyhash.init(0);
            inline for (@typeInfo(DataType).@"struct".fields) |field| {
                switch (field.type) {
                    i64 => std.hash.autoHash(&hasher, @field(self.data, field.name)),
                    f64 => std.hash.autoHash(&hasher, @as(u64, @bitCast(@field(self.data, field.name)))),
                    [:0]const u8 => hasher.update(@field(self.data, field.name)),
                    else => @compileError("unsupported field type: " ++ @typeName(field.type)),
                }
            }
            const raw: usize = @truncate(hasher.final());
            const result: Py_ssize_t = @bitCast(raw);
            return if (result == -1) -2 else result;
        }
    };
}

// ── tp_setattro (frozen) ──────────────────────────────────────────────────────

/// tp_setattro slot for frozen types: always raises AttributeError.
pub fn frozenSetAttrFn() type {
    return struct {
        pub fn call(self_obj: ?*PyObject, name: ?*PyObject, value: ?*PyObject) callconv(.c) c_int {
            _ = self_obj;
            _ = name;
            _ = value;
            PyErr_SetString(PyExc_AttributeError, "cannot assign to field of frozen instance");
            return -1;
        }
    };
}

// ── makeTypeObject ────────────────────────────────────────────────────────────

/// Options controlling which slots are wired into the generated type.
/// Mirror the keyword arguments accepted by Python's @dataclass decorator.
pub const makeTypeOptions = struct {
    /// Wire tp_init; set false when init=False is passed to @zetaclass.
    init: bool = true,
    /// Wire tp_repr; set false when repr=False is passed to @zetaclass.
    repr: bool = true,
    /// Wire tp_richcompare for eq/ne; set false when eq=False is passed to @zetaclass.
    eq: bool = true,
    /// Wire tp_richcompare for lt/le/gt/ge; requires eq=true.
    order: bool = false,
    /// Wire tp_hash; set when frozen=True or unsafe_hash=True.
    hash: bool = false,
    /// Wire tp_setattro to reject mutation; set when frozen=True.
    frozen: bool = false,
    /// Force __init__ to accept keyword arguments only (no positional args).
    kw_only: bool = false,
    /// Add Py_TPFLAGS_MANAGED_WEAKREF to enable weakref support.
    weakref_slot: bool = false,
};

/// Build a PyTypeObject for an Object struct of the form:
///   struct { ob_base: PyObject, data: SomeDataStruct }
/// Assign to an `export var` in generated params.zig, then load via load_class().
///
/// All defaults use Zig inline field syntax; [:0]const u8 defaults are heap-copied on init.
/// Numeric defaults use Zig inline field syntax.
/// opts: makeTypeOptions controlling which slots are generated.
pub fn makeTypeObject(
    comptime T: type,
    comptime name: [:0]const u8,
    comptime opts: makeTypeOptions,
) PyTypeObject {
    return PyTypeObject{
        .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
        .tp_name = name.ptr,
        .tp_basicsize = @sizeOf(T),
        .tp_itemsize = 0,
        .tp_dealloc = if (hasStringFields(T))
            @ptrCast(@constCast(&deallocFn(T).call))
        else
            null,
        .tp_vectorcall_offset = 0,
        .tp_getattr = null,
        .tp_setattr = null,
        .tp_as_async = null,
        .tp_repr = if (opts.repr) @ptrCast(@constCast(&reprFn(T, name).call)) else null,
        .tp_as_number = null,
        .tp_as_sequence = null,
        .tp_as_mapping = null,
        .tp_hash = if (opts.hash) @ptrCast(@constCast(&hashFn(T).call)) else null,
        .tp_call = null,
        .tp_str = null,
        .tp_getattro = null,
        .tp_setattro = if (opts.frozen) @ptrCast(@constCast(&frozenSetAttrFn().call)) else null,
        .tp_as_buffer = null,
        .tp_flags = Py_TPFLAGS_BASETYPE | (if (opts.weakref_slot) Py_TPFLAGS_MANAGED_WEAKREF else 0),
        .tp_doc = null,
        .tp_traverse = null,
        .tp_clear = null,
        .tp_richcompare = if (opts.eq) @ptrCast(@constCast(&richCompareFn(T, opts.order).call)) else null,
        .tp_weaklistoffset = 0,
        .tp_iter = null,
        .tp_iternext = null,
        .tp_methods = null,
        .tp_members = &membersArray(T).array,
        .tp_getset = if (hasStringFields(T)) &getsetArray(T, opts.frozen).array else null,
        .tp_base = null,
        .tp_dict = null,
        .tp_descr_get = null,
        .tp_descr_set = null,
        .tp_dictoffset = 0,
        .tp_init = if (opts.init)
            @ptrCast(@constCast(&initFn(T, opts.kw_only).call))
        else
            @ptrCast(@constCast(&noInitFn().call)),
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
