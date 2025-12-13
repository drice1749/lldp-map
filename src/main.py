#=== main.py ===

import argparse
from src.lldp_collector import collect_lldp
from src.utils import (
    console,
    section,
    kv_table,
    vlan_block,
    port_vlan_table,
    lacp_table,
    lldp_table,
)


def format_inventory(inv):
    section("INVENTORY")

    kv_table("System", {
        "Serial": inv.get("serial"),
        "Base MAC": inv.get("base_mac"),
        "Software": inv.get("software"),
        "Boot ROM": inv.get("bootrom"),
        "Uptime": inv.get("uptime"),
        "CPU Load": inv.get("cpu"),
    })

    kv_table("Memory", {
        "Total": inv.get("memory_total_hr"),
        "Free": inv.get("memory_free_hr"),
    })

    kv_table("Hardware", {
        "Model": inv.get("model"),
        "SKU": inv.get("sku"),
    })

    kv_table("Power", {
        "PoE Total": inv.get("poe_total"),
        "Used": inv.get("poe_used"),
        "Remaining": inv.get("poe_remaining"),
    })


def format_vlan_summary(inv):
    if "vlans_detail" not in inv:
        return

    section("VLAN SUMMARY")

    for vlan_id, vlan in sorted(inv["vlans_detail"].items(), key=lambda x: int(x[0])):
        vlan_block({
            "id": vlan_id,
            "name": vlan.get("name"),
            "ip": vlan.get("ip") or "—",
            "role": "L3" if vlan.get("l3") else "L2 only",
            "untagged": ", ".join(vlan.get("untagged", [])) or "—",
            "tagged": ", ".join(vlan.get("tagged", [])) or "—",
        })


def format_port_vlan_table(inv):
    if "port_vlans" not in inv:
        return

    section("PORT VLAN MAP")
    port_vlan_table(inv["port_vlans"], inv.get("interfaces", {}))


def format_lacp(inv, neighbors):
    trunks = inv.get("trunks", [])
    lacp_struct = {}

    for t in trunks:
        grp = t.get("group")
        if not grp:
            continue

        lacp_struct.setdefault(grp, [])

        partner = "unknown"
        partner_port = "unknown"

        for n in neighbors:
            if n.get("local_port") == t["port"]:
                partner = f"{n.get('system_name', '?')} ({n.get('chassis_id', '?')})"
                partner_port = n.get("port_descr") or "unknown"
                break

        lacp_struct[grp].append({
            "port_num": t["port"],
            "status": "?",
            "partner": partner,
            "port": partner_port,
        })

    section("LACP STATUS")
    lacp_table(lacp_struct)

def vlan1_risk_check(inv):
    vlans = inv.get("vlans_detail", {})
    v1 = vlans.get("1")

    if not v1:
        return

    untagged = v1.get("untagged", [])
    tagged = v1.get("tagged", [])

    if not tagged and not untagged:
        return

    section("NETWORK RISK WARNING")

    console.print("[bold red]⚠ VLAN 1 Risk Detected[/bold red]")

    if tagged:
        console.print("  • VLAN 1 is tagged on one or more ports")

    if untagged:
        console.print(f"  • VLAN 1 is untagged on {len(untagged)} ports")

    if tagged and untagged:
        console.print("  • VLAN 1 is used as both tagged and untagged (native + transit)")

    console.print(
        "\n[dim]Recommendation:[/dim] "
        "Limit VLAN 1 to switch-local control/management only. "
        "Move access ports and trunks to explicit VLANs."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    results = collect_lldp(args.switch, args.username, args.password)
    inv = results["inventory"]

    format_inventory(inv)
    vlan1_risk_check(inv)
    format_lacp(inv, results["neighbors"])
    format_vlan_summary(inv)
    format_port_vlan_table(inv)

    lldp_table({n["local_port"]: n for n in results["neighbors"]})


if __name__ == "__main__":
    main()
