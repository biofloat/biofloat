#!/usr/bin/env python

import sys
import unittest
sys.path.append('../')
from oxyfloat import OxyFloat

class DataTest(unittest.TestCase):
    def setUp(self):
        self.of = OxyFloat()

    def test_get_oxyfloats(self):
        float_list = self.of.get_oxy_floats()
        print len(float_list)
        self.assertNotEqual(len(float_list), 0)


if __name__ == '__main__':
    unittest.main()
