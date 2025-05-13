from setuptools import setup, find_packages

setup(
    name="huntbot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "discord.py",
        "pandas",
        "google-api-python-client",
        "pytz"
    ],
) 