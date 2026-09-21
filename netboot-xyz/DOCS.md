# Netboot.xyz Documentation

PXE-Server to deploy a OS inside your local network.

## ⚙️ Configuration

Configure the app via the **Configuration** tab in the Home Assistant App page.

### Options

```yaml
dhcp_range: 192.168.1.200
log_level: info
path: /media/netboot/image
path_config: /media/netboot/config
menu_version: latest
```

- `dhcp_range` (Required): The DHCP range/proxy IP settings.
- `log_level` (Optional): The log level of the addon (e.g. `info`, `debug`, `trace`).
- `path` (Required): The storage path for netboot local assets.
- `path_config` (Required): The storage path for configurations/menus.
- `menu_version` (Optional): The version tag of the netboot.xyz menus and bootloader to use (e.g. `2.0.84` or `latest`). Set this to an older version if you experience keyboard lockup bugs with the latest upstream iPXE release.
- `tftp_server_ip` (Optional): See below.

### Option: `tftp_server_ip`

*(optional, default: empty)*

IP address of the machine running this add-on, as seen by PXE clients on
the LAN. Required only when the main DHCP server (e.g. router) does **not**
send DHCP option 66 (`next-server` / `siaddr`) pointing at this machine.
This is the case for AVM FritzBox and many other consumer routers.

When set, the value is injected into every `pxe-service=` line of the
generated `dnsmasq.conf` as the 4th field (TFTP server IP), and an
explicit `dhcp-boot=` directive is added for clients that don't read
`pxe-service` records.

Example: `tftp_server_ip: "192.168.178.100"` — the IP of your Home
Assistant host on the LAN.

Leave empty if your DHCP server correctly advertises this add-on's IP
as the `next-server`; then behaviour is identical to upstream.

### Network Ports

| Port | Protocol | Required | Description                                                                  |
| ---- | -------- | -------- | ---------------------------------------------------------------------------- |
| 85   | TCP      | ✅ Yes   | NGINX server for hosting boot assets. **Must stay at port 85 for PXE boot!** |
| 69   | UDP      | ✅ Yes   | TFTP server. **Must stay at port 69 for PXE boot!**                          |
| 3000 | TCP      | ❌ No    | Web configuration interface (uses Ingress, can be changed)                   |

> ⚠️ **Warning**: Changing ports 85 or 69 will break PXE boot functionality. Only the web UI port (3000) can be safely modified.

### Requirements

> ⚠️ **Important**: this app requires **Protection mode** to be **disabled** because it needs full network access for PXE/DHCP functionality. The app will fail to start if protection mode is enabled.

## 📂 Folder Usage

- `/media`: Used for storing boot images and configuration files. Path and config path are configurable via options:
  - `path`: `/media/netboot/image` (Location for bootable ISOs/images)
  - `path_config`: `/media/netboot/config` (Location for menu and instance configuration)
- `/data`: Used internally by the app for persistent meta-data storage.

## ⚠️ Secure Boot

**IMPORTANT**: netboot.xyz does **NOT** support Secure Boot!

The iPXE binaries used by netboot.xyz are not signed by Microsoft, which means they will fail Secure Boot's signature verification.

### If you see "signature verification failed" errors

1. Enter your computer's BIOS/UEFI settings (usually F2, F10, F12, or Del during boot)
2. Navigate to the Security or Boot settings
3. **Disable Secure Boot**
4. Save changes and reboot
5. Try PXE booting again

### Why is this necessary?

Secure Boot requires all boot loaders to be cryptographically signed by a trusted authority (typically Microsoft). Since netboot.xyz uses open-source iPXE binaries that are not Microsoft-signed, they cannot pass Secure Boot verification.

## Support

For issues and feature requests, please use the GitHub repository issues.
