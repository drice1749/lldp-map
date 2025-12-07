import argparse
from src.lldp_collector import collect_lldp
from src.utils import print_table

def print_section(title):
    print(f"\n--- {title} ---")

def print_power_supplies(inv):
    if "power_supplies" in inv:
        print("\npower_supplies:")
        for ps in inv["power_supplies"]:
            print(f"   PSU{ps['psu']:>2}: {ps['watts']}W - {ps['status']}")

def print_trunks(inv):
    trunks = inv.get("trunks", [])
    if not trunks:
        return
    print_section("TRUNKS")

    # group by trunk
    groups = {}
    for t in trunks:
        g = t.get("group") or "Unknown"
        groups.setdefault(g, []).append(t)

    for grp, items in groups.items():
        print(f"\n  {grp}:")
        for item in items:
            port = item.get("port", "?")
            name = item.get("name", "") or ""
            typ  = item.get("type", "")
            print(f"    Port {port:<3} {name:<20} ({typ})")


def print_lacp(inv):
    lacp = inv.get("lacp", [])
    if not lacp:
        return
    print_section("LACP")

    groups = {}
    for entry in lacp:
        grp = entry.get("trunk_group", "Unknown")
        groups.setdefault(grp, []).append(entry)

    for grp, items in groups.items():
        print(f"\n  {grp}:")
        for e in items:
            port   = e["port"]
            status = e["status"]
            partner = e["partner"]
            print(f"    Port {port:<3} status:{status:<4} partner:{partner}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    results = collect_lldp(args.switch, args.username, args.password)
    inv = results["inventory"]

    print("\n========================")
    print("       INVENTORY        ")
    print("========================")

    # ---- SYSTEM ----
    print_section("SYSTEM")
    for key in ["serial", "base_mac", "software", "bootrom", "uptime", "cpu"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")

    # ---- MEMORY ----
    print_section("MEMORY")
    if "memory_total_hr" in inv:
        print(f"{'total':15}: {inv['memory_total_hr']}")
    if "memory_free_hr" in inv:
        print(f"{'free':15}: {inv['memory_free_hr']}")

    # ---- HARDWARE / MODEL ----
    print_section("HARDWARE")
    for key in ["model", "sku"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")

    # ---- POWER ----
    print_section("POWER")
    for key in ["poe_total", "poe_used", "poe_remaining"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")
    print_power_supplies(inv)

    # ---- TRUNKS + LACP (pretty) ----
    print_trunks(inv)
    print_lacp(inv)

    # ---- NEIGHBORS ----
    print()
    print_table(results["neighbors"])

if __name__ == "__main__":
    main()
