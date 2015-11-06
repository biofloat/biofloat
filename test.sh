#!/bin/bash
coverage run --source=oxyfloat scripts/load_cache.py --age 3000 --profiles 1
coverage run -a --source=oxyfloat tests/unit_tests.py
coverage report -m

