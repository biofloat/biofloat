#!/bin/bash
coverage run --source=biofloat scripts/load_biofloat_cache.py --age 3000 --profiles 1
coverage run -a --source=biofloat tests/unit_tests.py
coverage report -m

