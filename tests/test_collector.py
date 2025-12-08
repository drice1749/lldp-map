import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.lldp_collector import detect_vendor, human_bytes
from src.utils import print_inventory, print_table


def test_human_bytes_converts_numbers():
    assert human_bytes("1,500,000") == "1.5 MB"
    assert human_bytes("2,500,000,000") == "2.50 GB"
    assert human_bytes("1234") == "1234"


def test_detect_vendor_matches_known_strings():
    assert detect_vendor("ArubaOS Switch") == "arubaos-switch"
    assert detect_vendor("Cisco IOS XE") == "cisco_ios"
    assert detect_vendor("Fortinet") == "fortinet"


def test_print_helpers_emit_expected_sections(capsys):
    inventory = {
        "serial": "ABC",
        "memory_total_hr": "1.5 MB",
        "model": "CX123",
        "poe_total": "10 W",
        "power_supplies": [{"psu": "1", "watts": "250", "status": "ok"}],
    }
    neighbors = [
        {"local_port": "1", "system_name": "core", "chassis_id": "00:11", "mgmt_ip": "10.0.0.1"}
    ]

    print_inventory(inventory)
    print_table(neighbors)

    out = capsys.readouterr().out
    assert "INVENTORY" in out
    assert "LLDP Neighbors" in out
