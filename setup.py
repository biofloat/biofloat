from setuptools import setup, find_packages

setup(
    name = "biofloat",
    version = "0.4.0",
    packages = find_packages(),
    requires = ['Python (>=2.7)'],
    install_requires = [
        'beautifulsoup4>=4.4',
        'coverage>=4',
        'jupyter>=1.0.0',
        'matplotlib',
        'numpy>=1.10',
        'pandas>=0.17',
        'Pydap',
        'requests>=2.8',
        'seawater>=3.3',
        'simpletable>=0.2',
        'statsmodels>=0.6.1',
        'xray>=0.6'
    ],
    scripts = ['scripts/load_biofloat_cache.py',
               'scripts/woa_calibration.py'],

    # metadata for upload to PyPI
    author = "Mike McCann",
    author_email = "mccann@mbari.org",
    description = "Software for working with data from Bio-Argo floats",
    license = "MIT",
    keywords = "Oceanography Argo Bio-Argo drifting buoys floats",
    url = "https://github.com/biofloat/biofloat",
)
