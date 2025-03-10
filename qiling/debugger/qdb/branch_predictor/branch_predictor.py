#!/usr/bin/env python3
#
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
#

from abc import abstractmethod
from ..context import Context


class Prophecy:
    """
    container for storing result of the predictor
    @going: indicate the certian branch will be taken or not
    @where: where will it go if going is true
    """

    def __init__(self):
        self.going = False
        self.where = None

    def __iter__(self):
        return iter((self.going, self.where))

class BranchPredictor(Context):
    """
    Base class for predictor
    """

    def read_reg(self, reg_name):
        """
        read specific register value
        """

        return self.ql.arch.regs.read(reg_name)

    @abstractmethod
    def predict(self) -> Prophecy:
        """
        Try to predict certian branch will be taken or not based on current context
        """
