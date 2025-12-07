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

    # print inventory
    print("\n=== INVENTORY ===")
    for k, v in results["inventory"].items():
        print(f"{k}: {v}")

    # print neighbors
    print_table(results["neighbors"])

if __name__ == "__main__":
    main()
