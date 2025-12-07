"""Helpers for collecting LLDP data from network devices."""

import re
from typing import Any, Dict, List

from netmiko import ConnectHandler

# map vendor strings to netmiko device types
VENDOR_MAP = {
    "arubaos-switch": "hp_procurve",
    "arubaos_cx":     "aruba_aoscx",
    "cisco_ios":      "cisco_ios",
    "fortinet":       "fortinet",
}

def human_bytes(v: str) -> str:
    """Convert byte counts into a human-readable string when possible."""

    try:
        n = int(v.replace(",", ""))
    except (TypeError, ValueError, AttributeError):
        return v

    if n > 1_000_000_000:
        return f"{n/1_000_000_000:.2f} GB"
    if n > 1_000_000:
        return f"{n/1_000_000:.1f} MB"
    return v


def detect_vendor(output: str) -> str:
    """Infer the vendor from a device banner or command output."""

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


def collect_inventory(conn, vendor_key: str) -> Dict[str, Any]:
    """Gather inventory fields from a connected device."""

    inv: Dict[str, Any] = {}

    # ---- show system ----
    try:
        sys_out = conn.send_command("show system")

        # serial
        m = re.search(r"Serial Number\s+:\s*(\S+)", sys_out)
        if m:
            inv["serial"] = m.group(1)

        # base mac
        m = re.search(r"Base MAC Addr\s+:\s*(\S+)", sys_out)
        if m:
            inv["base_mac"] = m.group(1)

        # software
        m = re.search(r"Software revision\s+:\s*([\w\.]+)", sys_out)
        if m:
            inv["software"] = m.group(1)

        # uptime (only the X days portion)
        m = re.search(r"Up Time\s*:\s*([0-9]+\s+days?)", sys_out)
        if m:
            inv["uptime"] = m.group(1).strip()

        # cpu (%)
        m = re.search(r"CPU Util\s*\(\%\)\s*:\s*(\d+)", sys_out)
        if m:
            inv["cpu"] = m.group(1) + "%"

        # memory total
        m = re.search(r"Memory\s*-\s*Total\s*:\s*([\d,]+)", sys_out)
        if m:
            raw_total = m.group(1)
            inv["memory_total"] = raw_total
            inv["memory_total_hr"] = human_bytes(raw_total)

        # memory free
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

    return inv


def collect_lldp(host: str, username: str, password: str) -> Dict[str, Any]:
    """Collect inventory and LLDP neighbor data from the target device."""

    # connect generically to detect vendor
    base = {
        "device_type": "terminal_server",
        "host": host,
        "username": username,
        "password": password,
    }
    conn = ConnectHandler(**base)

    # minimal banner read
    banner = conn.find_prompt()
    try:
        banner += conn.send_command("show version", expect_string=r"#|>")
    except:
        pass
    conn.disconnect()

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
