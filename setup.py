from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in zarnik/__init__.py
from zarnik import __version__ as version

setup(
	name="zarnik",
	version=version,
	description="ERPNext customizations for Zarnik Hotel Supplies Private Limited",
	author="Zarnik Hotel Supplies Private Limited",
	author_email="azhar@zarnik.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
