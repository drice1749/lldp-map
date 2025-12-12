from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def section(title: str):
    console.print(Panel(f"[bold white]{title}[/bold white]", style="cyan", padding=(0, 2)))


def kv_table(title: str, data: dict):
    table = Table(
        title=f"[bold]{title}[/bold]",
        title_style="bold magenta",
        header_style="bold white",
        expand=False,
        box=box.SIMPLE_HEAVY,
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


def port_vlan_table(portmap: dict, interfaces: dict):
    table = Table(
        show_header=True,
        header_style="bold white",
        expand=True,              # FULL WIDTH for PORT MAP
        box=box.MINIMAL_DOUBLE_HEAD,
    )

    table.add_column("Port", style="cyan", no_wrap=True)
    table.add_column("Status", style="green", no_wrap=True)
    table.add_column("Speed", style="yellow", no_wrap=True)
    table.add_column("Description", style="magenta")
    table.add_column("MAC", style="white", no_wrap=True)
    table.add_column("Untagged VLAN", style="white", no_wrap=True)
    table.add_column("Tagged VLANs", style="bright_blue")

    for port, pdata in portmap.items():
        iface = interfaces.get(port, {})

        status = iface.get("status", "—")
        speed = iface.get("speed", "—")
        desc = iface.get("description", "—")

        # MAC logic (learned or first-seen)
        mac = iface.get("mac")
        if mac:
            mac = mac.lower()
        else:
            mac = "—"

        untag = pdata.get("untagged", "—")
        tagged_list = pdata.get("tagged", [])
        tagged = ", ".join(tagged_list) if tagged_list else "—"

        table.add_row(
            str(port),
            status,
            speed,
            desc,
            mac,
            str(untag),
            tagged,
        )

    console.print(table)


def lacp_table(lacp: dict):
    for trk, members in lacp.items():
        console.print(f"\n[bold yellow]{trk}[/bold yellow]")

        # LLDP missing warning
        if all(m.get("partner") == "unknown" for m in members):
            console.print(
                "  [bold red]⚠ No LLDP detected on LACP members — recommended to enable LLDP[/bold red]"
            )

        for m in members:
            status = m.get("status", "?")
            port = m.get("port_num")
            partner = m.get("partner")
            peer = m.get("port")

            status_icon = "🟢" if status.lower() == "up" else "🔴"

            console.print(
                f"  • Port [cyan]{port}[/cyan] {status_icon} {status} → partner: {partner}   peer-port: {peer}"
            )


def lldp_table(neighbors: dict):
    table = Table(
        title="[bold]LLDP NEIGHBORS[/bold]",
        title_style="bold cyan",
        show_header=True,
        header_style="bold white",
        expand=False,   # COMPACT
        box=box.SIMPLE_HEAVY,
    )

    table.add_column("Local Port", style="cyan", no_wrap=True)
    table.add_column("Remote Name", style="white")
    table.add_column("MAC", style="magenta", no_wrap=True)
    table.add_column("Remote Port", style="yellow", no_wrap=True)
    table.add_column("Mgmt IP", style="green", no_wrap=True)

    for port, entry in neighbors.items():
        table.add_row(
            str(port),
            entry.get("system_name", "—"),
            entry.get("chassis_id", "—"),
            entry.get("port_descr", "—"),
            entry.get("mgmt_ip", "—"),
        )

    console.print(table)
