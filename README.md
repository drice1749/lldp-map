# LLDP Mapper (Starter Template)

This project collects LLDP neighbor information from switches using SSH
and prints a simple neighbor list.

## Setup
1. Use Python 3.9+.
2. (Optional) Create and activate a virtual environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the collector
Run the CLI from the repository root with your switch credentials:
```bash
python3 src/main.py --switch 10.0.0.1 --username admin --password secret
```
This connects to the switch, fetches LLDP neighbors, and prints device inventory
followed by a neighbor table.

## Testing
Execute the test suite to verify the helpers and collectors:
```bash
pytest
```
Or use the helper script, which installs dependencies and runs pytest (activates `.venv` if present):
```bash
./scripts/run_tests.sh
```

## Features
- LLDP pull via SSH
- Modular collector
- Clean architecture (src/, tests/)
- Easy to extend
