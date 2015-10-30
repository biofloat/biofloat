oxyfloat
--------

[![Build Status](https://travis-ci.org/MBARIMike/oxyfloat.svg?branch=master)](https://travis-ci.org/MBARIMike/oxyfloat)
[![Coverage Status](https://coveralls.io/repos/MBARIMike/oxyfloat/badge.svg?branch=master&service=github)](https://coveralls.io/github/MBARIMike/oxyfloat?branch=master)
[![Code Health](https://landscape.io/github/MBARIMike/oxyfloat/master/landscape.svg?style=flat)](https://landscape.io/github/MBARIMike/oxyfloat/master)

oxyfloat is a Python module designed to enable oceanographers to perform
quality control operations on oxygen data from [Argo ocean drifting profiling floats](https://en.wikipedia.org/wiki/Argo_(oceanography)).

#### Installation

##### Bare-bones Unix

    sudo yum -y install hdf scipy blas blas-devel lapack lapack-devel
    pip install oxyfloat

##### Anaconda or Canopy

    pip install pydap
    pip install oxyfloat

For plotting data on a map [basemap needs to be installed](http://matplotlib.org/basemap/users/installing.html).

#### Usage

See example [Jupyter Notebooks](notebooks) and [scripts](scripts) that demonstrate specific analyses and 
visualizations.

