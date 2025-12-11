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

    system_fields = {
        "Serial": inv.get("serial"),
        "Base MAC": inv.get("base_mac"),
        "Software": inv.get("software"),
        "Boot ROM": inv.get("bootrom"),
        "Uptime": inv.get("uptime"),
        "CPU Load": inv.get("cpu"),
    }
    kv_table("System", system_fields)

    memory_fields = {
        "Total": inv.get("memory_total_hr"),
        "Free": inv.get("memory_free_hr"),
    }
    kv_table("Memory", memory_fields)

    hardware_fields = {
        "Model": inv.get("model"),
        "SKU": inv.get("sku"),
    }
    kv_table("Hardware", hardware_fields)

    power_fields = {
        "PoE Total": inv.get("poe_total"),
        "Used": inv.get("poe_used"),
        "Remaining": inv.get("poe_remaining"),
    }
    kv_table("Power", power_fields)


def format_vlan_summary(inv):
    if "vlans_detail" not in inv:
        return

    section("VLAN SUMMARY")

    for vlan_id, vlan in sorted(inv["vlans_detail"].items(), key=lambda x: int(x[0])):
        vlan_format = {
            "id": vlan_id,
            "name": vlan.get("name") or "",
            "ip": vlan.get("ip") or "—",
            "role": "L3" if vlan.get("l3") else "L2 only",
            "untagged": ", ".join(vlan.get("untagged", [])) or "—",
            "tagged": ", ".join(vlan.get("tagged", [])) or "—",
        }
        vlan_block(vlan_format)


def format_port_vlan_table(inv):
    if "port_vlans" not in inv:
        return

    section("PORT VLAN MAP")
    port_vlan_table(inv["port_vlans"])


def format_lacp(inv, neighbors):
    lacp_entries = inv.get("lacp", [])
    trunks = inv.get("trunks", [])

    lacp_struct = {}

    for t in trunks:
        grp = t.get("group")
        if not grp:
            continue

        lacp_struct.setdefault(grp, [])

        entry = next((l for l in lacp_entries if l.get("port") == t["port"]), {})
        status = entry.get("status", "?")

        partner = "unknown"
        partner_port = "unknown"

        for n in neighbors:
            if n.get("local_port") == t["port"]:
                sysname = n.get("system_name", "?")
                chassis = n.get("chassis_id", "?")
                partner = f"{sysname} ({chassis})"
                partner_port = n.get("port_descr") or n.get("port_id") or "unknown"
                break

        lacp_struct[grp].append({
            "port_num": t["port"],
            "status": status,
            "partner": partner,
            "port": partner_port,
        })

    section("LACP STATUS")
    lacp_table(lacp_struct)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    results = collect_lldp(args.switch, args.username, args.password)
    inv = results["inventory"]

    format_inventory(inv)
    format_lacp(inv, results["neighbors"])
    format_vlan_summary(inv)
    format_port_vlan_table(inv)

    lldp_table({n["local_port"]: n for n in results["neighbors"]})


if __name__ == "__main__":
    main()
