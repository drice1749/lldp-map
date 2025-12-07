import re
from netmiko import ConnectHandler

# map vendor strings to netmiko device types
VENDOR_MAP = {
    "arubaos-switch": "hp_procurve",     # ArubaOS Switch/ProCurve
    "arubaos_cx":     "aruba_aoscx",     # Aruba CX
    "cisco_ios":      "cisco_ios",
    "fortinet":       "fortinet",
}


def detect_vendor(output):
    text = output.lower()

    # ArubaOS-Switch / ProCurve
    if "arubaos-switch" in text or "procurve" in text or "arubaos" in text:
        return "arubaos-switch"

    # Aruba CX
    if "aruba" in text and "cx" in text:
        return "arubaos_cx"

    # Cisco
    if "cisco" in text:
        return "cisco_ios"

    # Fortinet
    if "fortigate" in text or "fortinet" in text:
        return "fortinet"

    # fallback default for your environment
    return "arubaos-switch"


def collect_inventory(conn, vendor_key):
    """
    Collect switch inventory from ArubaOS-Switch via 'show system' and 'show version'.
    """

    inv = {}

    # ---- get system info ----
    try:
        sys_out = conn.send_command("show system")

        # Serial Number
        m = re.search(r"Serial Number\s+:\s*(\S+)", sys_out)
        if m:
            inv["serial"] = m.group(1)

        # Base MAC
        m = re.search(r"Base MAC Addr\s+:\s*(\S+)", sys_out)
        if m:
            inv["base_mac"] = m.group(1)

        # Software revision
        m = re.search(r"Software revision\s+:\s*([\w\.]+)", sys_out)
        if m:
            inv["software"] = m.group(1)

        # Uptime
        m = re.search(r"Up Time\s*:\s*([\w\s]+)", sys_out)
        if m:
            inv["uptime"] = m.group(1).strip()

        # CPU Utilization
        m = re.search(r"CPU Util\s*\(\%\)\s*:\s*(\d+)", sys_out)
        if m:
            inv["cpu"] = m.group(1) + "%"

        # Memory Free
        m = re.search(r"Memory\s+-\s+Total\s+:\s*(\S+).*Free\s+:\s*(\S+)", sys_out)
        if m:
            inv["memory_total"] = m.group(1)
            inv["memory_free"] = m.group(2)

    except Exception as e:
        inv["system_error"] = str(e)

    # ---- get version info ----
    try:
        ver_out = conn.send_command("show version")

        # image version
        m = re.search(r"\n\s*([\w\.]+)\s*\n", ver_out)
        # optional: match WC version explicitly
        wc = re.search(r"WC\.\d+\.\d+\.\d+", ver_out)
        if wc:
            inv["software"] = wc.group(0)

        # bootrom
        boot = re.search(r"Boot ROM Version:\s*(\S+)", ver_out)
        if boot:
            inv["bootrom"] = boot.group(1)

    except Exception as e:
        inv["version_error"] = str(e)

    return inv
    # ---- get module info ----
    try:
        mod_out = conn.send_command("show modules")

        # Chassis line example:
        # Chassis: 2930M-48G-PoE+  JL322A         Serial Number:   SG78JQN66P
        m = re.search(r"Chassis:\s*([A-Za-z0-9\-+]+)\s+(\S+)", mod_out)
        if m:
            inv["model"] = m.group(1).strip()
            inv["sku"] = m.group(2).strip()

    except Exception as e:
        inv["modules_error"] = str(e)

    """
    Collect basic switch inventory: model, serial, modules.
    Currently supports ArubaOS-Switch. Extend per vendor.
    """
    inv = {}

    try:
        raw = conn.send_command("show inventory")

        # model
        m = re.search(r"Chassis\s+:\s*(.*)", raw)
        if m:
            inv["model"] = m.group(1).strip()

        # serial
        m = re.search(r"Serial\s+Number\s*:\s*(.*)", raw)
        if m:
            inv["serial"] = m.group(1).strip()

        # modules (optional)
        modules = re.findall(r"(?i)Module\s+\d+.*", raw)
        if modules:
            inv["modules"] = [m.strip() for m in modules]

    except Exception as e:
        inv["error"] = str(e)

    return inv
    # ---- get PoE power info ----
    try:
        pwr_out = conn.send_command("show power")

        # Total Available Power
        m = re.search(r"Total Available Power\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m:
            inv["poe_total"] = m.group(1) + " W"

        # Total Power Drawn
        m = re.search(r"Total Power Drawn\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m:
            inv["poe_used"] = m.group(1) + " W"

        # Total Remaining Power
        m = re.search(r"Total Remaining Power\s*:\s*([\d\.]+)\s*W", pwr_out)
        if m:
            inv["poe_remaining"] = m.group(1) + " W"

        # PSU status lines:
        # "1     0             Not Connected"
        # "2     740           POE+ Connected"
        psus = re.findall(r"(\d+)\s+(\d+)\s+([A-Za-z\+ ]+)", pwr_out)
        if psus:
            # store each PSU as a tuple or dict
            inv["power_supplies"] = []
            for ps, watts, status in psus:
                inv["power_supplies"].append({
                    "psu": ps,
                    "watts": watts,
                    "status": status.strip()
                })

    except Exception as e:
        inv["power_error"] = str(e)


def collect_lldp(host, username, password):

    # connect generically to detect vendor
    base = {
        "device_type": "terminal_server",
        "host": host,
        "username": username,
        "password": password,
    }

    conn = ConnectHandler(**base)

    # small banner/read
    banner = conn.find_prompt()
    try:
        banner += conn.send_command("show version", expect_string=r"#|>")
    except:
        pass

    conn.disconnect()

    # detect vendor
    vendor_key = detect_vendor(banner)
    device_type = VENDOR_MAP.get(vendor_key, "hp_procurve")

    print(f"[{host}] Vendor detected: {vendor_key} → {device_type}")

    # reconnect properly
    device = {
        "device_type": device_type,
        "host": host,
        "username": username,
        "password": password,
    }
    conn = ConnectHandler(**device)

    # disable paging
    for cmd in ["no page", "terminal length 0"]:
        try:
            conn.send_command(cmd)
        except:
            pass

    # collect inventory first
    inventory = collect_inventory(conn, vendor_key)

    # LLDP
    raw = conn.send_command("show lldp info remote-device detail")
    conn.disconnect()

    # parse neighbors
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

    # return both
    return {
        "inventory": inventory,
        "neighbors": neighbors
    }
