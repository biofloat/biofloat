Jupyter Notebooks for biofloat 
------------------------------

To execute the code in these Notebooks follow [these instructions to install biofloat](../README.md).
The biofloat package must be in your Python search path.  If you installed with `pip install biofloat`
it will be in your path and you are all set and will be able to execute these Notebooks.  

If you wish to use the biofloat software in a clone of the repository you should set your 
PYTHONPATH environment variable to that directory.

######  For example, on Unix:

    export PYTHONPATH=~/dev/biofloatgit

######  For example, on Windows:

    set PYTHONPATH=%HOMEDRIVE%%HOMEPATH%\Documents\GitHub\biofloat;

##### Change to this directory on your computer and execute this at the Anaconda, Canopy, or Unix prompt:

    ipython notebook

A browser window should open with a directory listing of the notebooks for you to select. 

Here is a brief description of the Notebooks that were created during the development 
of the biofloat module:

#####  First Notebooks, used to test local cache file operation and Pandas capabilities
1. [build_biofloat_cache.ipynb](build_biofloat_cache.ipynb)
2. [explore_cached_biofloat_data.ipynb](explore_cached_biofloat_data.ipynb)
3. [explore_surface_oxygen_and_WOA.ipynb](explore_surface_oxygen_and_WOA.ipynb)

##### Notebooks exploring calibrations against the World Ocean Atlas 
1. [compare_oxygen_calibrations.ipynb](compare_oxygen_calibrations.ipynb)
2. [oxygen_calibration_5903264_DOXY.ipynb](oxygen_calibration_5903264_DOXY.ipynb)
3. [calibrate_all_oxygen_floats.ipynb](calibrate_all_oxygen_floats.ipynb)
4. [save_to_odv.ipynb](save_to_odv.ipynb)
