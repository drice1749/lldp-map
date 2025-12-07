import re
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
    return "arubaos-switch"   # safe fallback


# -------------------------------------------------------------------
# PARSE TRUNKS (UPDATED to normalize "Trk60 LACP" → "Trk60")
# -------------------------------------------------------------------
def parse_aos_trunks(output: str):
    trunks = []
    if not output:
        return trunks

    for line in output.splitlines():
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue

        port = parts[0]
        if not port or not port[0].isdigit():
            continue

        name = parts[1] or None
        type_ = parts[2] or None

        raw_group = parts[3] or None
        group = raw_group.split()[0] if raw_group else None   # <<< normalize

        trunks.append({
            "port": port,
            "name": name,
            "type": type_,
            "group": group,
        })
    return trunks


# -------------------------------------------------------------------
# PARSE LACP
# -------------------------------------------------------------------
def parse_aos_lacp(output: str):
    entries = []
    if not output:
        return entries

    for line in output.splitlines():
        line = line.rstrip()
        if not line or "Port" in line:
            continue
        m = re.match(
            r"\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)",
            line
        )
        if not m:
            continue
        (
            port,
            enabled,
            group,
            status,
            partner,
            partner_status,
            admin_key,
            oper_key,
        ) = m.groups()

        entries.append({
            "port": port,
            "lacp_enabled": enabled,
            "trunk_group": group,
            "status": status,
            "partner": partner,
            "partner_status": partner_status,
            "admin_key": admin_key,
            "oper_key": oper_key,
        })
    return entries


# -------------------------------------------------------------------
# INVENTORY
# -------------------------------------------------------------------
def collect_inventory(conn, vendor_key):
    inv = {}

    # ---- show system ----
    try:
        sys_out = conn.send_command("show system")

        m = re.search(r"Serial Number\s+:\s*(\S+)", sys_out)
        if m:
            inv["serial"] = m.group(1)

        m = re.search(r"Base MAC Addr\s+:\s*(\S+)", sys_out)
        if m:
            inv["base_mac"] = m.group(1)

        m = re.search(r"Software revision\s+:\s*([\w\.]+)", sys_out)
        if m:
            inv["software"] = m.group(1)

        m = re.search(r"Up Time\s*:\s*([0-9]+\s+days?)", sys_out)
        if m:
            inv["uptime"] = m.group(1).strip()

        m = re.search(r"CPU Util\s*\(\%\)\s*:\s*(\d+)", sys_out)
        if m:
            inv["cpu"] = m.group(1) + "%"

        m = re.search(r"Memory\s*-\s*Total\s*:\s*([\d,]+)", sys_out)
        if m:
            raw_total = m.group(1)
            inv["memory_total"] = raw_total
            inv["memory_total_hr"] = human_bytes(raw_total)

        m = re.search(r"Free\s*:\s*([\d,]+)", sys_out)
        if m:
            raw_free = m.group(1)
            inv["memory_free"] = raw_free
            inv["memory_free_hr"] = human_bytes(raw_free)

    except Exception as e:
        inv["system_error"] = str(e)

    # ---- show version ----
    try:
        ver_out = conn.send_command("show version")

        wc = re.search(r"WC\.\d+\.\d+\.\d+", ver_out)
        if wc:
            inv["software"] = wc.group(0)

        boot = re.search(r"Boot ROM Version:\s*(\S+)", ver_out)
        if boot:
            inv["bootrom"] = boot.group(1)

    except Exception as e:
        inv["version_error"] = str(e)

    # ---- show modules ----
    try:
        mod_out = conn.send_command("show modules")
        m = re.search(r"Chassis:\s*([A-Za-z0-9\-+]+)\s+(\S+)", mod_out)
        if m:
            inv["model"] = m.group(1)
            inv["sku"] = m.group(2)
    except Exception as e:
        inv["modules_error"] = str(e)

    # ---- show power ----
    try:
        pwr_out = conn.send_command("show power")

        m = re.search(r"Total Available Power\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m:
            inv["poe_total"] = m.group(1) + " W"

        m = re.search(r"Total Power Drawn\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m:
            inv["poe_used"] = m.group(1) + " W"

        m = re.search(r"Total Remaining Power\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m:
            inv["poe_remaining"] = m.group(1) + " W"

        psus = re.findall(r"(\d+)\s+(\d+)\s+([A-Za-z\+ ]+)", pwr_out)
        if psus:
            inv["power_supplies"] = []
            for ps, watts, status in psus:
                inv["power_supplies"].append({
                    "psu": ps,
                    "watts": watts,
                    "status": status.strip()
                })

    except Exception as e:
        inv["power_error"] = str(e)

    # ---- NEW: trunk & LACP for ArubaOS-Switch ----
    if vendor_key == "arubaos-switch":
        try:
            tr_raw = conn.send_command("show trunks")
            inv["trunks"] = parse_aos_trunks(tr_raw)
        except Exception as e:
            inv["trunks_error"] = str(e)

        try:
            lacp_raw = conn.send_command("show lacp")
            inv["lacp"] = parse_aos_lacp(lacp_raw)
        except Exception as e:
            inv["lacp_error"] = str(e)

    return inv


# -------------------------------------------------------------------
# MAIN LLDP
# -------------------------------------------------------------------
def collect_lldp(host, username, password):

    base = {
        "device_type": "terminal_server",
        "host": host,
        "username": username,
        "password": password,
    }
    conn = ConnectHandler(**base)

    banner = conn.find_prompt()
    try:
        banner += conn.send_command("show version", expect_string=r"#|>")
    except:
        pass
    conn.disconnect()

    vendor_key = detect_vendor(banner)
    device_type = VENDOR_MAP.get(vendor_key, "hp_procurve")

    print(f"[{host}] Vendor detected: {vendor_key} → {device_type}")

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

        if "Address :" in line:
            parts = line.split(":")
            if len(parts) > 1:
                current["mgmt_ip"] = parts[1].strip()

    if current:
        neighbors.append(current)

    return {"inventory": inventory, "neighbors": neighbors}
