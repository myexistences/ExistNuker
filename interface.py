"""
Modern CLI Interface using 'rich' library
Handles all user interaction, menus, and progress display
"""

import sys
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.prompt import Prompt, IntPrompt, Confirm
from rich import box

from config import get_base_path, get_resource_path, stop_event

# Initialize console
console = Console()

class Interface:
    def __init__(self):
        self.console = console
        self.title = "ExistNuker"
        self.version = "https://github.com/myexistences/ExistNuker"
        
    def clear(self):
        """Clear the screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def print_banner(self):
        """Print the main application banner"""
        self.clear()
        
        banner_text = r"""
    ______      _      __  _   __      __             
   / ____/  __ (_)____/ /_/ | / /_  __/ /_____  _____ 
  / __/ | |/_// / ___/ __/  |/ / / / / //_/ _ \/ ___/ 
 / /____>  < / (__  ) /_/ /|  / /_/ / ,< /  __/ /     
/_____/_/|_|/_/____/\__/_/ |_/\__,_/_/|_|\___/_/      
        """
        
        grid = Table.grid(expand=True)
        grid.add_column(justify="center")
        
        # Ensure banner doesn't wrap and break the art
        banner = Text(banner_text, style="bold cyan", no_wrap=True, overflow="crop")
        grid.add_row(banner)
        
        grid.add_row(Text(f"{self.title}", style="bold white"))
        grid.add_row(Text(f"{self.version}", style="dim white"))
        
        self.console.print(Panel(grid, style="cyan", border_style="cyan", expand=True))

    def print_error(self, message):
        """Print error message"""
        self.console.print(f"[bold red]Error:[/bold red] {message}")
        
    def print_success(self, message):
        """Print success message"""
        self.console.print(f"[bold green]Success:[/bold green] {message}")
        
    def print_warning(self, message):
        """Print warning message"""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def print_info(self, message):
        """Print info message"""
        self.console.print(f"[bold cyan]Info:[/bold cyan] {message}")

    def get_token(self):
        """Prompt for token"""
        self.console.print("[bold yellow]Enter Discord Bot Token:[/bold yellow]")
        return Prompt.ask("", password=True)

    def select_server(self, guilds):
        """Display server selection menu"""
        self.print_banner()
        
        if not guilds:
            self.console.print("[bold red]No servers found![/bold red]")
            return None

        # Use expand=True to fill width, box=ROUNDED for style
        table = Table(
            title="Select a Server", 
            show_header=True, 
            header_style="bold magenta",
            expand=True,
            box=box.ROUNDED,
            border_style="cyan"
        )
        table.add_column("No.", style="cyan", width=4, justify="center")
        table.add_column("Server Name", style="white", ratio=2)
        table.add_column("ID", style="dim", ratio=1)
        
        for i, guild in enumerate(guilds, 1):
            table.add_row(str(i), str(guild.get('name', 'Unknown')), str(guild.get('id', 'Unknown')))
            
        self.console.print(table)
        self.console.print("\n[bold]T[/bold] - Change Token")
        self.console.print("[bold]Q[/bold] - Quit")
        
        while True:
            choice = Prompt.ask("[bold yellow]Choice[/bold yellow]").upper()
            if choice == 'T':
                return 'CHANGE_TOKEN'
            if choice == 'Q':
                sys.exit(0)
                
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(guilds):
                    return guilds[idx]
            except ValueError:
                pass
            
            self.print_error("Invalid selection")

    def server_menu(self, guild_info):
        """Display server action menu"""
        self.print_banner()
        
        # Server Info Panel
        info_grid = Table.grid(expand=True)
        info_grid.add_column(style="cyan", ratio=1)
        info_grid.add_column(style="white", ratio=3)
        
        info_grid.add_row("Server:", guild_info.get('name', 'Unknown'))
        info_grid.add_row("ID:", str(guild_info.get('id', 'Unknown')))
        
        # Counts if available
        if 'approximate_member_count' in guild_info:
            info_grid.add_row("Members:", str(guild_info.get('approximate_member_count', 0)))
            
        self.console.print(Panel(
            info_grid, 
            title="Target Server", 
            border_style="green",
            expand=True,
            box=box.ROUNDED
        ))
        
        # Menu Options
        menu_table = Table(show_header=False, box=None, expand=True)
        menu_table.add_column("Option", style="bold cyan", width=4, justify="center")
        menu_table.add_column("Description", style="white")
        
        options = [
            ("1", "Webhook Spam (All Channels)"),
            ("2", "Create Channels"),
            ("3", "Delete Channels"),
            ("4", "Create Roles"),
            ("5", "Delete Roles"),
            ("6", "Ban Members"),
            ("7", "Prune Inactive Members"),
            ("0", "Back (Select Different Server)")
        ]
        
        for opt, desc in options:
            menu_table.add_row(opt, desc)
            
        self.console.print(Panel(
            menu_table, 
            title="Actions", 
            border_style="magenta",
            expand=True,
            box=box.ROUNDED
        ))
        
        self.console.print("[dim]Press Ctrl+C to stop ongoing operations[/dim]")
        
        return Prompt.ask("[bold yellow]Select Action[/bold yellow]")

    def progress_bar(self, description="Processing..."):
        """Return a configured progress bar instance"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            transient=True,
            expand=True
        )

    def status_spinner(self, message):
        """Return a status spinner context manager"""
        return self.console.status(message, spinner="dots")

    def confirm_action(self, message):
        """Ask for confirmation"""
        return Confirm.ask(f"[bold red]{message}[/bold red]", default=False)

    def print_logs(self, message, style="dim"):
        """Print log message (for verbose output)"""
        self.console.print(message, style=style)

# Global interface instance
ui = Interface()
