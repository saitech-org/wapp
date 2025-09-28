# Top-level CLI menu: discover commands under wapp.cli_commands
import pkgutil
from importlib import import_module
import click

cli = click.Group(help="Wapp helper CLI")


def _load_commands():
    try:
        import wapp.cli_commands as commands_pkg
    except Exception:
        return
    for _finder, name, _ispkg in pkgutil.iter_modules(commands_pkg.__path__):
        if name.startswith("_"):
            continue
        mod = import_module(f"wapp.cli_commands.{name}")
        cmd = getattr(mod, "command", None) or getattr(mod, "cli_command", None) or getattr(mod, "cmd", None)
        if isinstance(cmd, click.Command):
            cli.add_command(cmd)


_load_commands()


if __name__ == "__main__":
    cli()
