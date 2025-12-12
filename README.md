LLDP Mapper  
Internal Network Discovery Tool (Proscan / Authorized Use Only)

NOTICE:
This tool is for internal use only.
External contributions, pull requests, forks, or redistribution are NOT permitted at this time.

------------------------------------------------------------
📌 Overview
------------------------------------------------------------

LLDP Mapper is a lightweight, multi-vendor network discovery tool used internally to gather:

- LLDP neighbors
- VLAN configuration (tagged/untagged)
- LACP trunk information
- Inventory details (software, hardware, PoE, uptime, memory)

The tool runs against a single switch at a time and produces clean, readable output formatted with the Rich library.

Supported platforms include:
- ArubaOS-Switch / ProCurve
- ArubaOS-CX
- Cisco IOS
- Fortinet

------------------------------------------------------------
✨ Features
------------------------------------------------------------

🔍 Automatic Vendor Detection
The tool examines banner + version output to select the correct Netmiko device handler.

🖧 LLDP Neighbor Discovery
Parses detailed LLDP information:
- Remote device hostname
- MAC / chassis ID
- Remote port
- Management IP
- Port sorting (A1, B1, 1/1/1, Gi1/0/1, etc.)

📚 VLAN Parsing
Pulls VLAN information from running configuration:
- VLAN names
- SVI IP addresses (converted to CIDR)
- Tagged/untagged ports
- Port-to-VLAN table generation

🔁 LACP + Trunk Mapping
Correlates show trunks and show lacp output with LLDP neighbors to identify:
- Trunk groups
- Member ports
- Remote partner devices
- Remote partner ports

🧩 Inventory Collection
Collects system and hardware details:
- Serial number
- Base MAC
- Software version / Boot ROM
- Uptime
- CPU load
- Memory usage (converted to human-readable form)
- Chassis model + SKU
- PoE usage / remaining power

🎨 Rich-Formatted CLI Output
All results are presented in clean sections:
- INVENTORY
- LACP STATUS
- VLAN SUMMARY
- PORT VLAN MAP
- LLDP NEIGHBORS

------------------------------------------------------------
📁 Project Structure
------------------------------------------------------------

src/
  main.py               # CLI entry point
  lldp_collector.py     # SSH + vendor detection + data collection
  utils.py              # Formatting (Rich tables, headers, blocks)

------------------------------------------------------------
🚀 Installation
------------------------------------------------------------

1. Install dependencies:
   pip install netmiko rich

2. Ensure project structure is preserved:
   project/
     src/
       main.py
       lldp_collector.py
       utils.py

------------------------------------------------------------
▶️ Usage Example
------------------------------------------------------------

Run the mapper against a switch:

python3 -m src.main --switch 10.0.0.5 --username admin --password MyPassword123

------------------------------------------------------------
📡 Supported Vendors
------------------------------------------------------------

Platform        | How It’s Detected           | Netmiko Driver Used
--------------- | --------------------------- | --------------------
ArubaOS-Switch  | "arubaos", "procurve"       | hp_procurve
Aruba CX        | "aruba" + "cx"              | aruba_aoscx
Cisco IOS       | "cisco"                     | cisco_ios
Fortinet        | "fortigate", "fortinet"     | fortinet

------------------------------------------------------------
🧠 Internal Notes
------------------------------------------------------------

- This is considered the baseline version for internal deployments.
- Use only with explicit authorization.
- Do NOT expose this tool, its output, or its repository externally.
- PR requests, issues, public discussion, or contributions are not permitted.

------------------------------------------------------------
🔒 Security Warning
------------------------------------------------------------

This tool handles SSH credentials. Always:
- Use unique per-device local accounts
- Rotate credentials periodically
- Avoid storing plain passwords in scripts
- If possible, use an encrypted secrets vault

------------------------------------------------------------
🛠 Roadmap (Internal Only)
------------------------------------------------------------

Potential future enhancements:
- JSON or CSV export
- Draw.io topology generation
- Multi-device scanning mode
- Credential rotation
- Full multi-vendor plugin architecture
- n8n integration for automated documentation workflows

------------------------------------------------------------
📄 License
------------------------------------------------------------

No license. This code is not open-source and not licensed for external distribution.
Usage is restricted to authorized internal personnel only.
