# === lldp_collector.py ===
import re
import ipaddress
from netmiko import ConnectHandler
from src.utils import console


# ------------------------------------------------------------
# PORT SORTING HELPERS
# ------------------------------------------------------------

def sort_key_port(port):
    if port is None:
        return (5, 9999, 9999, 9999)

    p = str(port).strip()

    if p.isdigit():
        return (1, int(p), 0, 0)

    m = re.match(r"^([A-Za-z])(\d+)$", p)
    if m:
        return (2, ord(m.group(1).upper()), int(m.group(2)), 0)

    if "/" in p:
        parts = p.split("/")
        if all(x.isdigit() for x in parts):
            return (3, int(parts[0]), int(parts[1]), int(parts[2]))

    return (5, str(p), 0, 0)


# ------------------------------------------------------------
# VENDOR MAP
# ------------------------------------------------------------

VENDOR_MAP = {
    "arubaos-switch": "hp_procurve",
    "arubaos_cx":     "aruba_aoscx",
    "cisco_ios":      "cisco_ios",
    "fortinet":       "fortinet",
}


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def human_bytes(v):
    try:
        n = int(v.replace(",", ""))
        if n > 1_000_000_000:
            return f"{n/1_000_000_000:.2f} GB"
        elif n > 1_000_000:
            return f"{n/1_000_000:.1f} MB"
        return v
    except:
        return v


def mask_to_cidr(mask):
    try:
        return ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
    except:
        return None


def expand_ports(text):
    result = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            prefix = start[0]
            try:
                for i in range(int(start[1:]), int(end[1:]) + 1):
                    result.append(f"{prefix}{i}")
            except:
                pass
        else:
            result.append(part)
    return result


def detect_vendor(output):
    text = output.lower()
    if "arubaos" in text or "procurve" in text:
        return "arubaos-switch"
    if "aruba" in text and "cx" in text:
        return "arubaos_cx"
    if "cisco" in text:
        return "cisco_ios"
    if "fortigate" in text or "fortinet" in text:
        return "fortinet"
    return "arubaos-switch"


# ------------------------------------------------------------
# INVENTORY COLLECTION
# ------------------------------------------------------------

def collect_inventory(conn, vendor_key):
    inv = {}

    # ---------------- SYSTEM ----------------
    try:
        sys_out = conn.send_command("show system")

        for pat, key in [
            (r"Serial Number\s+:\s*(\S+)", "serial"),
            (r"Base MAC Addr\s+:\s*(\S+)", "base_mac"),
            (r"Software revision\s+:\s*([\w\.]+)", "software"),
            (r"Up Time\s*:\s*([0-9]+\s+days?)", "uptime"),
            (r"CPU Util\s*\(\%\)\s*:\s*(\d+)", "cpu"),
        ]:
            m = re.search(pat, sys_out)
            if m:
                inv[key] = m.group(1)

        m = re.search(r"Memory\s*-\s*Total\s*:\s*([\d,]+)", sys_out)
        if m:
            inv["memory_total_hr"] = human_bytes(m.group(1))

        m = re.search(r"Memory\s*-\s*Free\s*:\s*([\d,]+)", sys_out)
        if m:
            inv["memory_free_hr"] = human_bytes(m.group(1))

    except Exception as e:
        inv["system_error"] = str(e)

    # ---------------- VERSION ----------------
    try:
        ver_out = conn.send_command("show version")
        wc = re.search(r"WC\.\d+\.\d+\.\d+", ver_out)
        if wc:
            inv["software"] = wc.group(0)

        boot = re.search(r"Boot ROM Version:\s*(\S+)", ver_out)
        if boot:
            inv["bootrom"] = boot.group(1)
    except:
        pass

    # ---------------- MODULES ----------------
    try:
        mod_out = conn.send_command("show modules")
        m = re.search(r"Chassis:\s*([A-Za-z0-9\-+]+)\s+(\S+)", mod_out)
        if m:
            inv["model"], inv["sku"] = m.group(1), m.group(2)
    except:
        pass

    # ---------------- POWER ----------------
    try:
        pwr_out = conn.send_command("show power")
        for pat, key in [
            (r"Total Available Power\s*:\s*([\d\.]+)", "poe_total"),
            (r"Total Power Drawn\s*:\s*([\d\.]+)", "poe_used"),
            (r"Total Remaining Power\s*:\s*([\d\.]+)", "poe_remaining"),
        ]:
            m = re.search(pat, pwr_out)
            if m:
                inv[key] = f"{m.group(1)} W"
    except:
        pass

    # ---------------- TRUNKS ----------------
    try:
        t_out = conn.send_command("show trunks")
        trunks = []
        for line in t_out.splitlines():
            m = re.search(r"^(\S+).*\b(Trk\d+)\b", line)
            if m:
                trunks.append({"port": m.group(1), "group": m.group(2)})
        if trunks:
            inv["trunks"] = trunks
    except:
        pass

    # ---------------- INTERFACES ----------------
    if vendor_key == "arubaos-switch":
        try:
            iface_out = conn.send_command("show interfaces brief")
            inv["interfaces"] = {}

            for raw_line in iface_out.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                parts = line.split()
                if not parts[0].isdigit() or len(parts) < 7:
                    continue

                port = parts[0]
                inv["interfaces"][port] = {
                    "status": parts[5],
                    "speed": parts[6],
                    "description": ""
                }

            for port in inv["interfaces"]:
                desc_out = conn.send_command(f"show interfaces {port}")
                m = re.search(r"Name\s*:\s*(.+)", desc_out)
                if m:
                    inv["interfaces"][port]["description"] = m.group(1).strip()

        except Exception as e:
            inv["interface_error"] = str(e)

    # ---------------- VLAN / PORT MAP ----------------
    try:
        rc = conn.send_command("show running-config")
        inv["vlans_detail"] = {}
        inv["port_vlans"] = {}
        current_vlan = None

        for line in rc.splitlines():
            m = re.match(r"^vlan\s+(\d+)", line)
            if m:
                current_vlan = m.group(1)
                inv["vlans_detail"].setdefault(current_vlan, {
                    "name": None,
                    "ip": None,
                    "untagged": [],
                    "tagged": [],
                    "l3": False,
                    "l2_only": True,
                })
                continue

            if not current_vlan:
                continue

            m = re.search(r'name\s+"(.+)"', line)
            if m:
                inv["vlans_detail"][current_vlan]["name"] = m.group(1)

            m = re.search(r'ip address\s+(\S+)\s+(\S+)', line)
            if m:
                cidr = mask_to_cidr(m.group(2))
                inv["vlans_detail"][current_vlan]["ip"] = f"{m.group(1)}/{cidr}"
                inv["vlans_detail"][current_vlan]["l3"] = True
                inv["vlans_detail"][current_vlan]["l2_only"] = False

            for tag_type in ("untagged", "tagged"):
                m = re.search(rf"{tag_type}\s+(.+)$", line)
                if m:
                    for p in expand_ports(m.group(1)):
                        inv["vlans_detail"][current_vlan][tag_type].append(p)
                        inv["port_vlans"].setdefault(p, {"untagged": None, "tagged": []})
                        if tag_type == "untagged":
                            inv["port_vlans"][p]["untagged"] = current_vlan
                        else:
                            inv["port_vlans"][p]["tagged"].append(current_vlan)

    except Exception as e:
        inv["vlan_error"] = str(e)

    return inv


# ------------------------------------------------------------
# LLDP COLLECTION
# ------------------------------------------------------------

def collect_lldp(host, username, password):
    """Detect vendor, collect inventory, then LLDP neighbors."""

    base = {
        "device_type": "terminal_server",
        "host": host,
        "username": username,
        "password": password,
    }

    conn = ConnectHandler(**base)
    banner = conn.find_prompt()
    try:
        banner += conn.send_command("show version")
    except:
        pass
    conn.disconnect()

    vendor_key = detect_vendor(banner)
    device_type = VENDOR_MAP.get(vendor_key, "hp_procurve")

    console.print(
        f"[bold cyan][{host}][/bold cyan] Vendor detected: "
        f"[yellow]{vendor_key}[/yellow] → [green]{device_type}[/green]"
    )

    conn = ConnectHandler(
        device_type=device_type,
        host=host,
        username=username,
        password=password,
    )

    for cmd in ("no page", "terminal length 0"):
        try:
            conn.send_command(cmd)
        except:
            pass

    inventory = collect_inventory(conn, vendor_key)

    raw = conn.send_command("show lldp info remote-device detail")
    conn.disconnect()

    neighbors = []
    current = {}

    for line in raw.splitlines():
        line = line.strip()

        if line.startswith("Local Port"):
            if current:
                neighbors.append(current)
            current = {}

        if m := re.search(r"Local Port\s*:\s*(\S+)", line):
            current["local_port"] = m.group(1)

        if m := re.search(r"ChassisId\s*:\s*(\S+)", line):
            current["chassis_id"] = m.group(1)

        if m := re.search(r"SysName\s*:\s*(.+)", line):
            current["system_name"] = m.group(1).strip()

        if m := re.search(r"PortId\s*:\s*(.+)", line):
            if m.group(1).strip():
                current["port_descr"] = m.group(1).strip()

        if m := re.search(r"PortDescr\s*:\s*(.+)", line):
            if "port_descr" not in current:
                current["port_descr"] = m.group(1).strip() or "—"

        if line.lower().startswith("type") and "ipv4" in line.lower():
            current["_expect_ipv4"] = True
            continue

        if current.get("_expect_ipv4") and line.lower().startswith("address"):
            current["mgmt_ip"] = line.split(":")[-1].strip()
            del current["_expect_ipv4"]

    if current:
        neighbors.append(current)

    neighbors.sort(key=lambda x: sort_key_port(x.get("local_port")))

    return {
        "inventory": inventory,
        "neighbors": neighbors,
    }
