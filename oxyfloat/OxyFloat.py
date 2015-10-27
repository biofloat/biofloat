import re
import sys
import time
import logging
import urllib2
import requests
import pandas as pd
import pydap.client
import pydap.exceptions

from pymongo import MongoClient
from datetime import datetime, timedelta
from thredds_crawler.crawl import Crawl
from bs4 import BeautifulSoup

# Support Python 2.7 and 3.x
try:
        from io import StringIO
except ImportError:
        from cStringIO import StringIO

from exceptions import RequiredVariableNotPresent, OpenDAPServerError

# Literals for groups stored in local HDF file cache
STATUS = 'status'

class OxyFloat(object):
    '''Collection of methods for working with Argo profiling float data.
    '''

    logger = logging.getLogger(__name__)
    ch = logging.StreamHandler()

    formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                                  '%(funcName)s():%(lineno)d %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    def __init__(self, debug=False, cache_file='oxyfloat_cache.hdf',
            status_url='http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt',
            global_url='ftp://ftp.ifremer.fr/ifremer/argo/ar_index_global_meta.txt',
            thredds_url='http://tds0.ifremer.fr/thredds/catalog/CORIOLIS-ARGO-GDAC-OBS'):

        '''Initialize OxyFloat object
        
        Args:
            debug (bool): Turn on debug output, defaults to False
            status_url (str): Source URL for Argo status data, defaults to
                http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt
            global_url (str): Source URL for DAC locations, defaults to
                ftp://ftp.ifremer.fr/ifremer/argo/ar_index_global_meta.txt
             thredds_url (str): Base URL for THREDDS Data Server, defaults to
                http://tds0.ifremer.fr/thredds/catalog/CORIOLIS-ARGO-GDAC-OBS

        Note:
        thredds_url='http://thredds.aodn.org.au/thredds/catalog/IMOS/Argo/dac/'
        worked on 27 July 2015, but doesn't work now - returns 500 errors.
        '''

        self.debug = debug
        self.cache_file = cache_file
        self.status_url = status_url
        self.global_url = global_url
        self.thredds_url = thredds_url

        if debug:
            self.logger.setLevel(logging.DEBUG)

    def status_to_df(self):
        '''Save the data at status_url link to a temporary .csv file 
        and load into a Pandas DataFrame.  Returns that DataFrame.
        '''
        self.logger.debug('Reading data from %s', self.status_url)
        req = requests.get(self.status_url)
        req.encoding = 'UTF-16LE'

        # Had to tell requests the encoding, StringIO makes the text 
        # look like a file object. Skip over leading BOM bytes.
        df = pd.read_csv(StringIO(req.text[1:]))
        return df

    def put_df(self, df, name, filename):
        '''Save Pandas DataFrame to local storage.
        '''
        store = pd.HDFStore(filename)
        self.logger.debug('Saving DataFrame to name {} in file {}'
                                        .format(name, filename))
        store[name] = df
        store.close()

    def get_df(self, name, filename):
        '''Get Pandas DataFrame from local storage.
        '''
        store = pd.HDFStore(filename)
        df = store[name]
        store.close()
        return df

    def write_status(self):
        '''Read CSV Argo status data file from the Internet and cache
        its conversion to a Pandas DataFrame in a local HDF cache file.
        '''
        self.put_df(self.status_to_df(), STATUS, self.cache_file)

    def read_status(self):
        '''Read CSV Argo status data from local cache.
        Returns Pandas DataFrame.
        '''
        return self.get_df(STATUS, self.cache_file)

    def get_oxy_floats(self, age=340):
        '''Starting with listing of all floats determine which floats have an
        oxygen sensor, are not greylisted, and have more than a specified days
        of data. Returns a list of float number strings.

        Args:
            age (int): Restrict to floats with data >= age, defaults to 340
        '''
        try:
            df = self.read_status()
        except KeyError:
            self.logger.debug('Could not read status, calling write_status()')
            self.write_status()
            df = self.read_status()

        # Select only the rows that have oxygen data, not greylisted, and > age
        fd_oxy = df.loc[df.loc[:, 'OXYGEN'] == 1, :]
        fd_gl  = df.loc[df.loc[:, 'GREYLIST'] == 0 , :] 
        fd_age = df.loc[df.loc[:, 'AGE'] >= age, :]
        self.logger.debug('len(oxy) = %d, len(gl) = %d, len(age) = %d' % 
                (len(fd_oxy), len(fd_gl), len(fd_age))) 

        # Use Pandas to merge these selections
        self.logger.debug('Merging oxygen, not greylisted, and age >= %s', age)
        fd_merge = pd.merge(pd.merge(fd_oxy, fd_gl), fd_age)
        self.logger.debug('len(fd_merge) = %d', len(fd_merge))

        # Pull out only the float numbers and return a normal Python list of them
        oxy_floats = []
        for index,row in fd_merge.loc[:,['WMO']].iterrows():
            oxy_floats.append(row['WMO'])

        return oxy_floats

    def get_dac_urls(self, desired_float_numbers):
        '''Return list of Data Assembly Centers where profile data are archived

        Args:
            desired_float_numbers (list[str]): List of strings of float numbers
        '''
        global_meta = self.global_url
        self.logger.debug('Reading data from %s', global_meta)
        with open('gd1.csv', 'w') as f:
            for row in urllib2.urlopen(global_meta):
                f.write(row)

        # Put into a Pandas DataFrame, because this is what we like to do now
        gd_table = pd.read_csv('gd1.csv' , comment = '#')

        dac_urls = []
        for index,row in gd_table.loc[:,['file']].iterrows():
            floatNum = row['file'].split('/')[1]
            if floatNum in desired_float_numbers:
                url = self.thredds_url
                url += '/'.join(row['file'].split('/')[:2])
                url += "/profiles/catalog.xml"
                dac_urls.append(url)

        self.logger.debug('Found %d dac_urls' % len(dac_urls))

        return dac_urls

    def get_profile_opendap_urls(self, catalog_url, use_beautifulsoup=True):
        '''Crawl the THREDDS catalog to return all the opendap urls to the profiles.
        The thredds_crawler is rrreeeeaaaallllyyy slow so the default is to use
        BeautifulSoup to simply parse the .xml and then build the TDS urls.
        Implemented as a generator.
        '''
        if use_beautifulsoup:
            self.logger.debug("Parsing %s", catalog_url)
            req = requests.get(catalog_url)
            soup = BeautifulSoup(req.text, 'html.parser')

            # Expect that this is a standard TDS with dodsC used for OpenDAP
            base_url = '/'.join(catalog_url.split('/')[:4]) + '/dodsC/'

            # Pull out <dataset ... urlPath='...nc'> attributes from the XML
            for e in soup.findAll('dataset', attrs={'urlpath': re.compile("nc$")}):
                yield base_url + e['urlpath']

        else:
            self.logger.debug("Crawling %s", catalog_url)
            sys.stdout.flush()
            c = Crawl(catalog_url, debug=self.debug)

            # Use generator comprehension to get only the opendap urls
            (s.get("url") for d in c.datasets for s in d.services 
                    if s.get("service").lower() == "opendap")

    def get_profile_data(self, url, surface_values_only=False):
        '''Return a dictionary of tuples of lists of variables and their 
        attributes.
        '''
        self.logger.debug('Opening %s', url)
        ds = pydap.client.open_url(url)
        self.logger.debug('Checking %s', url)
        for v in ('PRES_ADJUSTED', 'TEMP_ADJUSTED', 'PSAL_ADJUSTED',
                'DOXY_ADJUSTED', 'LATITUDE', 'LONGITUDE', 'JULD'):
            if v not in ds.keys():
                raise RequiredVariableNotPresent(url + ' missing ' + v)

        # Extract data casting numpy arrays into normal Python lists
        try:
            if surface_values_only:
                p = ds['PRES_ADJUSTED'][0][0][0].tolist()
                t = ds['TEMP_ADJUSTED'][0][0][0].tolist()
                s = ds['PSAL_ADJUSTED'][0][0][0].tolist()
                o = ds['DOXY_ADJUSTED'][0][0][0].tolist()
            else:
                p = ds['PRES_ADJUSTED'][0][0].tolist()
                t = ds['TEMP_ADJUSTED'][0][0].tolist()
                s = ds['PSAL_ADJUSTED'][0][0].tolist()
                o = ds['DOXY_ADJUSTED'][0][0].tolist()

            lat = ds['LATITUDE'][0][0]
            lon = ds['LONGITUDE'][0][0]
        except pydap.exceptions.ServerError as e:
            raise OpenDAPServerError("Can't read data from " + url)

        # Compute a datetime value for the profile
        dt = datetime.strptime(ds['REFERENCE_DATE_TIME'][:], '%Y%m%d%H%M%S')
        dt += timedelta(days=ds['JULD'][0][0])

        # Build a data structure that includes metadata for each variable
        pd = {'p': [ds['PRES_ADJUSTED'].attributes, p],
              't': [ds['TEMP_ADJUSTED'].attributes, t],
              's': [ds['PSAL_ADJUSTED'].attributes, s],
              'o': [ds['DOXY_ADJUSTED'].attributes, o],
              'lat': [ds['LATITUDE'].attributes, lat],
              'lon': [ds['LONGITUDE'].attributes, lon],
              'dt': [{'name': 'time', 'units': 'UTC'}, dt]}
                  
        return pd

    def get_data_for_float(self, dac_url, only_file=None, 
            surface_values_only=False):
        '''Given a dac_url return a list of hashes of data for each 
        profile for the float specified in dac_url.  Example dac_url
        for float 1900722:

        http://tds0.ifremer.fr/thredds/catalog/CORIOLIS-ARGO-GDAC-OBSaoml/1900722/profiles/catalog.xml
        '''
        pd = []
        for profile_url in sorted(self.get_profile_opendap_urls(dac_url)):
            if only_file:
                if not profile_url.endswith(only_file):
                    continue

            float = profile_url.split('/')[7]
            prof = str(profile_url.split('/')[-1].split('.')[0].split('_')[1])
            self.logger.info('Reading data from ' + profile_url[:20] + '...' +
                       profile_url[-50:])
            try:
                d = self.get_profile_data(profile_url, 
                        surface_values_only=surface_values_only)
                pd.append({float: {prof: d}})
            except RequiredVariableNotPresent as e:
                self.logger.warn(e)
            except OpenDAPServerError as e:
                self.logger.warn(e)

        return pd

    def db_insert_float_data(self, float_data):
        '''Insert/update document into Mongo database
        '''
        client = MongoClient()
        db = client.oxyfloat
        floats = db.floats

        result = floats.insert_many(float_data)
        self.logger.debug('IDs stored in mongodb floats database' + 
                str(result.inserted_ids))

