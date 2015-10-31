#!/usr/bin/env python

import os
import sys
parent_dir = os.path.join(os.path.dirname(__file__), "../")
sys.path.insert(0, parent_dir)

from oxyfloat import OxyFloat
cache_file_fmt = 'oxyfloat_age_{}_max_profiles_{:d}.hdf'

class OxyFloatLoader(object):

    def process(self):
        if self.args.cache_file:
            cache_file = self.args.cache_file
        else:
            cache_file = os.path.abspath(os.path.join(parent_dir, 'oxyfloat',
                cache_file_fmt.format(self.args.age, self.args.max_profiles)))

        of = OxyFloat(verbosity=self.args.verbose, cache_file=cache_file)

        wmo_list = of.get_oxy_floats_from_status(age_gte=self.args.age)
        of.get_float_dataframe(wmo_list, max_profiles=self.args.max_profiles)

    def process_command_line(self):
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Example:' + '\n' 
        examples += sys.argv[0] + " --age 340 --max_profiles 20"
        examples += "\n\n"
    
        parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                    description='Script to load local HDF cache with Argo float data.\n'
                                'Default cache file is located in oxyfloat module\n'
                                'directory named with age and max_profiles numbers\n'
                                'with format {}.'.format(cache_file_fmt),
                    epilog=examples)
                                             
        parser.add_argument('--age', action='store', type=int, default=340,
                            help='Select age >=') 
        parser.add_argument('--max_profiles', action='store', type=int, default=1000000,
                            help='Maximum number of profiles')
        parser.add_argument('--cache_file', action='store', help='Override default file')
        parser.add_argument('-v', '--verbose', nargs='?', choices=[0,1,2,3], type=int, 
                            help='0: ERROR, 1: WARN, 2: INFO, 3:DEBUG', const=2)

        self.args = parser.parse_args()


if __name__ == '__main__':

    ofl = OxyFloatLoader()
    ofl.process_command_line()
    ofl.process()

