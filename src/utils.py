from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def print_table(results):
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


def section(title: str):
    console.print(Panel(f"[bold white]{title}[/bold white]", style="cyan", padding=(0, 2)))


def kv_table(title: str, data: dict):
    table = Table(
        title=f"[bold]{title}[/bold]",
        title_style="bold magenta",
        header_style="bold white",
        box=box.SIMPLE_HEAVY
    )
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    for key, value in data.items():
        table.add_row(key, str(value))

    console.print(table)


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


def port_vlan_table(portmap: dict):
    table = Table(
        show_header=True,
        header_style="bold white",
        box=box.MINIMAL_DOUBLE_HEAD
    )
    table.add_column("Port", style="cyan", justify="center")
    table.add_column("Untagged VLAN", style="green", justify="center")
    table.add_column("Tagged VLANs", style="bright_blue", justify="left")

    for port in sorted(portmap, key=lambda x: int(x)):
        pdata = portmap[port]
        untag = pdata.get("untagged", "—") or "—"
        tagged_list = pdata.get("tagged", [])
        tagged = ", ".join(map(str, tagged_list)) if tagged_list else "—"
        table.add_row(str(port), str(untag), tagged)

    console.print(table)


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

        if all(m.get("partner") in (None, "unknown") for m in members):
            console.print("    [bold red]⚠ LLDP missing on active LACP member — recommended to enable LLDP[/bold red]")


# -----------------------------------------------------------
#  UPDATED 5-COLUMN LLDP TABLE
# -----------------------------------------------------------

def lldp_table(neighbors: dict):
    table = Table(
        title="[bold]LLDP NEIGHBORS[/bold]",
        title_style="bold cyan",
        show_header=True,
        header_style="bold white",
        box=box.SIMPLE_HEAVY
    )

    table.add_column("Local Port", style="cyan", no_wrap=True)
    table.add_column("Remote Name", style="white")
    table.add_column("MAC", style="white")
    table.add_column("Remote Port", style="bright_blue")
    table.add_column("Mgmt IP", style="green")

    for port in sorted(neighbors, key=lambda x: int(x)):
        n = neighbors[port]

        name = n.get("system_name", "unknown")
        mac = n.get("mac") or n.get("chassis_id") or "—"
        remote_port = n.get("remote_port") or "—"
        mgmt = n.get("mgmt_ip") or "—"

        table.add_row(str(port), name, mac, remote_port, mgmt)

    console.print(table)
