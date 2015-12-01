#!/bin/bash
coverage run --source=biofloat scripts/load_biofloat_cache.py --age 3000 --profiles 1
coverage run -a --source=biofloat tests/unit_tests.py
coverage run -a --source=biofloat scripts/woa_calibration.py --cache_file \
    ~/biofloat_fixed_cache_age3000_profiles1_variablesDOXY_ADJUSTED-PSAL_ADJUSTED-TEMP_ADJUSTED.hdf \
    --results_file woa.hdf -v --print_woa_lookups
coverage report -m

