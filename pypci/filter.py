from ._native import lib, ffi
from .device import PciClass, PciDevice
from typing import Optional


class PciFilter:
    def __init__(self, filt: ffi.CData):
        self._filt = filt

    @property
    def domain(self) -> Optional[int]:
        return self._filt.domain if self._filt.domain >= 0 else None

    @domain.setter
    def domain(self, val: Optional[int]):
        if val is None:
            self._filt.domain = -1
        elif val < 0:
            raise ValueError("domain must be positive number")
        self._filt.domain = val

    @property
    def bus(self) -> Optional[int]:
        return self._filt.bus if self._filt.bus >= 0 else None

    @bus.setter
    def bus(self, val: Optional[int]):
        if val is None:
            self._filt.bus = -1
        elif val < 0:
            raise ValueError("bus must be positive number")
        self._filt.bus = val

    @property
    def slot(self) -> Optional[int]:
        return self._filt.slot if self._filt.slot >= 0 else None

    @slot.setter
    def slot(self, val: Optional[int]):
        if val is None:
            self._filt.slot = -1
        elif val < 0:
            raise ValueError("slot must be positive number")
        self._filt.slot = val

    @property
    def func(self) -> Optional[int]:
        return self._filt.func if self._filt.func >= 0 else None

    @func.setter
    def func(self, val: Optional[int]):
        if val is None:
            self._filt.func = -1
        elif val < 0:
            raise ValueError("func must be positive number")
        self._filt.func = val

    @property
    def vendor(self) -> Optional[int]:
        return self._filt.vendor if self._filt.vendor >= 0 else None

    @vendor.setter
    def vendor(self, val: Optional[int]):
        if val is None:
            self._filt.vendor = -1
        elif val < 0:
            raise ValueError("vendor must be positive number")
        self._filt.vendor = val

    @property
    def device(self) -> Optional[int]:
        return self._filt.device if self._filt.device >= 0 else None

    @device.setter
    def device(self, val: Optional[int]):
        if val is None:
            self._filt.device = -1
        elif val < 0:
            raise ValueError("device must be positive number")
        self._filt.device = val

    @property
    def slot_filter(self) -> str:
        domain = '*' if self.domain is None else f'{self.domain:04x}'
        bus = '*' if self.bus is None else f'{self.bus:02x}'
        slot = '*' if self.slot is None else f'{self.slot:02x}'
        func = '*' if self.func is None else f'{self.func:02x}'

        return f'{domain}:{bus}:{slot}.{func}'

    @slot_filter.setter
    def slot_filter(self, val: str):
        val_ = val.encode('utf-8') + b'\0'
        lib.pci_filter_parse_slot(self._filt, ffi.from_buffer(val_))

    @property
    def id_filter(self) -> str:
        vid = '*' if self.vendor is None else f'0x{self.vendor:04x}'
        did = '*' if self.device is None else f'0x{self.device:04x}'

        return f'{vid}:{did}'

    @id_filter.setter
    def id_filter(self, val: str):
        val_ = val.encode('utf-8') + b'\0'
        lib.pci_filter_parse_id(self._filt, ffi.from_buffer(val_))

    def __contains__(self, dev: PciDevice) -> bool:
        return lib.pci_filter_match(self._filt, dev._dev) != 0

    def __repr__(self):
        return f'<{self.__class__.__module__}.{self.__class__.__name__}: slot={self.slot_filter}, id={self.id_filter}>'
