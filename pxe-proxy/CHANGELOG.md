# Changelog

## 1.0.0

- Initial release.
- dnsmasq in proxy DHCP mode, coexisting with the network's existing DHCP
  server.
- Boot file selected per client firmware (BIOS, UEFI x86, UEFI x86-64,
  UEFI ARM64) from DHCP option 93.
- Optional interface binding and configurable log level.
- Builds for amd64 and aarch64.
