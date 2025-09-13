import os
import sys

import click
import subprocess
import importlib.resources as pkg_resources

TEMPLATE_FILES = [
    'app.py',
    'app_env.py',
    'migrate_app.py',
    'create_app.py',
]

DEPENDENCIES = [
    'saitech-wapp',
    'flask',
    'flask_sqlalchemy',
    'alembic',
    'flasgger',
    'python-dotenv',
    'pydantic',
]


@click.command()
def wapp_init():
    """Bootstrap a new Wapp project in the current directory."""
    try:
        # Create project files from templates
        for filename in TEMPLATE_FILES:
            try:
                with open(pkg_resources.files('wapp.templates').joinpath(filename),'r', encoding='utf-8') as src_file:
                    content = src_file.read()
                with open(os.path.join(os.getcwd(), filename), 'w', encoding='utf-8') as dest_file:
                    dest_file.write(content)
            except Exception as e:
                click.echo(f'Error copying {filename}: {e}')

        # Install necessary dependencies
        subprocess.run([sys.executable, "-m", "pip", "install"] + DEPENDENCIES, check=True)

        # Initialize Alembic
        subprocess.run([sys.executable, "-m", "alembic", "init", "migrations"], check=True)

        click.echo('Wapp project initialized successfully in the current directory!')

    except Exception as e:
        click.echo(f'Error initializing project: {e}')


if __name__ == '__main__':
    wapp_init()