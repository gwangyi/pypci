from cffi import FFI
from cffi_ext import cdef_extract

cdef = cdef_extract(r"""
#define PCI_HAVE_STDINT_H
#define PRIx64 ""
#include <pci/pci.h>
""", cpp_args=["-I/usr/include", "-I/usr/local/include"])

ffi_builder = FFI()
ffi_builder.set_source("pypci._native", "#include <pci/pci.h>", libraries=['pci'])
ffi_builder.cdef(cdef)


if __name__ == "__main__":
    ffi_builder.compile(verbose=True)
