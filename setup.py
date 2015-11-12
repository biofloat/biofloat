from setuptools import setup, find_packages
setup(
    name = "biofloat",
    version = "0.1.1",
    packages = find_packages(),
    scripts = ['scripts/load_biofloat_cache.py'],

    # metadata for upload to PyPI
    author = "Mike McCann",
    author_email = "mccann@mbari.org",
    description = "Software for working with data from Bio-Argo floats",
    license = "MIT",
    keywords = "Oceanography Argo Bio-Argo drifting buoys floats",
    url = "https://github.com/biofloat/biofloat",
)
