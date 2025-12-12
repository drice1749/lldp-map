from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


# ============================================================
# SECTION HEADERS
# ============================================================

def section(title: str):
    console.print(Panel(f"[bold white]{title}[/bold white]", style="cyan", padding=(0, 2)))


# ============================================================
# GENERIC KEY/VALUE TABLE
# ============================================================

def kv_table(title: str, data: dict):
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
# VLAN BLOCK OUTPUT
# ============================================================

def vlan_block(vlan: dict):
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
# PORT → VLAN + INTERFACE TABLE
# ============================================================

def port_vlan_table(portmap: dict, interfaces: dict):
    table = Table(
        show_header=True,
        header_style="bold white",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=True
    )

    table.add_column("Port", style="cyan", no_wrap=True)
    table.add_column("Status", style="green", no_wrap=True)
    table.add_column("Speed", style="yellow", no_wrap=True)
    table.add_column("Description", style="magenta")
    table.add_column("Untagged VLAN", style="white", no_wrap=True)
    table.add_column("Tagged VLANs", style="bright_blue")

    for port, pdata in portmap.items():
        iface = interfaces.get(port, {})
        status = iface.get("status", "—")
        speed = iface.get("speed", "—")
        desc = iface.get("description", "—")

        untag = pdata.get("untagged", "—")
        tagged_list = pdata.get("tagged", [])
        tagged = ", ".join(tagged_list) if tagged_list else "—"

        table.add_row(
            str(port),
            status,
            speed,
            desc,
            str(untag),
            tagged
        )

    console.print(table)


# ============================================================
# LACP TABLE
# ============================================================

def lacp_table(lacp: dict):
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


# ============================================================
# LLDP TABLE
# ============================================================

def lldp_table(neighbors: dict):
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
        table.add_row(
            str(port),
            n.get("system_name", "—"),
            n.get("chassis_id", "—"),
            n.get("port_descr", "—"),
            n.get("mgmt_ip", "—"),
        )

    console.print(table)
