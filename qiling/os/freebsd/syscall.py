#!/usr/bin/env python3
#
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
#

import ctypes
from datetime import datetime
from math import floor

from qiling import Qiling
from qiling.arch.x86_const import *
from qiling.os.freebsd.const import *
from qiling.os.posix.const import ENOENT
from qiling.os.posix.syscall.unistd import ql_syscall_getcwd
from qiling.os.posix.syscall.stat import ql_syscall_newfstatat

class timespec(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_uint64),
        ("tv_nsec", ctypes.c_int64)
    ]

    _pack_ = 8

# See __FreeBSD_version in /sys/sys/params.h
# This value comes from FreeBSD stable/12 as of 2021.3.12
FREEBSD_OSRELDATE = 1202505

def ql_syscall_clock_gettime(ql, clock_gettime_clock_id, clock_gettime_timespec, *args, **kw):
    ql.log.info(f"clock_gettime(clock_id={clock_gettime_clock_id}, tp={hex(clock_gettime_timespec)})")
    now = datetime.now().timestamp()
    tv_sec = floor(now)
    tv_nsec = floor((now - floor(now)) * 1e6)
    tp = timespec(tv_sec= tv_sec, tv_nsec=tv_nsec)
    ql.mem.write(clock_gettime_timespec, bytes(tp))
    ql.log.debug(f"timespec(tv_sec={tv_sec}, tv_nsec={tv_nsec})")
    return 0


def ql_syscall_sysarch(ql, op, parms, *args, **kw):
    """
    wild guess, of cause not working
    """

    #ql.mem.map(GS_SEGMENT_ADDR, GS_SEGMENT_SIZE)
    #ql.arch.msr.write(IA32_GS_BASE_MSR, GS_SEGMENT_ADDR)
    ql.arch.msr.write(IA32_FS_BASE_MSR, parms)

    #op_buf = ql.pack32(op)
    #ql.mem.write(parms, op_buf)

    return 0

def ql_syscall_sigprocmask(ql, how, mask, omask, *args, **kw):
    ql.log.debug("sigprocmask(how: 0x%x, mask: 0x%x, omask: 0x%x)" % (how, mask, omask))
    return 0

def ql_syscall___getcwd(ql, path_buff, path_buffsize, *args, **kw):
    return ql_syscall_getcwd(ql, path_buff, path_buffsize, *args, **kw)

def ql_syscall_fstatat(ql, newfstatat_dirfd, newfstatat_path, newfstatat_buf_ptr, newfstatat_flag, *args, **kw):
    return ql_syscall_newfstatat(ql, newfstatat_dirfd, newfstatat_path, newfstatat_buf_ptr, newfstatat_flag, *args, **kw)

def ql_syscall___sysctl(ql: Qiling, name: int, namelen: int, old: int, oldlenp: int, new_arg: int, newlen: int):
    ql.log.debug("__sysctl(name: 0x%x, namelen: 0x%x, old: 0x%x, oldlenp: 0x%x, new: 0x%x, newlen: 0x%x)" % (
        name, namelen, old, oldlenp, new_arg, newlen
    ))

    vecs = [ql.mem.read_ptr(name + i * 4, 4, signed=True) for i in range(namelen)]

    ql.log.debug(f"__sysctl vectors: {vecs}")
    if vecs[0] == CTL_SYSCTL:
        if vecs[1] == CTL_SYSCTL_NAME2OID:
            # Write oid to old and oldlenp
            sysctl_name = ql.os.utils.read_cstring(new_arg)
            out_vecs = []
            out_len = 0

            # TODO: Implement oid<-->name as many as possible from FreeBSD source.
            #       Search SYSCTL_ADD_NODE etc.
            if sysctl_name == "hw.pagesizes":
                out_vecs = [CTL_HW, HW_PAGESIZE]
                out_len = 2
            else:
                ql.log.warning("Unknown oid name!")

            for i, v in enumerate(out_vecs):
                ql.mem.write_ptr(old + i * 4, v, 4, signed=True)

            ql.mem.write_ptr(oldlenp, out_len, 4, signed=True)

        return -ENOENT

    if vecs[0] == CTL_KERN:
        if vecs[1] == KERN_OSRELDATE:
            if old == 0 or oldlenp == 0:
                return -1

            # Ignore oldlenp check.
            ql.mem.write_ptr(old, FREEBSD_OSRELDATE, 4, signed=True)

            return 0
    return 0
