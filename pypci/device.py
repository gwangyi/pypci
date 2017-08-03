from ._native import lib, ffi
from typing import SupportsBytes, overload, NamedTuple, Union, List, Optional
import enum
import itertools
import functools
from . import pci


def _rstrip(iterable, pred):
    cache = []
    cache_append = cache.append
    for x in iterable:
        if pred(x):
            cache_append(x)
        else:
            for y in cache:
                yield y
            del cache[:]
            yield x


PciFillFlag = enum.IntFlag('PciFillFlag', dict(
    (''.join(x.capitalize() for x in k.split('_')[2:]), getattr(lib, k))
    for k in dir(lib) if k.startswith('PCI_FILL_')))

PciFillFlag.All = PciFillFlag(sum(v.value for v in PciFillFlag if v.value < PciFillFlag.Rescan))


class PciCapType(enum.Enum):
    Normal = lib.PCI_CAP_NORMAL
    Extended = lib.PCI_CAP_EXTENDED


PciCapId = enum.IntEnum('PciCapId', dict(
    (''.join(x.capitalize() for x in k.split('_')[3:]), getattr(lib, k))
    for k in dir(lib) if k.startswith('PCI_CAP_ID_')))

PciExtCapId = enum.IntEnum('PciExtCapId', dict(
    (''.join(x.capitalize() for x in k.split('_')[3:]), getattr(lib, k))
    for k in dir(lib) if k.startswith('PCI_EXT_CAP_ID_')))


class PciCap(NamedTuple):
    id: Union[int, PciCapId, PciExtCapId]
    type: PciCapType
    addr: int


class _PciBaseClass(enum.IntEnum):
    def __contains__(self, pci_class: 'PciClass') -> bool:
        return isinstance(pci_class, PciClass) and (pci_class.value >> 8) == self.value


class _PciClass(enum.IntEnum):
    @property
    def base(self) -> 'PciBaseClass':
        return PciBaseClass(self.value >> 8)


PciBaseClass = _PciBaseClass('PciBaseClass', dict(
    (''.join(x.capitalize() for x in k.split('_')[3:]), getattr(lib, k))
    for k in dir(lib) if k.startswith('PCI_BASE_CLASS_')))

PciClass = _PciClass('PciClass', dict(
    (''.join(x.capitalize() for x in k.split('_')[2:]), getattr(lib, k))
    for k in dir(lib) if k.startswith('PCI_CLASS_')))


def _pci_info(flag: str):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapped(self):
            if flag in PciFillFlag.__members__:
                f = getattr(PciFillFlag, flag)
                if f not in self.known_fields:
                    self.fill_info(f)
                return fn(self)
            else:
                raise AttributeError(fn.__name__)
        return wrapped
    return decorator


class PciDevice:
    def __init__(self, pci: 'pci.Pci', dev: ffi.CData):
        self._dev = dev
        self._pci = pci

    def close(self):
        if self._dev is not None:
            self._dev, dev = None, self._dev
            lib.pci_free_dev(dev)

    def __del__(self):
        self.close()

    @property
    def domain(self) -> int:
        return self._dev.domain

    @property
    def bus(self) -> int:
        return self._dev.bus

    @property
    def dev(self) -> int:
        return self._dev.dev

    @property
    def func(self) -> int:
        return self._dev.func

    @property
    def known_fields(self) -> PciFillFlag:
        return PciFillFlag(self._dev.known_fields)

    @property
    @_pci_info('Ident')
    def vendor(self) -> str:
        return self._pci.lookup(vendor_id=self.vendor_id).vendor

    @property
    @_pci_info('Ident')
    def device(self) -> str:
        return self._pci.lookup(vendor_id=self.vendor_id, device_id=self.device_id).device

    @property
    @_pci_info('Ident')
    def vendor_id(self) -> int:
        return self._dev.vendor_id

    @property
    @_pci_info('Ident')
    def device_id(self) -> int:
        return self._dev.device_id

    @property
    @_pci_info('Class')
    def device_class(self) -> PciClass:
        return PciClass(self._dev.device_class)

    @property
    @_pci_info('Class')
    def device_class_name(self) -> str:
        return self._pci.lookup(class_id=self.device_class).pci_class

    @property
    @_pci_info('Irq')
    def irq(self) -> int:
        return self._dev.irq

    @property
    @_pci_info('Bases')
    def base_addr(self) -> List[int]:
        return list(_rstrip(self._dev.base_addr, lambda x: x == 0))

    @property
    @_pci_info('Sizes')
    def size(self) -> List[int]:
        return list(_rstrip(self._dev.size, lambda x: x == 0))

    @property
    @_pci_info('RomBase')
    def rom_base_addr(self) -> int:
        return self._dev.rom_base_addr

    @property
    @_pci_info('Sizes')
    def rom_size(self) -> int:
        return self._dev.rom_size

    @property
    @_pci_info('Caps')
    @_pci_info('ExtCaps')
    def caps(self) -> List[PciCap]:
        def gen():
            cap = self._dev.first_cap
            while cap != ffi.NULL:
                try:
                    if cap.type == PciCapType.Normal.value:
                        yield PciCap(PciCapId(cap.id), PciCapType.Normal, cap.addr)
                    elif cap.type == PciCapType.Extended.value:
                        yield PciCap(PciExtCapId(cap.id), PciCapType.Extended, cap.addr)
                    else:
                        raise ValueError()
                except ValueError:
                    yield PciCap(cap.id, PciCapType(cap.type), cap.addr)
                cap = cap.next
        return list(gen())

    @property
    @_pci_info('PhysSlot')
    def phy_slot(self) -> Optional[str]:
        if self._dev.phy_slot == ffi.NULL:
            return None
        return ffi.string(self._dev.phy_slot).decode('utf-8')

    phys_slot = phy_slot

    @property
    @_pci_info('ModuleAlias')
    def module_alias(self) -> Optional[str]:
        if self._dev.module_alias == ffi.NULL:
            return None
        return ffi.string(self._dev.module_alias).decode('utf-8')

    @property
    @_pci_info('Label')
    def label(self) -> Optional[str]:
        if self._dev.label == ffi.NULL:
            return None
        return ffi.string(self._dev.label).decode('utf-8')

    def read(self, pos: int, len: int) -> bytes:
        buf = ffi.new(f'u8[{len}]')
        lib.pci_read_block(self._dev, pos, buf, len)
        return ffi.buffer(buf)[:]

    def read_vpd(self, pos: int, len: int) -> bytes:
        buf = ffi.new(f'u8[{len}]')
        lib.pci_read_vpd(self._dev, pos, buf, len)
        return ffi.buffer(buf)[:]

    def write(self, pos: int, buf: SupportsBytes):
        buf_ = ffi.from_buffer(buf)
        lib.pci_write_block(self._dev, pos, buf_, len(buf))

    def read_byte(self, pos: int) -> int:
        return lib.pci_read_byte(self._dev, pos)

    def read_word(self, pos: int) -> int:
        return lib.pci_read_word(self._dev, pos)

    def read_long(self, pos: int) -> int:
        return lib.pci_read_long(self._dev, pos)

    def write_byte(self, pos: int, data: int):
        lib.pci_write_byte(self._dev, pos, data)

    def write_word(self, pos: int, data: int):
        lib.pci_write_word(self._dev, pos, data)

    def write_long(self, pos: int, data: int):
        lib.pci_write_long(self._dev, pos, data)

    def fill_info(self, flags: PciFillFlag = PciFillFlag.All) -> PciFillFlag:
        return PciFillFlag(lib.pci_fill_info(self._dev, flags.value))

    @overload
    def setup_cache(self, cache: ffi.CData):
        ...

    @overload
    def setup_cache(self, cache: int):
        ...

    def setup_cache(self, cache):
        if isinstance(cache, ffi.CData):
            self._cache = cache
            lib.pci_setup_cache(self._dev, cache, len(cache))
        elif isinstance(cache, int):
            self._cache = ffi.new(f'u8[{cache}]')
            lib.pci_setup_cache(self._dev, self._cache, cache)
        else:
            raise ValueError(f'{repr(cache)} is not an instance of int or ffi.CData')

    @overload
    def find_cap(self, id: PciCapId, type: PciCapType) -> int:
        ...

    @overload
    def find_cap(self, id: int, type: PciCapType) -> int:
        ...

    def find_cap(self, id, type):
        cap = lib.pci_find_cap(self._dev, id, type)
        return cap.addr

    def __repr__(self):
        info = [f'{self.domain:04x}:{self.bus:02x}:{self.dev:02x}.{self.func:02x}']
        flags = PciFillFlag.__members__

        if 'Ident' in flags and PciFillFlag.Ident in self.known_fields:
            info.append(f', {{{self.vendor} {self.device}}}')
            info.append(f', vendor_id=0x{self.vendor_id:04x}, device_id=0x{self.device_id:04x}')
        if 'Irq' in flags and PciFillFlag.Irq in self.known_fields:
            info.append(f', irq={self.irq}')
        if 'Bases' in flags and PciFillFlag.Bases in self.known_fields:
            info.append(f', bases={list(hex(addr) for addr in self.base_addr)}')
        if 'RomBase' in flags and PciFillFlag.RomBase in self.known_fields:
            info.append(f', rom_base={hex(self.rom_base_addr)}')
        if 'Sizes' in flags and PciFillFlag.Sizes in self.known_fields:
            info.append(f', size={list(hex(size) for addr in self.sizes)}')
            info.append(f', rom_size={hex(self.rom_size)}')
        if 'Class' in flags and PciFillFlag.Class in self.known_fields:
            info.append(f', device_class={self.device_class_name}')
        if ('Caps' in flags and PciFillFlag.Caps in self.known_fields) or\
           ('ExtCaps' in flags and PciFillFlag.ExtCaps in self.known_fields):
            info.append(f', caps={self.caps}')
        if 'PhysSlot' in flags and PciFillFlag.PhysSlot in self.known_fields:
            info.append(f', phys_slot={repr(self.phy_slot)}')
        if 'ModuleAlias' in flags and PciFillFlag.ModuleAlias in self.known_fields:
            info.append(f', module_alias={repr(self.module_alias)}')
        if 'Label' in flags and PciFillFlag.Label in self.known_fields:
            info.append(f', label={repr(self.label)}')

        return f'<{self.__class__.__module__}.{self.__class__.__name__}: {"".join(info)}>'

