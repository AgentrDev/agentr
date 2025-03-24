import typer
from pathlib import Path

app = typer.Typer()

@app.command()
def version():
    """Show the version of the CLI"""
    print("agentr version 0.1.0")

@app.command()
def generate(schema_path: Path = typer.Option(..., "--schema", "-s")):
    """Generate API client from OpenAPI schema"""
    if not schema_path.exists():
        typer.echo(f"Error: Schema file {schema_path} does not exist", err=True)
        raise typer.Exit(1)
    from .utils.openapi import generate_api_client, load_schema

    try:
        schema = load_schema(schema_path)
    except Exception as e:
        typer.echo(f"Error loading schema: {e}", err=True)
        raise typer.Exit(1)
    code = generate_api_client(schema)
    print(code)

@app.command()
def run():
    """Run the MCP server"""
    from agentr.test import mcp
    mcp.run()

@app.command()
def install(app_name: str):
    """Install an app"""
    import json
    api_key = typer.prompt("Enter your API key", hide_input=True)
    if app_name == "claude":
        typer.echo(f"Installing mcp server for: {app_name}")
        config_path = '~/Library/Application Support/Claude/claude_desktop_config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)
        config['mcpServers']['agentr-r'] = {
            "command": "uvx",
            "args": ["agentr@latest", "run"],
            "env": {
                "AGENTR_API_KEY": api_key
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        typer.echo("App installed successfully")
    else:
        typer.echo(f"App {app_name} not supported")


if __name__ == "__main__":
    app()
