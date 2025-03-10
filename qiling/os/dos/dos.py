#!/usr/bin/env python3
#
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
#

import curses
from enum import IntEnum
from datetime import datetime

from unicorn import UcError

from qiling import Qiling
from qiling.const import QL_OS, QL_INTERCEPT
from qiling.os.os import QlOs

from .interrupts import handlers


# @see: https://en.wikipedia.org/wiki/FLAGS_register
class Flags(IntEnum):
    CF = (1 << 0)       # carry
    PF = (1 << 2)       # parity
    AF = (1 << 4)       # alignment
    ZF = (1 << 6)       # zero
    SF = (1 << 7)       # sign
    TF = (1 << 8)       # trap
    IF = (1 << 9)       # interrupt
    DF = (1 << 10)      # direction
    OF = (1 << 11)      # overflow
    IOPL = (3 << 12)    # io privilege


class QlOsDos(QlOs):
    type = QL_OS.DOS

    def __init__(self, ql: Qiling):
        super().__init__(ql)

        self.hook_syscall()

        # used by int 21h
        self.handle_next = 0
        self.handles = {}

        # used by int 10h
        self.color_pairs = {}
        self.revese_color_pairs = {}

        self.stdscr = None

        kconf = self.ql.profile["KERNEL"]

        self.dos_ver = kconf.getint("version")
        self.ticks_per_second = kconf.getfloat("ticks_per_second")

    def __del__(self):
        # resume terminal
        if self.stdscr is not None:
            self.stdscr.keypad(False)

            curses.echo()
            curses.nocbreak()
            curses.endwin()

    def set_flag_value(self, fl: Flags, val: int) -> None:
        self.ql.arch.regs.eflags = self.ql.arch.regs.eflags & (~fl) | (fl * val)

    def test_flags(self, fl):
        return self.ql.arch.regs.eflags & fl == fl

    def set_cf(self):
        self.set_flag_value(Flags.CF, 0b1)

    def clear_cf(self):
        self.set_flag_value(Flags.CF, 0b0)

    def set_zf(self):
        self.set_flag_value(Flags.ZF, 0b1)

    def clear_zf(self):
        self.set_flag_value(Flags.ZF, 0b0)

    def hook_syscall(self):

        def cb(ql: Qiling, intno: int):
            ah = ql.arch.regs.ah
            intinfo = (intno, ah)

            func = self.user_defined_api[QL_INTERCEPT.CALL].get(intinfo) or handlers.get(intno)
            onenter = self.user_defined_api[QL_INTERCEPT.ENTER].get(intinfo)
            onexit = self.user_defined_api[QL_INTERCEPT.EXIT].get(intinfo)

            if onenter is not None:
                onenter(ql)

            if func is None:
                raise NotImplementedError(f'DOS interrupt {intno:02x}h is not implemented')

            ql.log.debug(f'Handling interrupt {intno:02x}h (leaf {ah:#04x})')
            func(ql)

            if onexit is not None:
                onexit(ql)

        self.ql.hook_intr(cb)

    def run(self):
        if self.ql.exit_point is not None:
            self.exit_point = self.ql.exit_point

        if self.ql.entry_point is None:
            self.ql.entry_point = self.ql.loader.start_address

        if not self.ql.code:
            self.start_time = datetime.now()

            try:
                self.ql.emu_start(self.ql.entry_point, self.exit_point, self.ql.timeout, self.ql.count)
            except UcError:
                self.emu_error()
                raise
