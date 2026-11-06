from setuptools import setup, find_packages

setup(
    name="toolhub",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "toolhub=app.cli:app",
        ],
    },
)

