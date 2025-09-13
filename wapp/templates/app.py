import subprocess
import sys

from app_env import ENV
from create_app import create_app

if __name__ == '__main__':
    if ENV == 'development':
        # prevent recursion by only running this from the main entrypoint
        subprocess.run([sys.executable, "-m", "migrate_app"], check=True)

    app = create_app(bind=True)
    app.run(debug=True)