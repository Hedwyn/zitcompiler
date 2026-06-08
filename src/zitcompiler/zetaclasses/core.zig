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
//!   pub const PersonObject = core.wrapAsPythonObject(PersonData, true, false);
//!
//!   pub export var PersonType: core.PyTypeObject =
//!       core.makeTypeObject(PersonObject, "Person", .{});
//!
//! All defaults use Zig inline field syntax. [:0]const u8 string defaults are
//! heap-copied on init to maintain the ownership invariant (every non-empty
//! string field is heap-allocated and owned by the struct instance).
//! Fields with no default simply omit the declaration; missing arguments at
//! init time will raise TypeError.
//!
//! Each DataType field has a corresponding py_cache slot (?*PyObject) in the
//! wrapper struct. Getters check the cache first (populate on miss, IncRef on
//! return). Setters update both native and cache. Dealloc DecRefs all cached
//! objects.
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
extern fn PyObject_IsInstance(inst: ?*PyObject, cls: ?*PyObject) c_int;
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
extern fn PyObject_Hash(obj: ?*PyObject) Py_ssize_t;
extern var PyExc_TypeError: *PyObject;
extern var PyExc_AttributeError: *PyObject;
extern var PyExc_MemoryError: *PyObject;
extern var PyLong_Type: PyTypeObject;
extern var PyFloat_Type: PyTypeObject;
extern var PyUnicode_Type: PyTypeObject;
extern var _Py_TrueStruct: PyObject;
extern var _Py_FalseStruct: PyObject;
extern var _Py_NotImplementedStruct: PyObject;
extern var PyExc_ValueError: *PyObject;
extern fn PyBytes_FromStringAndSize(v: ?[*]const u8, len: Py_ssize_t) ?*PyObject;
extern fn PyBytes_AsStringAndSize(obj: ?*PyObject, buffer: *[*]u8, length: *Py_ssize_t) c_int;

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

// PyMethodDef ml_flags
const METH_NOARGS: c_int = 0x0004;
const METH_O: c_int = 0x0008;
const METH_CLASS: c_int = 0x0010;
const METH_STATIC: c_int = 0x0020;

// ── Public comptime helpers ───────────────────────────────────────────────────

/// Wraps a data struct as a Python object struct by prepending `ob_base: PyObject`
/// and a `py_cache` array (one ?*PyObject slot per DataType field, null = uncached).
/// The returned type is suitable for use as the Object struct in makeTypeObject.
/// validate: include py_cache (for tp_getset lazy caching).
/// pack:     include data (for pack/unpack native struct access).
/// At least one of validate or pack must be true; both may be true.
/// When validate=false, py_cache is void (zero-size, no storage).
pub fn wrapAsPythonObject(comptime DataType: type, comptime validate: bool, comptime pack: bool) type {
    comptime std.debug.assert(validate or pack);
    const n = @typeInfo(DataType).@"struct".fields.len;
    const CacheType = if (validate) [n]?*PyObject else void;
    const DataField = if (validate or pack) DataType else void;
    const T = struct {
        ob_base: PyObject,
        py_cache: CacheType,
        data: DataField,
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

/// Returns the type of the `data` field, located by name.
fn getDataType(comptime T: type) type {
    const flds = @typeInfo(T).@"struct".fields;
    inline for (flds) |fld| {
        if (std.mem.eql(u8, fld.name, "data")) return fld.type;
    }
    @compileError(@typeName(T) ++ ": expected field `data`");
}

fn hasPointerOrSlice(comptime DataType: type) bool {
    inline for (@typeInfo(DataType).@"struct".fields) |field| {
        switch (@typeInfo(field.type)) {
            .pointer => return true,
            else => {},
        }
    }
    return false;
}

fn writeU64Le(buf: [*]u8, off: usize, val: u64) void {
    buf[off + 0] = @truncate(val);
    buf[off + 1] = @truncate(val >> 8);
    buf[off + 2] = @truncate(val >> 16);
    buf[off + 3] = @truncate(val >> 24);
    buf[off + 4] = @truncate(val >> 32);
    buf[off + 5] = @truncate(val >> 40);
    buf[off + 6] = @truncate(val >> 48);
    buf[off + 7] = @truncate(val >> 56);
}

fn readU64Le(buf: [*]const u8, off: usize) u64 {
    return @as(u64, buf[off + 0]) |
        (@as(u64, buf[off + 1]) << 8) |
        (@as(u64, buf[off + 2]) << 16) |
        (@as(u64, buf[off + 3]) << 24) |
        (@as(u64, buf[off + 4]) << 32) |
        (@as(u64, buf[off + 5]) << 40) |
        (@as(u64, buf[off + 6]) << 48) |
        (@as(u64, buf[off + 7]) << 56);
}

fn checkFieldType(comptime FieldType: type, arg: ?*PyObject) bool {
    return switch (FieldType) {
        i64 => PyObject_IsInstance(arg, @as(?*PyObject, @ptrCast(&PyLong_Type))) > 0,
        // float accepts int (standard Python coercion)
        f64 => PyObject_IsInstance(arg, @as(?*PyObject, @ptrCast(&PyFloat_Type))) > 0 or
            PyObject_IsInstance(arg, @as(?*PyObject, @ptrCast(&PyLong_Type))) > 0,
        [:0]const u8 => PyObject_IsInstance(arg, @as(?*PyObject, @ptrCast(&PyUnicode_Type))) > 0,
        else => @compileError("unsupported field type: " ++ @typeName(FieldType)),
    };
}

fn fieldTypeError(comptime FieldType: type) [*:0]const u8 {
    return switch (FieldType) {
        i64 => "expected int",
        f64 => "expected float or int",
        [:0]const u8 => "expected str",
        else => @compileError("unsupported field type: " ++ @typeName(FieldType)),
    };
}

// Store a Python arg into a native struct field.
// For [:0]const u8: borrows a pointer directly into the Python object's internal UTF-8 buffer.
// The caller is responsible for keeping the Python object alive (via py_cache) for as long as
// the native slice is in use.  No heap allocation or copy is performed.
fn storeField(comptime FieldType: type, dest: *FieldType, arg: ?*PyObject) void {
    if (!checkFieldType(FieldType, arg)) {
        PyErr_SetString(PyExc_TypeError, fieldTypeError(FieldType));
        return;
    }
    switch (FieldType) {
        i64 => dest.* = @as(i64, @intCast(PyLong_AsLongLong(arg))),
        f64 => dest.* = PyFloat_AsDouble(arg),
        [:0]const u8 => {
            var size: Py_ssize_t = 0;
            // PyUnicode_AsUTF8AndSize guarantees null-termination; the returned pointer
            // is stable for the lifetime of the unicode object.
            const ptr = PyUnicode_AsUTF8AndSize(arg, &size) orelse return;
            const n: usize = @intCast(size);
            dest.* = if (n == 0) "" else ptr[0..n :0];
        },
        else => @compileError("unsupported zetaclass field type: " ++ @typeName(FieldType)),
    }
}

// Build the canonical Python object for a native field value.
// For [:0]const u8 we IncRef the original Python arg instead of allocating a new string.
// For i64/f64 we construct from the stored native value (ensures correct type after coercion).
fn buildCachedValue(comptime FieldType: type, native_ptr: *const FieldType, arg: ?*PyObject) ?*PyObject {
    return switch (FieldType) {
        i64 => PyLong_FromLongLong(@as(c_longlong, @intCast(native_ptr.*))),
        f64 => PyFloat_FromDouble(native_ptr.*),
        [:0]const u8 => blk: {
            // arg is the Python str object; IncRef and reuse it.
            Py_IncRef(arg);
            break :blk arg;
        },
        else => @compileError("unsupported field type: " ++ @typeName(FieldType)),
    };
}

// ── pack / unpack ─────────────────────────────────────────────────────────────

/// Returns a namespace containing `call` for the `pack()` instance method.
///
/// No pointer/slice fields: serializes the entire struct in one shot (raw struct bytes
/// including layout padding). Frozen structs can be cast directly; mutable structs are
/// memcopied — PyBytes_FromStringAndSize copies in both cases, so the result is identical.
/// Has pointer/slice fields ([:0]const u8 strings): field-by-field serialization.
/// i64/f64 are 8 bytes little-endian; strings are an 8-byte LE length prefix followed
/// by the raw UTF-8 bytes (no null terminator in the payload).
pub fn packFn(comptime T: type, comptime frozen: bool) type {
    _ = frozen; // future: expose struct memory via buffer protocol for zero-copy on frozen
    comptime assertObBase(T);
    const DataType = getDataType(T);
    const has_ptr = comptime hasPointerOrSlice(DataType);
    return struct {
        pub fn call(self_obj: ?*PyObject, _: ?*PyObject) callconv(.c) ?*PyObject {
            const self: *const T = @ptrCast(@alignCast(self_obj.?));
            if (comptime !has_ptr) {
                return PyBytes_FromStringAndSize(
                    @as([*]const u8, @ptrCast(&self.data)),
                    @as(Py_ssize_t, @intCast(@sizeOf(DataType))),
                );
            } else {
                var total: usize = 0;
                inline for (@typeInfo(DataType).@"struct".fields) |field| {
                    total += switch (field.type) {
                        i64, f64 => 8,
                        [:0]const u8 => 8 + @field(self.data, field.name).len,
                        else => @compileError("unsupported field type: " ++ @typeName(field.type)),
                    };
                }
                const raw = PyMem_Malloc(total) orelse {
                    PyErr_SetString(PyExc_MemoryError, "pack: out of memory");
                    return null;
                };
                defer PyMem_Free(raw);
                const buf: [*]u8 = @ptrCast(raw);
                var off: usize = 0;
                inline for (@typeInfo(DataType).@"struct".fields) |field| {
                    switch (field.type) {
                        i64, f64 => {
                            writeU64Le(buf, off, @bitCast(@field(self.data, field.name)));
                            off += 8;
                        },
                        [:0]const u8 => {
                            const s = @field(self.data, field.name);
                            writeU64Le(buf, off, s.len);
                            off += 8;
                            @memcpy((buf + off)[0..s.len], s);
                            off += s.len;
                        },
                        else => @compileError("unsupported field type: " ++ @typeName(field.type)),
                    }
                }
                return PyBytes_FromStringAndSize(@ptrCast(buf), @intCast(total));
            }
        }
    };
}

/// Returns a namespace containing `call` for the `unpack(bytes)` classmethod.
///
/// Inverse of packFn. Allocates and returns a new instance populated from the packed bytes.
/// No-pointer structs: direct memcopy of the raw struct bytes (must match @sizeOf exactly).
/// Structs with string fields: field-by-field deserialization; each string is reconstructed
/// as a Python str object that is stored in py_cache to keep the borrowed UTF-8 slice alive.
pub fn unpackFn(comptime T: type) type {
    comptime assertObBase(T);
    const DataType = getDataType(T);
    const has_ptr = comptime hasPointerOrSlice(DataType);
    return struct {
        pub fn call(cls_obj: ?*PyObject, bytes_obj: ?*PyObject) callconv(.c) ?*PyObject {
            const tp: *PyTypeObject = @ptrCast(@alignCast(cls_obj.?));
            var raw_buf: [*]u8 = undefined;
            var raw_len: Py_ssize_t = undefined;
            if (PyBytes_AsStringAndSize(bytes_obj, &raw_buf, &raw_len) < 0) return null;
            const new_obj = PyType_GenericNew(tp, null, null) orelse return null;
            const self: *T = @ptrCast(@alignCast(new_obj));
            // py_cache is zeroed by tp_alloc; tp_dealloc handles cleanup on any early return.
            if (comptime !has_ptr) {
                if (raw_len != @as(Py_ssize_t, @intCast(@sizeOf(DataType)))) {
                    PyErr_SetString(PyExc_ValueError, "unpack: wrong byte length");
                    Py_DecRef(new_obj);
                    return null;
                }
                @memcpy(
                    @as([*]u8, @ptrCast(&self.data))[0..@sizeOf(DataType)],
                    raw_buf[0..@sizeOf(DataType)],
                );
            } else {
                const buf: [*]const u8 = raw_buf;
                const buf_len: usize = @intCast(raw_len);
                var off: usize = 0;
                inline for (@typeInfo(DataType).@"struct".fields, 0..) |field, i| {
                    switch (field.type) {
                        i64, f64 => {
                            if (off + 8 > buf_len) {
                                PyErr_SetString(PyExc_ValueError, "unpack: buffer too short");
                                Py_DecRef(new_obj);
                                return null;
                            }
                            @field(self.data, field.name) = @bitCast(readU64Le(buf, off));
                            off += 8;
                        },
                        [:0]const u8 => {
                            if (off + 8 > buf_len) {
                                PyErr_SetString(PyExc_ValueError, "unpack: buffer too short");
                                Py_DecRef(new_obj);
                                return null;
                            }
                            const str_len: usize = @intCast(readU64Le(buf, off));
                            off += 8;
                            if (off + str_len > buf_len) {
                                PyErr_SetString(PyExc_ValueError, "unpack: buffer too short");
                                Py_DecRef(new_obj);
                                return null;
                            }
                            // Reconstruct a Python str; cache it to keep the UTF-8 buffer alive
                            // for the borrowed native slice.
                            const py_str = PyUnicode_FromStringAndSize(
                                buf + off,
                                @intCast(str_len),
                            ) orelse {
                                Py_DecRef(new_obj);
                                return null;
                            };
                            var actual_size: Py_ssize_t = 0;
                            const ptr = PyUnicode_AsUTF8AndSize(py_str, &actual_size) orelse {
                                Py_DecRef(py_str);
                                Py_DecRef(new_obj);
                                return null;
                            };
                            self.py_cache[i] = py_str; // dealloc releases this
                            const n: usize = @intCast(actual_size);
                            @field(self.data, field.name) = if (n == 0) "" else ptr[0..n :0];
                            off += str_len;
                        },
                        else => @compileError("unsupported field type: " ++ @typeName(field.type)),
                    }
                }
            }
            return new_obj;
        }
    };
}

// ── tp_members array (empty sentinel) ────────────────────────────────────────

/// All fields are exposed via tp_getset (with caching). tp_members is always empty.
pub fn membersArray() type {
    const init_array = [1]PyMemberDef{std.mem.zeroes(PyMemberDef)};
    return struct {
        pub var array: [1]PyMemberDef = init_array;
    };
}

// ── tp_getset array ───────────────────────────────────────────────────────────

/// Returns a namespace with a static `array: [N+1]PyGetSetDef` for ALL fields.
///
/// Getter: checks py_cache[i]; on miss builds the Python object from native,
///         stores it in cache (cache holds one ref), then returns it with an
///         additional IncRef for the caller.
/// Setter: updates the native field via storeField, then updates py_cache[i]
///         (DecRef old, build canonical Python value, cache it).
/// When frozen=true the set pointer is null (read-only descriptor).
pub fn getsetArray(comptime T: type, comptime frozen: bool) type {
    comptime assertObBase(T);
    const DataType = getDataType(T);
    const data_fields = @typeInfo(DataType).@"struct".fields;
    const N = data_fields.len;

    comptime var init_array: [N + 1]PyGetSetDef = std.mem.zeroes([N + 1]PyGetSetDef);
    inline for (data_fields, 0..) |field, i| {
        const FieldAccessor = struct {
            fn get(self_obj: ?*PyObject, _: ?*anyopaque) callconv(.c) ?*PyObject {
                const self: *T = @ptrCast(@alignCast(self_obj.?));
                const cache = &self.py_cache[i];
                if (cache.* == null) {
                    const py_val: ?*PyObject = switch (field.type) {
                        i64 => PyLong_FromLongLong(@as(c_longlong, @intCast(@field(self.data, field.name)))),
                        f64 => PyFloat_FromDouble(@field(self.data, field.name)),
                        [:0]const u8 => blk: {
                            const s = @field(self.data, field.name);
                            break :blk PyUnicode_FromStringAndSize(s.ptr, @intCast(s.len));
                        },
                        else => @compileError("unsupported field type: " ++ @typeName(field.type)),
                    };
                    if (py_val == null) return null;
                    cache.* = py_val; // cache holds one reference
                }
                Py_IncRef(cache.*);
                return cache.*;
            }
            fn set(self_obj: ?*PyObject, value: ?*PyObject, _: ?*anyopaque) callconv(.c) c_int {
                const self: *T = @ptrCast(@alignCast(self_obj.?));
                // Update native (handles type checking and string heap management).
                storeField(field.type, &@field(self.data, field.name), value);
                if (PyErr_Occurred() != null) return -1;
                // Update cache: DecRef old, build canonical Python value, store.
                const cache = &self.py_cache[i];
                if (cache.*) |old| Py_DecRef(old);
                const py_val = buildCachedValue(field.type, &@field(self.data, field.name), value);
                if (py_val == null) {
                    // OOM building numeric wrapper; native updated, invalidate cache.
                    cache.* = null;
                    return -1;
                }
                cache.* = py_val;
                return 0;
            }
        };
        init_array[i] = .{
            .name = @ptrCast(field.name.ptr),
            .get = @ptrCast(@constCast(&FieldAccessor.get)),
            .set = if (frozen) null else @ptrCast(@constCast(&FieldAccessor.set)),
            .doc = null,
            .closure = null,
        };
    }
    const getset_init = init_array;
    return struct {
        pub var array: [N + 1]PyGetSetDef = getset_init;
    };
}

// ── tp_methods array ──────────────────────────────────────────────────────────

/// Returns a namespace with a static `array: [3]PyMethodDef` containing:
///   is_zetaclass(obj)  — classmethod, PyObject_IsInstance(obj, cls).
///   is_instance(obj)   — classmethod, PyObject_IsInstance(obj, cls).
pub fn methodsArray() type {
    const TypeCheck = struct {
        fn call(cls_obj: ?*PyObject, arg: ?*PyObject) callconv(.c) ?*PyObject {
            const r = PyObject_IsInstance(arg, cls_obj);
            if (r < 0) return null;
            const ret: *PyObject = if (r > 0) &_Py_TrueStruct else &_Py_FalseStruct;
            Py_IncRef(ret);
            return ret;
        }
    };
    const init_array = [3]PyMethodDef{
        .{
            .ml_name = "is_zetaclass",
            .ml_meth = @ptrCast(@constCast(&TypeCheck.call)),
            .ml_flags = METH_CLASS | METH_O,
            .ml_doc = null,
        },
        .{
            .ml_name = "is_instance",
            .ml_meth = @ptrCast(@constCast(&TypeCheck.call)),
            .ml_flags = METH_CLASS | METH_O,
            .ml_doc = null,
        },
        std.mem.zeroes(PyMethodDef),
    };
    return struct {
        pub var array: [3]PyMethodDef = init_array;
    };
}

/// Like methodsArray() but also exposes pack() and unpack() for the validated path.
pub fn methodsArrayValidated(comptime T: type, comptime frozen: bool) type {
    const TypeCheck = struct {
        fn call(cls_obj: ?*PyObject, arg: ?*PyObject) callconv(.c) ?*PyObject {
            const r = PyObject_IsInstance(arg, cls_obj);
            if (r < 0) return null;
            const ret: *PyObject = if (r > 0) &_Py_TrueStruct else &_Py_FalseStruct;
            Py_IncRef(ret);
            return ret;
        }
    };
    const Pack = packFn(T, frozen);
    const Unpack = unpackFn(T);
    const init_array = [5]PyMethodDef{
        .{
            .ml_name = "is_zetaclass",
            .ml_meth = @ptrCast(@constCast(&TypeCheck.call)),
            .ml_flags = METH_CLASS | METH_O,
            .ml_doc = null,
        },
        .{
            .ml_name = "is_instance",
            .ml_meth = @ptrCast(@constCast(&TypeCheck.call)),
            .ml_flags = METH_CLASS | METH_O,
            .ml_doc = null,
        },
        .{
            .ml_name = "pack",
            .ml_meth = @ptrCast(@constCast(&Pack.call)),
            .ml_flags = METH_NOARGS,
            .ml_doc = null,
        },
        .{
            .ml_name = "unpack",
            .ml_meth = @ptrCast(@constCast(&Unpack.call)),
            .ml_flags = METH_CLASS | METH_O,
            .ml_doc = null,
        },
        std.mem.zeroes(PyMethodDef),
    };
    return struct {
        pub var array: [5]PyMethodDef = init_array;
    };
}

// ── tp_init ───────────────────────────────────────────────────────────────────

/// Returns a namespace containing `call`, suitable for use as tp_init.
///
/// Fields are populated in declaration order from positional args, then keyword
/// args by field name, then inline struct field defaults via field.defaultValue().
/// When an explicit Python arg is provided it is also cached immediately in
/// py_cache[i] (canonical Python value built from the stored native value).
/// When a default is used the cache slot is left null (lazy build on first get).
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

                const cache = &self.py_cache[i];

                if (arg != null) {
                    storeField(field.type, &@field(self.data, field.name), arg);
                    if (PyErr_Occurred() != null) return -1;
                    // Cache immediately: DecRef any stale value, build canonical Python obj.
                    if (cache.*) |old| Py_DecRef(old);
                    const py_val = buildCachedValue(field.type, &@field(self.data, field.name), arg);
                    if (py_val == null) return -1;
                    cache.* = py_val;
                } else if (field.defaultValue()) |dv| {
                    // Zero-copy: for strings, point directly to the Zig static default
                    // literal (always valid; no heap allocation needed).
                    @field(self.data, field.name) = dv;
                    // Clear stale cache so the getter rebuilds from native on first access.
                    if (cache.*) |old| Py_DecRef(old);
                    cache.* = null;
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
/// DecRefs all cached PyObject slots.  String fields are zero-copy borrows from
/// those Python objects, so releasing the cache entries is sufficient — no
/// separate heap memory to free.
///
/// In Python 3.12+, @zetaclass wraps the Zig base type in a Python heap subtype
/// via type(). That heap subtype gets tp_dealloc = subtype_dealloc. CPython's
/// subtype_dealloc handles GC untrack, managed weakrefs, managed dict, tp_free,
/// and the HEAPTYPE type-reference decrement — then calls this function as the
/// base-class dealloc. We must not repeat any of those steps.
pub fn deallocFn(comptime T: type) type {
    const DataType = getDataType(T);
    const n = @typeInfo(DataType).@"struct".fields.len;
    return struct {
        pub fn call(self_obj: ?*PyObject) callconv(.c) void {
            const self: *T = @ptrCast(@alignCast(self_obj.?));
            // Releasing cache entries frees all resources: numeric Python wrappers
            // are released, and string fields' borrowed pointers become unreachable
            // once their backing unicode objects are DecRef'd here.
            inline for (0..n) |i| {
                if (self.py_cache[i]) |cached| Py_DecRef(cached);
            }
        }
    };
}

// ── validate=False (unvalidated) path ────────────────────────────────────────

/// Default-value descriptor for an unvalidated field.
/// `.required` means no default (caller must supply the argument).
pub const DefaultValue = union(enum) {
    required,
    int: i64,
    float: f64,
    string: [:0]const u8,
};

/// Bundles the field name and its default value for the unvalidated path.
pub const FieldDescriptor = struct {
    name: [:0]const u8,
    default: DefaultValue,
};

/// Python object layout for validate=False: ob_base + N raw PyObject* slots.
/// No native data struct, no py_cache.
pub fn wrapAsPythonObjectUnvalidated(comptime N: usize) type {
    return struct {
        ob_base: PyObject,
        slots: [N]?*PyObject,
    };
}

fn getSlotCount(comptime T: type) usize {
    for (@typeInfo(T).@"struct".fields) |fld| {
        if (std.mem.eql(u8, fld.name, "slots")) return @typeInfo(fld.type).array.len;
    }
    @compileError(@typeName(T) ++ ": no `slots` field");
}

const T_OBJECT_EX: c_int = 16;
const READONLY: c_int = 1;

/// Generates a [N+1]PyMemberDef array using T_OBJECT_EX, one entry per slot.
/// When frozen=true each member is marked READONLY.
pub fn membersArrayUnvalidated(
    comptime T: type,
    comptime field_descs: []const FieldDescriptor,
    comptime frozen: bool,
) type {
    const N = field_descs.len;
    comptime var init_array: [N + 1]PyMemberDef = std.mem.zeroes([N + 1]PyMemberDef);
    inline for (field_descs, 0..) |fd, i| {
        init_array[i] = .{
            .name = @ptrCast(fd.name.ptr),
            .member_type = T_OBJECT_EX,
            .offset = @intCast(@offsetOf(T, "slots") + @sizeOf(?*PyObject) * i),
            .flags = if (frozen) READONLY else 0,
            .doc = null,
        };
    }
    const members_init = init_array;
    return struct {
        pub var array: [N + 1]PyMemberDef = members_init;
    };
}

/// tp_init for the unvalidated path.
/// Stores Python objects directly in slots without type conversion.
pub fn initFnUnvalidated(
    comptime T: type,
    comptime field_descs: []const FieldDescriptor,
    comptime kw_only: bool,
) type {
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
            inline for (field_descs, 0..) |fd, i| {
                const arg: ?*PyObject = if (!kw_only and i < nargs)
                    PyTuple_GetItem(args, @intCast(i))
                else if (kwargs != null)
                    PyDict_GetItemString(kwargs, @as([*:0]const u8, @ptrCast(fd.name.ptr)))
                else
                    null;

                if (arg != null) {
                    if (self.slots[i]) |old| Py_DecRef(old);
                    Py_IncRef(arg);
                    self.slots[i] = arg;
                } else {
                    switch (fd.default) {
                        .required => {
                            PyErr_SetString(PyExc_TypeError, "zetaclass __init__: missing required argument");
                            return -1;
                        },
                        .int => |v| {
                            if (self.slots[i]) |old| Py_DecRef(old);
                            self.slots[i] = PyLong_FromLongLong(@as(c_longlong, @intCast(v)));
                            if (self.slots[i] == null) return -1;
                        },
                        .float => |v| {
                            if (self.slots[i]) |old| Py_DecRef(old);
                            self.slots[i] = PyFloat_FromDouble(v);
                            if (self.slots[i] == null) return -1;
                        },
                        .string => |v| {
                            if (self.slots[i]) |old| Py_DecRef(old);
                            self.slots[i] = PyUnicode_FromStringAndSize(v.ptr, @intCast(v.len));
                            if (self.slots[i] == null) return -1;
                        },
                    }
                }
            }
            return 0;
        }
    };
}

/// tp_dealloc for the unvalidated path: DecRefs all slot values.
pub fn deallocFnUnvalidated(comptime T: type) type {
    const N = getSlotCount(T);
    return struct {
        pub fn call(self_obj: ?*PyObject) callconv(.c) void {
            const self: *T = @ptrCast(@alignCast(self_obj.?));
            inline for (0..N) |i| {
                if (self.slots[i]) |obj| Py_DecRef(obj);
            }
        }
    };
}

/// tp_repr for the unvalidated path.
pub fn reprFnUnvalidated(
    comptime T: type,
    comptime field_descs: []const FieldDescriptor,
    comptime class_name: [:0]const u8,
) type {
    return struct {
        pub fn call(self_obj: ?*PyObject) callconv(.c) ?*PyObject {
            const self: *const T = @ptrCast(@alignCast(self_obj.?));
            var result: ?*PyObject = PyUnicode_FromStringAndSize(class_name.ptr, @intCast(class_name.len));
            appendConcat(&result, PyUnicode_FromStringAndSize("(", 1));
            inline for (field_descs, 0..) |fd, i| {
                if (i > 0) appendConcat(&result, PyUnicode_FromStringAndSize(", ", 2));
                appendConcat(&result, PyUnicode_FromStringAndSize(fd.name.ptr, @intCast(fd.name.len)));
                appendConcat(&result, PyUnicode_FromStringAndSize("=", 1));
                const val = self.slots[i];
                const val_repr = if (val != null) PyObject_Repr(val) else PyUnicode_FromStringAndSize("None", 4);
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

/// tp_richcompare for the unvalidated path.
/// Equality: field-by-field PyObject_RichCompareBool.
/// Order (when order=true): lexicographic via Python comparisons.
pub fn richCompareFnUnvalidated(comptime T: type, comptime order: bool) type {
    const N = getSlotCount(T);
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

            if (op == Py_EQ or op == Py_NE) {
                inline for (0..N) |i| {
                    const eq = PyObject_RichCompareBool(a.slots[i], b.slots[i], Py_EQ);
                    if (eq < 0) return null;
                    if (eq == 0) {
                        const ret: *PyObject = if (op == Py_NE) &_Py_TrueStruct else &_Py_FalseStruct;
                        Py_IncRef(ret);
                        return ret;
                    }
                }
                const ret: *PyObject = if (op == Py_EQ) &_Py_TrueStruct else &_Py_FalseStruct;
                Py_IncRef(ret);
                return ret;
            } else {
                inline for (0..N) |i| {
                    const lt = PyObject_RichCompareBool(a.slots[i], b.slots[i], Py_LT);
                    if (lt < 0) return null;
                    if (lt > 0) {
                        const result = op == Py_LT or op == Py_LE;
                        const ret: *PyObject = if (result) &_Py_TrueStruct else &_Py_FalseStruct;
                        Py_IncRef(ret);
                        return ret;
                    }
                    const gt = PyObject_RichCompareBool(a.slots[i], b.slots[i], Py_GT);
                    if (gt < 0) return null;
                    if (gt > 0) {
                        const result = op == Py_GT or op == Py_GE;
                        const ret: *PyObject = if (result) &_Py_TrueStruct else &_Py_FalseStruct;
                        Py_IncRef(ret);
                        return ret;
                    }
                }
                const result = op == Py_LE or op == Py_GE;
                const ret: *PyObject = if (result) &_Py_TrueStruct else &_Py_FalseStruct;
                Py_IncRef(ret);
                return ret;
            }
        }
    };
}

/// tp_hash for the unvalidated path: feeds PyObject_Hash of each slot into Wyhash.
pub fn hashFnUnvalidated(comptime T: type) type {
    const N = getSlotCount(T);
    return struct {
        pub fn call(self_obj: ?*PyObject) callconv(.c) Py_ssize_t {
            const self: *const T = @ptrCast(@alignCast(self_obj.?));
            var hasher = std.hash.Wyhash.init(0);
            inline for (0..N) |i| {
                const h = PyObject_Hash(self.slots[i]);
                if (h == -1) return -1;
                std.hash.autoHash(&hasher, @as(usize, @bitCast(h)));
            }
            const raw: usize = @truncate(hasher.final());
            const result: Py_ssize_t = @bitCast(raw);
            return if (result == -1) -2 else result;
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
    /// When true: native Zig struct + tp_getset with type validation (validate=True path).
    /// When false: raw PyObject* slots + tp_members, no type conversion (validate=False path).
    validate: bool = true,
    /// Expose pack() / unpack() methods. Requires validate=true.
    pack: bool = false,
};

/// Build a PyTypeObject for a zetaclass object.
///
/// When opts.validate=true (default), T must be wrapAsPythonObject(DataType) and
/// field_descs is unused (pass &[_]FieldDescriptor{}).  Fields are exposed via
/// tp_getset with native type storage and Python-object caching.
///
/// When opts.validate=false, T must be wrapAsPythonObjectUnvalidated(N) and
/// field_descs provides field names and defaults.  Fields are exposed directly
/// via tp_members (T_OBJECT_EX) with no type conversion.
pub fn makeTypeObject(
    comptime T: type,
    comptime name: [:0]const u8,
    comptime field_descs: []const FieldDescriptor,
    comptime opts: makeTypeOptions,
) PyTypeObject {
    return PyTypeObject{
        .ob_base = .{ .ob_base = .{ .ob_refcnt = 1, .ob_type = null }, .ob_size = 0 },
        .tp_name = name.ptr,
        .tp_basicsize = @sizeOf(T),
        .tp_itemsize = 0,
        .tp_dealloc = if (opts.validate)
            @ptrCast(@constCast(&deallocFn(T).call))
        else
            @ptrCast(@constCast(&deallocFnUnvalidated(T).call)),
        .tp_vectorcall_offset = 0,
        .tp_getattr = null,
        .tp_setattr = null,
        .tp_as_async = null,
        .tp_repr = if (opts.repr) (if (opts.validate)
            @ptrCast(@constCast(&reprFn(T, name).call))
        else
            @ptrCast(@constCast(&reprFnUnvalidated(T, field_descs, name).call))) else null,
        .tp_as_number = null,
        .tp_as_sequence = null,
        .tp_as_mapping = null,
        .tp_hash = if (opts.hash) (if (opts.validate)
            @ptrCast(@constCast(&hashFn(T).call))
        else
            @ptrCast(@constCast(&hashFnUnvalidated(T).call))) else null,
        .tp_call = null,
        .tp_str = null,
        .tp_getattro = null,
        .tp_setattro = if (opts.frozen) @ptrCast(@constCast(&frozenSetAttrFn().call)) else null,
        .tp_as_buffer = null,
        .tp_flags = Py_TPFLAGS_BASETYPE | (if (opts.weakref_slot) Py_TPFLAGS_MANAGED_WEAKREF else 0),
        .tp_doc = null,
        .tp_traverse = null,
        .tp_clear = null,
        .tp_richcompare = if (opts.eq) (if (opts.validate)
            @ptrCast(@constCast(&richCompareFn(T, opts.order).call))
        else
            @ptrCast(@constCast(&richCompareFnUnvalidated(T, opts.order).call))) else null,
        .tp_weaklistoffset = 0,
        .tp_iter = null,
        .tp_iternext = null,
        .tp_methods = if (opts.validate and opts.pack) &methodsArrayValidated(T, opts.frozen).array else &methodsArray().array,
        .tp_members = if (opts.validate)
            &membersArray().array
        else
            &membersArrayUnvalidated(T, field_descs, opts.frozen).array,
        .tp_getset = if (opts.validate) &getsetArray(T, opts.frozen).array else null,
        .tp_base = null,
        .tp_dict = null,
        .tp_descr_get = null,
        .tp_descr_set = null,
        .tp_dictoffset = 0,
        .tp_init = if (opts.init) (if (opts.validate)
            @ptrCast(@constCast(&initFn(T, opts.kw_only).call))
        else
            @ptrCast(@constCast(&initFnUnvalidated(T, field_descs, opts.kw_only).call))) else @ptrCast(@constCast(&noInitFn().call)),
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
