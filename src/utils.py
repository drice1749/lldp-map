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

        if mgmt:
            print(f"{local} → {sysname} ({chassis})  mgmt:{mgmt}")
        else:
            print(f"{local} → {sysname} ({chassis})")
