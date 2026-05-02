import json
from rich.console import Console
from rich.table import Table

console = Console()

def main():
    try:
        with open('dane.json', 'r') as f:
            data = json.load(f)
        
        table = Table(title="DataOps Toolbox Status")
        table.add_column("Tool", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Status", style="green")

        for item in data:
            table.add_row(item['tool'], item['category'], item['status'])

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")

if __name__ == "__main__":
    main()
