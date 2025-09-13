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
@click.argument('project_name')
def wapp_init(project_name):
    """Bootstrap a new Wapp project."""
    try:
        # Create project directory
        os.makedirs(project_name)

        # Create project files from templates
        for filename in TEMPLATE_FILES:
            try:
                with pkg_resources.files('wapp.templates').joinpath(filename).open('r', encoding='utf-8') as src_file:
                    content = src_file.read()
                with open(os.path.join(project_name, filename), 'w', encoding='utf-8') as dest_file:
                    dest_file.write(content)
            except Exception as e:
                click.echo(f'Error copying {filename}: {e}')

        # Install necessary dependencies
        subprocess.run([sys.executable, "-m", "pip", "install"] + DEPENDENCIES, check=True)

        # Change into the project directory
        os.chdir(project_name)

        # Initialize Alembic
        subprocess.run([sys.executable, "-m", "alembic", "init", "migrations"], check=True)

        click.echo(f'Project {project_name} initialized successfully!')

    except Exception as e:
        click.echo(f'Error initializing project: {e}')


if __name__ == '__main__':
    wapp_init()