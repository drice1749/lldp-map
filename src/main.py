"""CLI entrypoint for collecting and displaying LLDP information."""

import argparse
from src.utils import collect_inventory
from src.lldp_collector import collect_lldp
<<<<<<< Updated upstream
from src.utils import print_inventory, print_table

def main():
    parser = argparse.ArgumentParser(
        description="Collect and display LLDP neighbors and device inventory."
    )
    parser.add_argument("--switch", required=True, help="switch hostname or IP")
    parser.add_argument("--username", required=True, help="login username")
    parser.add_argument("--password", required=True, help="login password")
    args = parser.parse_args()

    results = collect_lldp(args.switch, args.username, args.password)
    print_inventory(results["inventory"])
    print_table(results["neighbors"])
=======


def pretty_print(inv, neigh):
    print("\n========================")
    print("       INVENTORY        ")
    print("========================")

    print("\n--- SYSTEM ---")
    for k in ["serial", "base_mac", "software", "bootrom", "uptime", "cpu"]:
        if k in inv:
            print(f"{k:15}: {inv[k]}")

    print("\n--- MEMORY ---")
    for k in ["memory_total", "memory_free"]:
        if k in inv:
            print(f"{k:15}: {inv[k]} MB")

    print("\n--- HARDWARE ---")
    for k in ["model", "sku"]:
        if k in inv:
            print(f"{k:15}: {inv[k]}")

    print("\n--- POWER ---")
    for k in ["poe_total", "poe_used", "poe_remaining"]:
        if k in inv:
            print(f"{k:15}: {inv[k]}")

    print("\n--- POWER SUPPLIES ---")
    for ps in inv.get("psu_detail", []):
        if ps["state"] == "Not Present":
            print(f"PSU{ps['psu']}: Not Present")
        else:
            print(f"PSU{ps['psu']}: {ps['model']}  (Serial: {ps['serial']})")
            print(f"       State: {ps['state']}")
            print(f"       Power: {ps['power']} / {ps['max']} max")

    print("\n--- ENVIRONMENT ---")
    for k in ["temp_current", "temp_min", "temp_max", "temp_threshold", "temp_alarm"]:
        if k in inv:
            print(f"{k:15}: {inv[k]}")

    print("\n=== LLDP Neighbors ===")
    for n in neigh:
        print(f"{n['port']} → {n['sysname']} ({n['chassis']})  mgmt:{n['mgmt_ip']}")

>>>>>>> Stashed changes

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--switch", required=True)
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    args = p.parse_args()

    inv = collect_inventory(args.switch, args.username, args.password)
    neigh = collect_lldp(args.switch, args.username, args.password)

    print(f"[{args.switch}] Vendor detected: {inv.get('vendor')}")

    pretty_print(inv, neigh)
