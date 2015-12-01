#!/usr/bin/env python

import sys
from os.path import join, dirname, abspath, expanduser
parent_dir = join(dirname(__file__), "../")
sys.path.insert(0, parent_dir)

from biofloat import ArgoData

class ArgoDataLoader(object):

    def short_cache_file(self):
        '''Build cache_file short name from command line arguments and
        from format descriptors from ArgoData.
        '''
        # This unfortunately tricky loop finds all class variables in
        # ArgoData ending with 'RE' (e.g. 'ageRE', 'profilesRE') and
        # gets the corresponding argument value for building the 
        # cache file name. It allows control of items from ArgoData
        # but suffers from having to keep this script's calling
        # arguments in sync with the *RE variables in ArgoData.

        cache_file = ArgoData._fixed_cache_base
        # Lop off leading '_' and trailing 'RE' from regex values in ArgoData
        for item in [a[1:-2] for a in dir(ArgoData) 
                                 if not callable(a) and a.endswith("RE")]:
            try:
                value = '-'.join(sorted(vars(self.args)[item]))
            except TypeError:
                value = vars(self.args)[item]
            except KeyError:
                value = None

            if value:
                try:
                    cache_file += '_{}{}'.format(item, value)
                except (KeyError, ValueError):
                    pass

        cache_file += '.hdf'

        return cache_file

    def process(self):
        if self.args.cache_file:
            cache_file = self.args.cache_file
        else:
            cache_file = self.short_cache_file()

        if self.args.cache_dir:
            cache_dir = self.args.cache_dir
        else:
            cache_dir = expanduser('~')
    
        cache_file = abspath(join(cache_dir, cache_file))

        print(('Loading cache file {}').format(cache_file))
        ad = ArgoData(verbosity=self.args.verbose, cache_file=cache_file,
                      bio_list=self.args.bio_list, variables=self.args.variables)

        if self.args.age:
            wmo_list = ad.get_oxy_floats_from_status(age_gte=self.args.age)
        elif self.args.wmo:
            wmo_list = self.args.wmo

        ad.get_float_dataframe(wmo_list, max_profiles=self.args.profiles, 
                                         max_pressure=self.args.pressure,
                                         append_df=False)

        # After loading add lookup information to the cache file
        df = ad.get_cache_file_oxy_count_df(max_profiles=self.args.profiles, flush=True)
        print(('{} floats appear to have valid oxygen data').format(len(df)))
        print(('Finished loading cache file {}').format(cache_file))

    def process_command_line(self):
        import argparse
        from argparse import RawTextHelpFormatter

        examples = 'Examples:' + '\n' 
        examples += '---------' + '\n' 
        examples += sys.argv[0] + " --age 340 --profiles 20\n"
        examples += sys.argv[0] + " --age 340 --pressure 10\n"
        examples += sys.argv[0] + " --wmo 1900650 1901157 5901073 -v\n"
        examples += "\n\n"
    
        parser = argparse.ArgumentParser(
                    description='Script to load local HDF cache with Argo float data.\n'
                                'Default cache file is located in users home\n'
                                'directory named with constraints used to build the\n'
                                'cache file.',
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                    epilog=examples)
                                             
        parser.add_argument('--age', action='store', type=int,
                            help='Select age greater than or equal') 
        parser.add_argument('--wmo', action='store', nargs='*', default=[],
                            help='One or more WMO numbers') 
        parser.add_argument('--profiles', action='store', type=int,
                            help='Maximum number of profiles')
        parser.add_argument('--pressure', action='store', type=int,
                            help='Select pressures less than this value')
        parser.add_argument('--cache_file', action='store', help='Override default file')
        parser.add_argument('--cache_dir', action='store', help='Directory for cache file'
                            ' otherwise it is \nput in the users home directory')
        parser.add_argument('--bio_list', action='store', nargs='*', default=['DOXY_ADJUSTED'],
                            help='List of bio variables to look for in N_PROF 1') 
        parser.add_argument('--variables', action='store', nargs='*', 
                            default=['TEMP_ADJUSTED', 'PSAL_ADJUSTED', 'DOXY_ADJUSTED'],
                            help='Bio-Argo variables to add to the DataFrame') 
        parser.add_argument('-v', '--verbose', nargs='?', choices=[0,1,2,3], type=int,
                            help='0: ERROR, 1: WARN, 2: INFO, 3:DEBUG', default=0, const=2)

        self.args = parser.parse_args()

        if (not self.args.age) == (not self.args.wmo):
            parser.print_help()
            print "\n*** Must specify either --age or --wmo ***\n"
            sys.exit(1)


if __name__ == '__main__':

    adl = ArgoDataLoader()
    adl.process_command_line()
    adl.process()

