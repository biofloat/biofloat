import os
from os.path import join as pjoin, splitext, split as psplit
from distutils.command.install_scripts import install_scripts
from distutils import log
from setuptools import setup, find_packages

# See: https://matthew-brett.github.io/pydagogue/installing_scripts.html
BAT_TEMPLATE = \
r"""@echo off
REM wrapper to use shebang first line of {FNAME}
set mypath=%~dp0
set pyscript="%mypath%{FNAME}"
set /p line1=<%pyscript%
if "%line1:~0,2%" == "#!" (goto :goodstart)
echo First line of %pyscript% does not start with "#!"
exit /b 1
:goodstart
set py_exe=%line1:~2%
call "%py_exe%" %pyscript% %*
"""


class my_install_scripts(install_scripts):
    def run(self):
        install_scripts.run(self)
        if not os.name == "nt":
            return
        for filepath in self.get_outputs():
            # If we can find an executable name in the #! top line of the script
            # file, make .bat wrapper for script.
            with open(filepath, 'rt') as fobj:
                first_line = fobj.readline()
            if not (first_line.startswith('#!') and
                    'python' in first_line.lower()):
                log.info("No #!python executable found, skipping .bat "
                            "wrapper")
                continue
            pth, fname = psplit(filepath)
            froot, ext = splitext(fname)
            bat_file = pjoin(pth, froot + '.bat')
            bat_contents = BAT_TEMPLATE.replace('{FNAME}', fname)
            log.info("Making %s wrapper for %s" % (bat_file, filepath))
            if self.dry_run:
                continue
            with open(bat_file, 'wt') as fobj:
                fobj.write(bat_contents)


setup(
    name = "biofloat",
    version = "0.4.5",
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
    cmdclass = {'install_scripts': my_install_scripts},

    # metadata for upload to PyPI
    author = "Mike McCann",
    author_email = "mccann@mbari.org",
    description = "Software for working with data from Bio-Argo floats",
    license = "MIT",
    keywords = "Oceanography Argo Bio-Argo drifting buoys floats",
    url = "https://github.com/biofloat/biofloat",
)
