from ._native import lib, ffi
from .device import PciDevice, PciClass
from .filter import PciFilter
from typing import MutableMapping, Iterator, Iterable, Tuple, Optional
import enum


class PciParameters(MutableMapping[str, str]):
    def __init__(self, pci: 'Pci'):
        self._pci = pci

    def __iter__(self) -> Iterator[str]:
        pacc = self._pci._pacc
        if pacc is None:
            return
        ret = []
        param = lib.pci_walk_params(pacc, ffi.NULL)
        while param != ffi.NULL:
            ret.append(ffi.string(param.param).decode('utf-8'))
            param = lib.pci_walk_params(pacc, param)
        for p in ret:
            yield p

    def items(self) -> Iterable[Tuple[str, str]]:
        def gen():
            pacc = self._pci._pacc
            if pacc is None:
                return
            ret = []
            param = lib.pci_walk_params(pacc, ffi.NULL)
            while param != ffi.NULL:
                k, v, h = ffi.string(param.param).decode('utf-8'),\
                          ffi.string(param.value).decode('utf-8'),\
                          ffi.string(param.help).decode('utf-8')
                cls = type(k, (tuple,), dict(__doc__=h))
                ret.append(cls((k, v)))
                param = lib.pci_walk_params(pacc, param)
            for p in ret:
                yield p
        return list(gen())

    def __len__(self):
        return sum(1 for _ in self)

    def __getitem__(self, key: str) -> str:
        pacc = self._pci._pacc
        if pacc is None:
            raise KeyError(key)
        key_ = key.encode('utf-8') + b'\0'

        ret = lib.pci_get_param(pacc, ffi.from_buffer(key_))
        if ret == ffi.NULL:
            raise KeyError(key)
        return ffi.string(ret).decode('utf-8')

    def __setitem__(self, key: str, val: str):
        pacc = self._pci._pacc
        if pacc is None:
            raise KeyError(key)
        key_ = key.encode('utf-8') + b'\0'
        val_ = val.encode('utf-8') + b'\0'

        if lib.pci_set_param(pacc, ffi.from_buffer(key_), ffi.from_buffer(val_)) != 0:
            raise KeyError(key)

    def __delitem__(self, key: str):
        raise KeyError(key)

    def __repr__(self):
        return repr(dict(self.items()))

PciAccessType = enum.IntFlag('PciAccessType', dict(
    (''.join(x.capitalize() for x in k.split('_')[2:]), getattr(lib, k))
    for k in dir(lib) if k.startswith('PCI_ACCESS_')))

PciLookupMode = enum.IntFlag('PciLookupMode', dict(
    (''.join(x.capitalize() for x in k.split('_')[2:]), getattr(lib, k))
    for k in dir(lib) if k.startswith('PCI_LOOKUP_')))


class Pci:
    def __init__(self):
        self._pacc = lib.pci_alloc()
        lib.pci_init(self._pacc)

    def close(self):
        if self._pacc is not None:
            self._pacc, pacc = None, self._pacc
            lib.pci_cleanup(pacc)

    def __del__(self):
        self.close()

    def scan_bus(self):
        lib.pci_scan_bus(self._pacc)

    def get_dev(self, domain: int, bus: int, dev: int, func: int) -> PciDevice:
        return PciDevice(self, lib.pci_get_dev(self._pacc, domain, bus, dev, func))

    @staticmethod
    def lookup_method(name: str) -> int:
        name_ = name.encode('utf-8') + b'\0'
        return lib.pci_lookup_method(ffi.from_buffer(name_))

    @staticmethod
    def get_method_name(index: int) -> str:
        return ffi.string(lib.pci_get_method_name(index))

    @property
    def parameters(self) -> PciParameters:
        return PciParameters(self)

    def filter(self) -> PciFilter:
        filt = ffi.new('struct pci_filter *')
        lib.pci_filter_init(self._pacc, filt)
        return PciFilter(filt)

    def lookup_name(self, flags: PciLookupMode, *args: int) -> Optional[str]:
        buf = ffi.new('char[512]')
        ret = lib.pci_lookup_name(self._pacc, buf, 512, flags.value, *iter(ffi.cast('int', arg) for arg in args))
        if ret == ffi.NULL:
            return None
        else:
            return ffi.string(ret).decode('utf-8')

    def lookup(self, vendor_id: Optional[int] = None, device_id: Optional[int] = None,
               subvendor_id: Optional[int] = None, subdev_id: Optional[int] = None,
               class_id: Optional[PciClass] = None, progif: Optional[int] = None,
               flags: PciLookupMode = PciLookupMode(0)):
        return PciLookupName(self, vendor_id, device_id, subvendor_id, subdev_id,
                             class_id, progif, flags)

    @property
    def method(self) -> PciAccessType:
        return PciAccessType(self._pacc.method)

    @method.setter
    def method(self, val: PciAccessType):
        self._pacc.method = val.value

    @property
    def writeable(self) -> bool:
        return self._pacc.writeable != 0

    @writeable.setter
    def writeable(self, val: bool):
        self._pacc.writeable = 1 if val else 0

    @property
    def buscentric(self) -> bool:
        return self._pacc.buscentric != 0

    @buscentric.setter
    def buscentric(self, val: bool):
        self._pacc.buscentric = 1 if val else 0

    @property
    def id_file_name(self) -> str:
        return ffi.string(self._pacc.id_file_name).decode('utf-8')

    @id_file_name.setter
    def id_file_name(self, val: str):
        self._id_file_name = val.encode('utf-8') + b'\0'
        self._pacc.id_file_name = ffi.from_buffer(self._id_file_name)
        self._pacc.free_id_name = 0

    @property
    def numeric_ids(self) -> bool:
        return self._pacc.numeric_ids != 0

    @numeric_ids.setter
    def numeric_ids(self, val: bool):
        self._pacc.numeric_ids = 1 if val else 0

    @property
    def id_lookup_mode(self) -> PciLookupMode:
        return PciLookupMode(self._pacc.id_lookup_mode)

    @id_lookup_mode.setter
    def id_lookup_mode(self, val: PciLookupMode):
        self._pacc.id_lookup_mode = val.value

    @property
    def debugging(self) -> bool:
        return self._pacc.debugging != 0

    @debugging.setter
    def debugging(self, val: bool):
        self._pacc.debugging = 1 if val else 0

    @property
    def devices(self) -> Iterable[PciDevice]:
        dev = self._pacc.devices
        while dev != ffi.NULL:
            yield self.get_dev(dev.domain, dev.bus, dev.dev, dev.func)
            dev = dev.next


class PciLookupName:
    def __init__(self, pci: Pci, vendor_id: Optional[int] = None, device_id: Optional[int] = None,
                 subvendor_id: Optional[int] = None, subdev_id: Optional[int] = None,
                 class_id: Optional[PciClass] = None, progif: Optional[int] = None,
                 flags: PciLookupMode = PciLookupMode(0)):
        self._pci = pci
        self.vendor_id = vendor_id
        self.device_id = device_id
        self.subvendor_id = subvendor_id
        self.subdev_id = subdev_id
        self.class_id = class_id
        self.progif = progif
        self.flags = flags

    @property
    def vendor(self) -> str:
        "(vendorID) -> vendor"
        if self.vendor_id is None:
            raise ValueError("vendor_id is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff | PciLookupMode.Vendor, self.vendor_id)

    @property
    def device(self) -> str:
        "(vendorID, deviceID) -> device"
        if self.vendor_id is None:
            raise ValueError("vendor_id is not specified")
        if self.device_id is None:
            raise ValueError("device_id is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff | PciLookupMode.Device, self.vendor_id, self.device_id)

    @property
    def vendor_device(self) -> str:
        "(vendorID, deviceID) -> combined vendor and device"
        if self.vendor_id is None:
            raise ValueError("vendor_id is not specified")
        if self.device_id is None:
            raise ValueError("device_id is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff | PciLookupMode.Vendor | PciLookupMode.Device,
                                     self.vendor_id, self.device_id)

    @property
    def subsystem_vendor(self) -> str:
        "(subvendorID) -> subsystem vendor"
        if self.subvendor_id is None:
            raise ValueError("subvendor_id is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff | PciLookupMode.Subsystem | PciLookupMode.Device,
                                     self.subvendor_id)

    @property
    def subsystem_device(self) -> str:
        "(vendorID, deviceID, subvendorID, subdevID) -> subsystem device"
        if self.vendor_id is None:
            raise ValueError("subvendor_id is not specified")
        if self.device_id is None:
            raise ValueError("device_id is not specified")
        if self.subvendor_id is None:
            raise ValueError("subvendor_id is not specified")
        if self.subdev_id is None:
            raise ValueError("subdev_id is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff | PciLookupMode.Subsystem | PciLookupMode.Device,
                                     self.vendor_id, self.device_id, self.subvendor_id, self.subdev_id)

    @property
    def subsystem_vendor_device(self) -> str:
        "(vendorID, deviceID, subvendorID, subdevID) -> combined subsystem v+d"
        if self.vendor_id is None:
            raise ValueError("subvendor_id is not specified")
        if self.device_id is None:
            raise ValueError("device_id is not specified")
        if self.subvendor_id is None:
            raise ValueError("subvendor_id is not specified")
        if self.subdev_id is None:
            raise ValueError("subdev_id is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff |
                                     PciLookupMode.Subsystem | PciLookupMode.Vendor | PciLookupMode.Device,
                                     self.vendor_id, self.device_id, self.subvendor_id, self.subdev_id)

    @property
    def generic_subsystem(self) -> str:
        "(subvendorID, subdevID) -> generic subsystem"
        if self.subvendor_id is None:
            raise ValueError("subvendor_id is not specified")
        if self.subdev_id is None:
            raise ValueError("subdev_id is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff |
                                     PciLookupMode.Subsystem | PciLookupMode.Vendor | PciLookupMode.Device,
                                     -1, -1, self.subvendor_id, self.subdev_id)

    @property
    def pci_class(self) -> str:
        "(classID) -> class"
        if self.class_id is None:
            raise ValueError("class_id is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff | PciLookupMode.Class, self.class_id)

    @property
    def programming_interface(self) -> str:
        "(classID, progif) -> programming interface"
        if self.class_id is None:
            raise ValueError("class_id is not specified")
        if self.progif is None:
            raise ValueError("progif is not specified")
        return self._pci.lookup_name(self.flags & ~0xffff | PciLookupMode.Class | PciLookupMode.Progif,
                                     self.class_id, self.progif)

