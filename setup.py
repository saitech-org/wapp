from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="wapp",
    version="0.1.0",
    description="A modular Flask API framework with auto CRUD and migrations",
    author="saitech",
    url="https://github.com/saitech-org/wapp",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    install_requires=[
        'alembic',
        'python-dotenv',
        'flask',
        'sqlalchemy'
    ],
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'wapp-migrate = wapp.migrate:main',
        ],
    },
)
