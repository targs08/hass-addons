# Home Assistant Add-on: PXE Proxy

Proxy DHCP server for PXE network booting, based on [dnsmasq][dnsmasq].

## About

PXE clients need two pieces of information to boot from the network: the
address of a boot server and the name of a boot file (DHCP options 66 and 67).
Many DHCP servers — most consumer and ISP routers among them — offer no way to
set those options, which makes network booting impossible without replacing the
router's DHCP server.

This add-on solves that by answering **only** the PXE part of the DHCP
conversation. It runs dnsmasq in proxy DHCP mode, so it never hands out
addresses, leases, gateways, or DNS servers. The existing DHCP server keeps
doing all of that, and the client combines both replies:

```
                    1. "Who am I?"
   ┌──────────┐ ──────────────────────────►  ┌────────────────────┐
   │  Client  │ ◄── address, gateway, DNS ──  │ Existing DHCP      │
   │  (PXE)   │                               └────────────────────┘
   │          │      2. "How do I boot?"
   │          │ ──────────────────────────►  ┌────────────────────┐
   └──────────┘ ◄── boot server, boot file ── │ PXE Proxy (this)   │
                                              └────────────────────┘
                    3. Fetch the boot file over TFTP
```

The add-on does not serve the boot files itself — point it at any TFTP server
already on your network.

## Installation

1. Add this repository to Home Assistant (see the [repository README][repo]).
2. Install the **PXE Proxy** add-on.
3. Set `subnet` and `tftp_server_ip` to match your network.
4. Start the add-on and check the log.

Full configuration reference and troubleshooting: [DOCS.md](DOCS.md).

## Configuration

```yaml
subnet: 192.168.1.0
tftp_server_ip: 192.168.1.2
boot_file_bios: netboot.xyz.kpxe
boot_file_uefi: netboot.xyz.efi
interfaces: []
log_level: info
```

## License

MIT — see the [LICENSE](../LICENSE) in the repository root. dnsmasq itself is
licensed under the GPL-2.

[dnsmasq]: https://thekelleys.org.uk/dnsmasq/doc.html
[repo]: https://github.com/targs08/hass-addons
