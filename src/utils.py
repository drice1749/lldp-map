def print_table(results):
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
