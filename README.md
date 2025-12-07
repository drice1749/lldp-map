# LLDP Mapper (Starter Template)

This project collects LLDP neighbor information from switches using SSH
and prints a simple neighbor list.

## Usage

```bash
python3 src/main.py --switch 10.0.0.1 --username admin
```

## Features
- LLDP pull via SSH
- Modular collector
- Clean architecture (src/, tests/)
- Easy to extend
