# Home Assistant Add-on: PXE Proxy

## Requirements

- A DHCP server already running on the network. This add-on complements it,
  it does not replace it.
- A TFTP server reachable from the clients, serving the boot files. Any TFTP
  server works.
- Home Assistant and the clients on the same layer-2 network, with broadcast
  traffic allowed between them. Client isolation, guest networks and separate
  VLANs all prevent PXE from working.

## Configuration

Example configuration:

```yaml
subnet: 192.168.1.0
tftp_server_ip: 192.168.1.2
boot_file_bios: netboot.xyz.kpxe
boot_file_uefi: netboot.xyz.efi
boot_file_uefi_ia32: netboot.xyz.efi
boot_file_uefi_arm64: netboot.xyz-arm64.efi
interfaces:
  - eth0
log_level: info
```

### Option: `subnet` (required)

The network address of the subnet the clients boot on, without a prefix
length — for example `192.168.1.0` for a `192.168.1.0/24` network.

dnsmasq uses this to decide which requests belong to the proxied network. It
must match the subnet the Home Assistant host is in, otherwise the add-on
ignores every request it sees.

You can read the value off any machine on the network: `ip addr` on Linux,
`ifconfig` on macOS, `ipconfig` on Windows, or the router's status page.

### Option: `tftp_server_ip` (required)

The IPv4 address of the TFTP server holding the boot files. This is the
address the add-on hands to clients — it must be reachable from the clients,
not just from Home Assistant.

### Option: `boot_file_bios` (required)

The boot file for clients booting in legacy BIOS mode, as a path relative to
the TFTP server's root.

### Option: `boot_file_uefi` (required)

The boot file for 64-bit UEFI clients, which covers practically all modern
x86 hardware.

### Option: `boot_file_uefi_ia32`

The boot file for 32-bit UEFI clients. Rare, mostly older tablets and some
low-power devices. Defaults to `boot_file_uefi` when left empty.

### Option: `boot_file_uefi_arm64`

The boot file for 64-bit ARM UEFI clients. Defaults to `boot_file_uefi` when
left empty.

### Option: `interfaces`

The network interfaces to listen on, for example `eth0`. Leave the list empty
to listen on every interface, which is the right choice for a host with a
single network connection.

Set it explicitly when the Home Assistant host is attached to more than one
network and PXE should only be offered on one of them.

### Option: `log_level`

Controls how much the add-on writes to its log.

- `trace`, `debug`, `info` — every DHCP transaction is logged. `debug` and
  `trace` additionally print the generated dnsmasq configuration at startup.
- `notice`, `warning`, `error`, `fatal` — progressively quieter; only
  problems are reported.

`info` is a good default: it is quiet while nothing boots, and it shows the
full exchange when a client does.

## How it works

The add-on runs dnsmasq with `dhcp-range=<subnet>,proxy`. In this mode dnsmasq
never allocates addresses and never answers a plain DHCP request — it only
adds the boot server and boot file to the exchange that the network's real
DHCP server is already handling. The two servers do not conflict, because they
answer different questions.

Clients announce their firmware type in DHCP option 93. The add-on matches on
it and returns the matching boot file, so BIOS and UEFI machines on the same
network each get something they can actually execute. The answer is sent both
as DHCP options and over the PXE protocol on port 4011, since firmware differs
in which one it uses.

The add-on's DNS server is disabled entirely, so it does not interfere with
name resolution or with any DNS service running on the host.

Because proxy DHCP relies on broadcast traffic, the add-on needs
`host_network` — it runs directly on the host's network stack rather than in
an isolated container network.

## Troubleshooting

### The client boots straight from disk, never attempting PXE

This happens before the add-on is ever involved. Check the client firmware:

- Network stack / network boot: enabled
- IPv4 PXE support: enabled
- Network boot ahead of the local disks in the boot order

### Nothing appears in the add-on log while a client boots

The add-on is not seeing the client's broadcast.

- Confirm `subnet` matches the network the client is on.
- If the Home Assistant host has several interfaces, set `interfaces` to the
  one facing the clients.
- Check the router for client isolation, guest-network separation, or a
  separate VLAN between the host and the client.

### `PXE-E53: No boot filename received`

The client got an address but no boot information.

- Check the log for the incoming request. If the request is not there, see
  the previous section.
- Set `log_level` to `debug` and confirm the generated configuration lists
  your boot files.
- Some firmware reports an unusual architecture in option 93. With
  `log_level: debug` the log shows the client architecture that was matched.

### `PXE-E32: TFTP open timeout` or `PXE-E3B: TFTP error`

The boot server and file were delivered, but the transfer failed. This is a
TFTP problem, outside this add-on.

- Confirm the TFTP server is running and `tftp_server_ip` is correct.
- Confirm the file name matches what the TFTP server actually serves,
  including any subdirectory.
- Test the download from another machine on the same network:

  ```bash
  tftp <tftp_server_ip>
  tftp> get <boot_file_uefi>
  tftp> quit
  ```

### Clients start getting wrong addresses

The add-on never assigns addresses, so this points elsewhere — usually a
second full DHCP server on the network. To rule the add-on out, set
`log_level: debug` and confirm the generated configuration contains:

```
dhcp-range=<your subnet>,proxy
```

The `,proxy` suffix is what keeps it in proxy mode.
