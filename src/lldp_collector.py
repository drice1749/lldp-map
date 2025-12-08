import re
import ipaddress
from netmiko import ConnectHandler

# map vendor strings to netmiko device types
VENDOR_MAP = {
    "arubaos-switch": "hp_procurve",
    "arubaos_cx":     "aruba_aoscx",
    "cisco_ios":      "cisco_ios",
    "fortinet":       "fortinet",
}


def human_bytes(v):
    try:
        n = int(v.replace(",", ""))
        if n > 1_000_000_000:
            return f"{n/1_000_000_000:.2f} GB"
        elif n > 1_000_000:
            return f"{n/1000000:.1f} MB"
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
    parts = text.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            prefix = start[0]
            try:
                s = int(start[1:])
                e = int(end[1:])
                for x in range(s, e+1):
                    result.append(f"{prefix}{x}")
            except:
                continue
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
    return "arubaos-switch"   # fallback


def collect_inventory(conn, vendor_key):
    inv = {}

    # ---- SYSTEM ----
    try:
        sys_out = conn.send_command("show system")

        m = re.search(r"Serial Number\s+:\s*(\S+)", sys_out)
        if m: inv["serial"] = m.group(1)

        m = re.search(r"Base MAC Addr\s+:\s*(\S+)", sys_out)
        if m: inv["base_mac"] = m.group(1)

        m = re.search(r"Software revision\s+:\s*([\w\.]+)", sys_out)
        if m: inv["software"] = m.group(1)

        m = re.search(r"Up Time\s*:\s*([0-9]+\s+days?)", sys_out)
        if m: inv["uptime"] = m.group(1).strip()

        m = re.search(r"CPU Util\s*\(\%\)\s*:\s*(\d+)", sys_out)
        if m: inv["cpu"] = m.group(1) + "%"

        m = re.search(r"Memory\s*-\s*Total\s*:\s*([\d,]+)", sys_out)
        if m:
            inv["memory_total_hr"] = human_bytes(m.group(1))

        m = re.search(r"Free\s*:\s*([\d,]+)", sys_out)
        if m:
            inv["memory_free_hr"] = human_bytes(m.group(1))

    except Exception as e:
        inv["system_error"] = str(e)

    # ---- VERSION ----
    try:
        ver_out = conn.send_command("show version")

        wc = re.search(r"WC\.\d+\.\d+\.\d+", ver_out)
        if wc: inv["software"] = wc.group(0)

        boot = re.search(r"Boot ROM Version:\s*(\S+)", ver_out)
        if boot: inv["bootrom"] = boot.group(1)

    except Exception as e:
        inv["version_error"] = str(e)

    # ---- MODULES ----
    try:
        mod_out = conn.send_command("show modules")
        m = re.search(r"Chassis:\s*([A-Za-z0-9\-+]+)\s+(\S+)", mod_out)
        if m:
            inv["model"] = m.group(1)
            inv["sku"] = m.group(2)
    except:
        pass

    # ---- POWER ----
    try:
        pwr_out = conn.send_command("show power")

        m = re.search(r"Total Available Power\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m: inv["poe_total"] = m.group(1) + " W"

        m = re.search(r"Total Power Drawn\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m: inv["poe_used"] = m.group(1) + " W"

        m = re.search(r"Total Remaining Power\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m: inv["poe_remaining"] = m.group(1) + " W"
    except:
        pass

    # ---- TRUNKS ----
    try:
        t_out = conn.send_command("show trunks")
        trunks = []
        for line in t_out.splitlines():
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            port = parts[0]
            m_grp = re.search(r"\bTrk\d+\b", line)
            if not m_grp:
                continue

            trunks.append({"port": port, "group": m_grp.group(0)})
        if trunks:
            inv["trunks"] = trunks
    except:
        pass

    # ---- LACP ----
    try:
        lacp_out = conn.send_command("show lacp")
        lacp = []
        in_table = False

        for line in lacp_out.splitlines():
            line = line.strip()
            if not line:
                continue

            if re.match(r"^-{3,}", line):
                in_table = True
                continue

            if not in_table:
                continue

            parts = line.split()
            if len(parts) >= 8:
                port, enabled, group, status, partner, partner_status, admin_key, oper_key = parts[:8]
                lacp.append({
                    "port": port,
                    "lacp_enabled": enabled,
                    "trunk_group": group,
                    "status": status,
                    "partner": partner,
                    "partner_status": partner_status,
                    "admin_key": admin_key,
                    "oper_key": oper_key,
                })
        if lacp:
            inv["lacp"] = lacp
    except Exception as e:
        inv["lacp_error"] = str(e)

    # ---- VLAN + PORT VLAN PARSING ----
    try:
        rc = conn.send_command("show running-config")
        inv["vlans_detail"] = {}
        inv["port_vlans"] = {}
        current_vlan = None

        for line in rc.splitlines():
            line = line.rstrip()

            m_vlan = re.match(r"^vlan\s+(\d+)", line)
            if m_vlan:
                current_vlan = m_vlan.group(1)
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

            # name
            m = re.search(r'name\s+"(.+)"', line)
            if m:
                inv["vlans_detail"][current_vlan]["name"] = m.group(1)

            # ip address
            m = re.search(r'ip address\s+(\S+)\s+(\S+)', line)
            if m:
                ip = m.group(1)
                mask = m.group(2)
                cidr = mask_to_cidr(mask)
                inv["vlans_detail"][current_vlan]["ip"] = f"{ip}/{cidr}" if cidr else ip
                inv["vlans_detail"][current_vlan]["l3"] = True
                inv["vlans_detail"][current_vlan]["l2_only"] = False

            # untagged
            m = re.search(r'untagged\s+(.+)$', line)
            if m:
                ports = expand_ports(m.group(1))
                for p in ports:
                    inv["vlans_detail"][current_vlan]["untagged"].append(p)
                    inv["port_vlans"].setdefault(p, {"tagged":[], "untagged":None})
                    inv["port_vlans"][p]["untagged"] = current_vlan

            # tagged
            m = re.search(r'tagged\s+(.+)$', line)
            if m:
                ports = expand_ports(m.group(1))
                for p in ports:
                    inv["vlans_detail"][current_vlan]["tagged"].append(p)
                    inv["port_vlans"].setdefault(p, {"tagged":[], "untagged":None})
                    inv["port_vlans"][p]["tagged"].append(current_vlan)

    except Exception as e:
        inv["vlan_error"] = str(e)

    return inv


def collect_lldp(host, username, password):
    # vendor detect
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

    print(f"[{host}] Vendor detected: {vendor_key} → {device_type}")

    # proper connection
    device = {
        "device_type": device_type,
        "host": host,
        "username": username,
        "password": password,
    }
    conn = ConnectHandler(**device)

    for cmd in ["no page", "terminal length 0"]:
        try: conn.send_command(cmd)
        except: pass

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

        m = re.search(r"Local Port\s*:\s*(\S+)", line)
        if m: current["local_port"] = m.group(1)

        m = re.search(r"ChassisId\s*:\s*(\S+)", line)
        if m: current["chassis_id"] = m.group(1)

        m = re.search(r"SysName\s*:\s*(.+)$", line)
        if m: current["system_name"] = m.group(1).strip()

        m = re.search(r"PortDescr\s*:\s*(.+)$", line)
        if m: current["port_descr"] = m.group(1).strip()

        if line.startswith("Type") and "ipv4" in line.lower():
            current["_next_addr_is_ipv4"] = True
            continue

        if line.startswith("Address") and current.get("_next_addr_is_ipv4"):
            parts = line.split(":")
            if len(parts) > 1:
                current["mgmt_ip"] = parts[1].strip()
            current.pop("_next_addr_is_ipv4", None)

    if current:
        neighbors.append(current)

    return {"inventory": inventory, "neighbors": neighbors}

