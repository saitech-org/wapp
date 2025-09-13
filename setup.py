from setuptools import setup, find_packages

setup(
    name='wapp',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'alembic',
        'python-dotenv',
        'flask',
        'sqlalchemy',
    ],
    entry_points={
        'console_scripts': [
            'wapp-migrate = wapp.migrate:main',
        ],
    },
)

