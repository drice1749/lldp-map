import argparse
from src.lldp_collector import collect_lldp
from src.utils import print_table


def print_lacp_detail(inv, neighbors):
    lacp = inv.get("lacp", [])
    trunks = inv.get("trunks", [])

    trunk_members = {}
    for t in trunks:
        grp = t.get("group")
        if grp:
            trunk_members.setdefault(grp, []).append(t["port"])

    neigh_by_port = {}
    for n in neighbors:
        p = n.get("local_port")
        neigh_by_port.setdefault(p, []).append(n)

    print("\n--- LACP ---\n")

    for grp, ports in trunk_members.items():
        print(f"  {grp}:")

        chk_status = set()
        chk_partner = set()
        lldp_missing_on_up = False

        for p in ports:
            entry = next((l for l in lacp if l.get("port") == p), {})
            status = entry.get("status","?")
            chk_status.add(status)

            partner = "unknown"
            partner_port = "unknown"

            if p in neigh_by_port:
                n = neigh_by_port[p][0]
                sysname = n.get("system_name","?")
                chassis = n.get("chassis_id","?")
                partner = f"{sysname} ({chassis})"
                partner_port = n.get("port_descr") or "?"
            else:
                # LLDP missing
                if status.lower() == "up":
                    lldp_missing_on_up = True

            chk_partner.add(partner)

            # Always show partner port (even if different)
            print(f"    Port {p:<3} status:{status:<4} partner:{partner}   port:{partner_port}")

        # TRUE mismatch logic:
        # Warn only if:
        #   1) a link is down
        #   OR
        #   2) partner SYSTEM differs
        if ("Down" in chk_status) or len(chk_partner) > 1:
            print("      ⚠ WARNING: LACP link mismatch detected")

        # LLDP missing only matters if link is Up
        if lldp_missing_on_up:
            print("      ⚠ WARNING: LLDP missing on active LACP member (best practice to enable)")

        print()


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

    # SYSTEM
    print("\n--- SYSTEM ---")
    for key in ["serial", "base_mac", "software", "bootrom", "uptime", "cpu"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")

    print("\n--- MEMORY ---")
    if "memory_total_hr" in inv:
        print(f"{'total':15}: {inv['memory_total_hr']}")
    if "memory_free_hr" in inv:
        print(f"{'free':15}: {inv['memory_free_hr']}")

    print("\n--- HARDWARE ---")
    for key in ["model", "sku"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")

    print("\n--- POWER ---")
    for key in ["poe_total", "poe_used", "poe_remaining"]:
        if key in inv:
            print(f"{key:15}: {inv[key]}")

    if "power_supplies" in inv:
        print("\npower_supplies:")
        for ps in inv["power_supplies"]:
            print(f"   PSU{ps['psu']}: {ps['watts']}W - {ps['status']}")

    # New LACP output with improved warnings
    print_lacp_detail(inv, results["neighbors"])

    # LLDP neighbors table
    print_table(results["neighbors"])


if __name__ == "__main__":
    main()

