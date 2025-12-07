"""CLI entrypoint for collecting and displaying LLDP information."""

import argparse
from src.lldp_collector import collect_lldp
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

if __name__ == "__main__":
    main()
