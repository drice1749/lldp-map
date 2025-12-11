# utils.py
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


# ============================================================
#  LEGACY FUNCTION (kept for compatibility)
# ============================================================

def print_table(results):
    """
    Old LLDP table printing. Still works for backward compatibility.
    """
    console.print("\n[bold cyan]=== LLDP Neighbors ===[/bold cyan]")
    for r in results:
        local = r.get("local_port", "?")
        sysname = r.get("system_name", "?")
        chassis = r.get("chassis_id", "?")
        mgmt = r.get("mgmt_ip", "")

        if mgmt:
            console.print(f"[cyan]{local}[/cyan] → {sysname} ({chassis})  [green]mgmt:{mgmt}[/green]")
        else:
            console.print(f"[cyan]{local}[/cyan] → {sysname} ({chassis})")


# ============================================================
#  SECTION HEADERS
# ============================================================

def section(title: str):
    """
    Styled section header.
    """
    console.print(Panel(f"[bold white]{title}[/bold white]", style="cyan", padding=(0, 2)))


# ============================================================
#  GENERIC KEY/VALUE TABLE
# ============================================================

def kv_table(title: str, data: dict):
    """
    Pretty two-column key/value table.
    """
    table = Table(
        title=f"[bold]{title}[/bold]",
        title_style="bold magenta",
        header_style="bold white",
        box=box.SIMPLE_HEAVY,
        expand=False
    )
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    for key, value in data.items():
        table.add_row(key, str(value))

    console.print(table)


# ============================================================
#  VLAN BLOCK OUTPUT
# ============================================================

def vlan_block(vlan: dict):
    """
    Pretty output of a single VLAN block.
    """
    vid = vlan.get("id")
    name = vlan.get("name", "")
    ip = vlan.get("ip", "—")
    role = vlan.get("role", "L2")

    untagged = vlan.get("untagged") or "—"
    tagged = vlan.get("tagged") or "—"

    console.print(f"\n[bold yellow]VLAN {vid}[/bold yellow] — {name}")
    console.print(f"[cyan]IP/Subnet:[/cyan] {ip}")
    console.print(f"[cyan]Role:[/cyan] {role}")
    console.print(f"[green]Untagged:[/green] {untagged}")
    console.print(f"[bright_blue]Tagged:[/bright_blue] {tagged}")


# ============================================================
#  PORT → VLAN TABLE
# ============================================================

def port_vlan_table(portmap: dict):
    """
    Pretty port-to-VLAN mapping table.
    """
    table = Table(
        show_header=True,
        header_style="bold white",
        box=box.MINIMAL_DOUBLE_HEAD
    )
    table.add_column("Port", style="cyan", justify="center")
    table.add_column("Untagged VLAN", style="green", justify="center")
    table.add_column("Tagged VLANs", style="bright_blue", justify="left")

    # Keep numeric/letter/CX sorting responsibility in caller.
    for port, pdata in portmap.items():
        untag = pdata.get("untagged", "—") or "—"
        tagged_list = pdata.get("tagged", [])
        tagged = ", ".join(map(str, tagged_list)) if tagged_list else "—"

        table.add_row(str(port), str(untag), tagged)

    console.print(table)


# ============================================================
#  LACP TABLE
# ============================================================

def lacp_table(lacp: dict):
    """
    Pretty LACP output.
    """
    for trk, members in lacp.items():
        console.print(f"\n[bold yellow]{trk}[/bold yellow]")

        for m in members:
            port = m.get("port_num")
            status = m.get("status", "unknown")
            partner = m.get("partner", "unknown")
            peer_port = m.get("port", "unknown")

            status_icon = "🟢" if status.lower() == "up" else "🔴"

            console.print(
                f"  • Port [cyan]{port}[/cyan] {status_icon} {status} "
                f"→ partner: {partner}   peer-port: {peer_port}"
            )

        # LLDP missing hint
        if all(m.get("partner") in (None, "unknown") for m in members):
            console.print("    [bold red]⚠ LLDP missing on active LACP member — recommended to enable LLDP[/bold red]")


# ============================================================
#  LLDP TABLE — 5 COLUMNS (LOCAL / REMOTE / MAC / REMOTE PORT / MGMT IP)
# ============================================================

def lldp_table(neighbors: dict):
    """
    Pretty LLDP neighbor output.
    Columns:
    - Local Port
    - Remote Name
    - MAC
    - Remote Port
    - Mgmt IP
    """
    table = Table(
        title="[bold]LLDP NEIGHBORS[/bold]",
        title_style="bold cyan",
        show_header=True,
        header_style="bold white",
        expand=False,
        box=box.SIMPLE_HEAVY
    )

    table.add_column("Local Port", style="cyan", no_wrap=True)
    table.add_column("Remote Name", style="white")
    table.add_column("MAC", style="magenta", no_wrap=True)
    table.add_column("Remote Port", style="yellow", no_wrap=True)
    table.add_column("Mgmt IP", style="green", no_wrap=True)

    for port, n in neighbors.items():
        remote_name = n.get("system_name", "—")
        mac = n.get("chassis_id", "—")
        rport = n.get("port_descr", "—")
        mgmt = n.get("mgmt_ip", "—")

        table.add_row(str(port), remote_name, mac, rport, mgmt)

    console.print(table)
