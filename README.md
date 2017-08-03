# pypci

cffi-based libpci python wrapper

## Example

```python
import pypci

pci = pypci.Pci()
pci.scan_bus()
for device in pci.devices:
    print(device.vendor, device.device)
```
