import argparse
from src.lldp_collector import collect_lldp
from src.utils import print_table

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
    print("\n--- SYSTEM ---")
    for key in ["serial", "base_mac", "software", "bootrom", "uptime", "cpu"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")

    # ---- MEMORY ----
    print("\n--- MEMORY ---")
    if "memory_total_hr" in inv:
        print(f"{'total':15}: {inv['memory_total_hr']}")
    if "memory_free_hr" in inv:
        print(f"{'free':15}: {inv['memory_free_hr']}")

    # ---- HARDWARE / MODEL ----
    print("\n--- HARDWARE ---")
    for key in ["model", "sku"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")

    # ---- POWER ----
    print("\n--- POWER ---")
    for key in ["poe_total", "poe_used", "poe_remaining"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")

    if "power_supplies" in inv:
        print("\npower_supplies:")
        for ps in inv["power_supplies"]:
            print(f"   PSU{ps['psu']}: {ps['watts']}W - {ps['status']}")

    print()
    print_table(results["neighbors"])

if __name__ == "__main__":
    main()
