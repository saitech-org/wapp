import os
import click
import subprocess
import importlib.resources as pkg_resources

TEMPLATE_FILES = [
    'app.py',
    'app_env.py',
    'migrate_app.py',
    'create_app.py',
    'example.py',
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
            dest_path = os.path.join(os.getcwd(), filename)
            if os.path.exists(dest_path):
                click.echo(f'Skipping {filename}: already exists.')
                continue
            try:
                with pkg_resources.files('wapp.templates').joinpath(filename).open('r', encoding='utf-8') as src_file:
                    content = src_file.read()
                with open(dest_path, 'w', encoding='utf-8') as dest_file:
                    dest_file.write(content)
            except Exception as e:
                click.echo(f'Error copying {filename}: {e}')

        # Install necessary dependencies
        subprocess.run([os.sys.executable, "-m", "pip", "install"] + DEPENDENCIES, check=True)

        # Initialize Alembic
        subprocess.run([os.sys.executable, "-m", "alembic", "init", "migrations"], check=True)

        # Update migrations/env.py to set target_metadata
        migrations_env_path = os.path.join(os.getcwd(), 'migrations', 'env.py')
        with open(migrations_env_path, 'r', encoding='utf-8') as file:
            content = file.readlines()

        # Insert the line to load db from app_env
        for i, line in enumerate(content):
            if "target_metadata = None" in line:
                content[i] = "from app_env import db\n\ntarget_metadata = db.metadata\n"

        with open(migrations_env_path, 'w', encoding='utf-8') as file:
            file.writelines(content)

        click.echo('Wapp project initialized successfully in the current directory!')

    except Exception as e:
        click.echo(f'Error initializing project: {e}')


if __name__ == '__main__':
    wapp_init()