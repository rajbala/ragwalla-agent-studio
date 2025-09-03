#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "boto3",
#     "urllib3",
#     "rich",
# ]
# ///

import click
import boto3
from rich.console import Console
from rich.table import Table
import urllib3

console = Console()

@click.command()
@click.option('--name', default='World', help='Name to greet')
@click.option('--count', default=1, help='Number of greetings')
def hello(name, count):
    """Simple program that greets NAME COUNT times."""
    for _ in range(count):
        console.print(f"[bold green]Hello {name}![/bold green]")
    
    # Display a sample table
    table = Table(title="Sample Dependencies")
    table.add_column("Package", style="cyan")
    table.add_column("Description", style="magenta")
    
    table.add_row("click", "Command line interface creation kit")
    table.add_row("boto3", "AWS SDK for Python")
    table.add_row("urllib3", "HTTP client for Python")
    table.add_row("rich", "Rich text and beautiful formatting")
    
    console.print(table)
    
    # Show versions
    console.print("\n[yellow]Package versions:[/yellow]")
    console.print(f"urllib3: {urllib3.__version__}")
    console.print(f"boto3: {boto3.__version__}")

if __name__ == '__main__':
    hello()