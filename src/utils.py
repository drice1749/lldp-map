<<<<<<< Updated upstream
"""Utility helpers for displaying LLDP results."""

from typing import Dict, Iterable, List


def _print_section(title: str, rows: Iterable[str]) -> None:
    print(f"\n--- {title} ---")
    for row in rows:
        print(row)


def print_inventory(inventory: Dict[str, str]) -> None:
    """Pretty-print the collected inventory summary.

    Args:
        inventory: Mapping of inventory keys to values returned by the collector.
    """

    print("\n========================")
    print("       INVENTORY        ")
    print("========================")

    sections = [
        (
            "SYSTEM",
            [
                ("serial", "serial"),
                ("base_mac", "base_mac"),
                ("software", "software"),
                ("bootrom", "bootrom"),
                ("uptime", "uptime"),
                ("cpu", "cpu"),
            ],
        ),
        ("MEMORY", [("memory_total_hr", "total"), ("memory_free_hr", "free")]),
        ("HARDWARE", [("model", "model"), ("sku", "sku")]),
        (
            "POWER",
            [
                ("poe_total", "poe_total"),
                ("poe_used", "poe_used"),
                ("poe_remaining", "poe_remaining"),
            ],
        ),
    ]

    for title, fields in sections:
        rows: List[str] = []
        for key, label in fields:
            if key in inventory:
                rows.append(f"{label:15}: {inventory[key]}")
        _print_section(title, rows)

    if "power_supplies" in inventory:
        supplies = [
            f"   PSU{ps['psu']}: {ps['watts']}W - {ps['status']}"
            for ps in inventory["power_supplies"]
        ]
        _print_section("POWER SUPPLIES", ["power_supplies:"] + supplies)


def print_table(results: Iterable[Dict[str, str]]) -> None:
    """Print a compact table of LLDP neighbor entries."""

    print("\n=== LLDP Neighbors ===")
    for r in results:
        local = r.get("local_port", "?")
        sysname = r.get("system_name", "?")
        chassis = r.get("chassis_id", "?")
        mgmt = r.get("mgmt_ip", "")
=======
import re
from netmiko import ConnectHandler
>>>>>>> Stashed changes


def detect_vendor(conn):
    out = conn.send_command("show version")
    if "WC." in out:
        return "hp_procurve"
    return "unknown"


def collect_inventory(ip, username, password):
    device = {
        "device_type": "hp_procurve",
        "host": ip,
        "username": username,
        "password": password,
        "fast_cli": False
    }

    conn = ConnectHandler(**device)
    inv = {}
    vendor = detect_vendor(conn)
    inv["vendor"] = vendor

    # ----- SHOW SYSTEM -----
    sys = conn.send_command("show system")

    m = re.search(r"Serial Number\s+:\s+(\S+)", sys)
    if m: inv["serial"] = m.group(1)

    m = re.search(r"Base MAC Addr\s+:\s+(\S+)", sys)
    if m: inv["base_mac"] = m.group(1)

    m = re.search(r"Software revision\s+:\s+(\S+)", sys)
    if m: inv["software"] = m.group(1)

    m = re.search(r"ROM Version\s+:\s+(\S+)", sys)
    if m: inv["bootrom"] = m.group(1)

    m = re.search(r"Up Time\s+:\s+([^\n]+)", sys)
    if m: inv["uptime"] = m.group(1).strip()

    m = re.search(r"CPU Util.*:\s+(\d+)", sys)
    if m: inv["cpu"] = m.group(1) + "%"

    # Memory total / free
    m = re.search(r"Memory.*Total\s+:\s+([\d,]+)", sys)
    if m:
        total = int(m.group(1).replace(",", ""))
        inv["memory_total"] = round(total / (1024 * 1024), 1)

    m = re.search(r"Free\s+:\s+([\d,]+)", sys)
    if m:
        free = int(m.group(1).replace(",", ""))
        inv["memory_free"] = round(free / (1024 * 1024), 1)

    # ----- MODULES -----
    modules = conn.send_command("show modules")
    m = re.search(r"Chassis:\s+([^\n]+)", modules)
    if m:
        parts = m.group(1).strip().split()
        inv["model"] = parts[0]
        inv["sku"] = parts[-1]

    # ----- POE -----
    poe = conn.send_command("show power")

    m = re.search(r"Total Available Power\s+:\s+(\d+)", poe)
    if m: inv["poe_total"] = m.group(1) + " W"

    m = re.search(r"Total Power Drawn\s+:\s+(\d+)", poe)
    if m: inv["poe_used"] = m.group(1) + " W"

    m = re.search(r"Total Remaining Power\s+:\s+(\d+)", poe)
    if m: inv["poe_remaining"] = m.group(1) + " W"

    # ----- TEMPERATURE -----
    temp = conn.send_command("show system temperature")
    m = re.search(r"Chassis\s+(\d+)C\s+(\d+)C\s+(\d+)C\s+(\d+)C\s+(\S+)", temp)
    if m:
        inv["temp_current"] = m.group(1) + "C"
        inv["temp_max"] = m.group(2) + "C"
        inv["temp_min"] = m.group(3) + "C"
        inv["temp_threshold"] = m.group(4) + "C"
        inv["temp_alarm"] = "YES" if m.group(5).upper() != "NO" else "NO"

    # ----- POWER SUPPLY -----
    ps_out = conn.send_command("show system power-supply")

    supplies = []
    for line in ps_out.splitlines():

        if "Not Present" in line:
            m = re.search(r"^\s*(\d+)", line)
            if m:
                supplies.append({
                    "psu": m.group(1),
                    "model": None,
                    "serial": None,
                    "state": "Not Present",
                    "power": "0 W",
                    "max": "0 W"
                })
            continue

        m = re.search(
            r"^\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+).*?(\d+)\s+(\d+)",
            line
        )
        if m:
            supplies.append({
                "psu": m.group(1),
                "model": m.group(2),
                "serial": m.group(3),
                "state": m.group(4),
                "power": m.group(5) + " W",
                "max": m.group(6) + " W"
            })

    inv["psu_detail"] = supplies

    conn.disconnect()
    return inv
