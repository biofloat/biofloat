import os
import re
import logging
import urllib2
import requests
import pandas as pd
import pydap.client
import pydap.exceptions
import xray

from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from contextlib import closing

# Support Python 2.7 and 3.x
try:
    from io import StringIO
except ImportError:
    from cStringIO import StringIO

from exceptions import RequiredVariableNotPresent, OpenDAPServerError

class OxyFloat(object):
    '''Collection of methods for working with Argo profiling float data.
    '''

    # Jupyter Notebook defines a root logger, use that if it exists
    if logging.getLogger().handlers:
        _notebook_handler = logging.getLogger().handlers[0]
        logger = logging.getLogger()
    else:
        logger = logging.getLogger(__name__)
        _handler = logging.StreamHandler()
        _formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                                      '%(funcName)s():%(lineno)d %(message)s')
        _handler.setFormatter(_formatter)
        logger.addHandler(_handler)

    _log_levels = (logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG)

    # Literals for groups stored in local HDF file cache
    _STATUS = 'status'
    _GLOBAL_META = 'global_meta'

    def __init__(self, verbosity=0, cache_file=None,
            status_url='http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt',
            global_url='ftp://ftp.ifremer.fr/ifremer/argo/ar_index_global_meta.txt',
            thredds_url='http://tds0.ifremer.fr/thredds/catalog/CORIOLIS-ARGO-GDAC-OBS'):

        '''Initialize OxyFloat object
        
        Args:
            verbosity (int): range(4), default=0
            cache_file (str): Defaults to oxyfloat_cache.hdf next to module
            status_url (str): Source URL for Argo status data, defaults to
                http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt
            global_url (str): Source URL for DAC locations, defaults to
                ftp://ftp.ifremer.fr/ifremer/argo/ar_index_global_meta.txt
            thredds_url (str): Base URL for THREDDS Data Server, defaults to
                http://tds0.ifremer.fr/thredds/catalog/CORIOLIS-ARGO-GDAC-OBS
        '''
        self.status_url = status_url
        self.global_url = global_url
        self.thredds_url = thredds_url

        self.logger.setLevel(self._log_levels[verbosity])

        if cache_file:
            self.cache_file = cache_file
        else:
            # Write to same directory where this module is installed
            self.cache_file = os.path.abspath(os.path.join(
                              os.path.dirname(__file__), 'oxyfloat_cache.hdf'))

    def _put_df(self, df, name):
        '''Save Pandas DataFrame to local storage.
        '''
        store = pd.HDFStore(self.cache_file)
        self.logger.info('Saving DataFrame to name "%s" in file %s',
                                            name, self.cache_file)
        store[name] = df
        self.logger.debug('store.close()')
        store.close()

    def _get_df(self, name):
        '''Get Pandas DataFrame from local storage or raise KeyError.
        '''
        store = pd.HDFStore(self.cache_file)
        try:
            self.logger.debug('Getting "%s" from %s', name, self.cache_file)
            df = store[name]
        except KeyError:
            raise
        finally:
            self.logger.debug('store.close()')
            store.close()

        return df

    def _status_to_df(self):
        '''Read the data at status_url link and return it as a Pandas DataFrame.
        '''
        self.logger.info('Reading data from %s', self.status_url)
        req = requests.get(self.status_url)
        req.encoding = 'UTF-16LE'

        # Had to tell requests the encoding, StringIO makes the text 
        # look like a file object. Skip over leading BOM bytes.
        df = pd.read_csv(StringIO(req.text[1:]))
        return df

    def _global_meta_to_df(self):
        '''Read the data at global_url link and return it as a Pandas DataFrame.
        '''
        self.logger.info('Reading data from %s', self.global_url)
        with closing(urllib2.urlopen(self.global_url)) as r:
            df = pd.read_csv(r, comment='#')

        return df

    def _profile_to_dataframe(self, url):
        '''Return a Pandas DataFrame of profiling float data from data at url.
        '''
        self.logger.debug('Opening %s', url)
        ds = xray.open_dataset(url)
        desired_vars = ('TEMP_ADJUSTED', 'PSAL_ADJUSTED', 'DOXY_ADJUSTED', 
                        'PRES_ADJUSTED', 'LATITUDE', 'LONGITUDE', 'JULD')

        self.logger.debug('Checking %s for our desired variables', url)
        for v in desired_vars:
            if v not in ds.keys():
                raise RequiredVariableNotPresent(url + ' missing ' + v)

        # Make a table with variables as columns and PRES_ADJUSTED as rows
        # Argo data have a N_PROF dimension always of length 1, hence the [0]
        df = pd.DataFrame()
        indices = ['{}_{}'.format(str(ds['JULD'].values[0]).split('.')[0], pres) 
                                    for pres in ds['PRES_ADJUSTED'].values[0]]
        for v in desired_vars:
            try:
                s = pd.Series(ds[v].values[0], index=indices)
                n = '{} ({})'.format(v, ds[v].attrs['units'])
                self.logger.debug('Added %s to DataFrame', n)
                df[n] = s
            except KeyError:
                self.logger.warn('%s not in %s', v, url)

        return df

    def _url_to_naturalname(self, url):
        '''Remove HDFStore illegal characters from url and return key string.
        '''
        regex = re.compile(r"[^a-zA-Z0-9_]")
        return regex.sub('', url)

    def set_verbosity(self, verbosity):
        '''Change loglevel. 0: ERROR, 1: WARN, 2: INFO, 3:DEBUG
        '''
        self.logger.setLevel(self._log_levels[verbosity])


    def get_oxy_floats(self, age_gte=340):
        '''Starting with listing of all floats determine which floats have an
        oxygen sensor, are not greylisted, and have more than a specified days
        of data. Returns a list of float number strings.

        Args:
            age_gte (int): Restrict to floats with data >= age, defaults to 340
        '''
        try:
            df = self._get_df(self._STATUS)
        except KeyError:
            self.logger.debug('Could not read status, putting it into the cache.')
            self._put_df(self._status_to_df(), self._STATUS)
            df = self._get_df(self._STATUS)

        # Select only the rows that have oxygen data, not greylisted, and > age_gte
        fd_oxy = df.loc[df.loc[:, 'OXYGEN'] == 1, :]
        fd_gl  = df.loc[df.loc[:, 'GREYLIST'] == 0 , :] 
        fd_age = df.loc[df.loc[:, 'AGE'] >= age_gte, :]
        self.logger.debug('len(oxy) = %d, len(gl) = %d, len(age_gte) = %d',
                                        len(fd_oxy), len(fd_gl), len(fd_age)) 

        # Use Pandas to merge these selections
        self.logger.debug('Merging oxygen, not greylisted, and age >= %s', age_gte)
        fd_merge = pd.merge(pd.merge(fd_oxy, fd_gl), fd_age)
        self.logger.debug('len(fd_merge) = %s', len(fd_merge))

        # Pull out only the float numbers and return a normal Python list of them
        oxy_floats = []
        for _, row in fd_merge.loc[:,['WMO']].iterrows():
            oxy_floats.append(row['WMO'])

        return oxy_floats

    def get_dac_urls(self, desired_float_numbers):
        '''Return list of Data Assembly Centers where profile data are archived

        Args:
            desired_float_numbers (list[str]): List of strings of float numbers
        '''
        try:
            df = self._get_df(self._GLOBAL_META)
        except KeyError:
            self.logger.debug('Could not read global_meta, putting it into cache.')
            self._put_df(self._global_meta_to_df(), self._GLOBAL_META)
            df = self._get_df(self._GLOBAL_META)

        dac_urls = []
        for _, row in df.loc[:,['file']].iterrows():
            floatNum = row['file'].split('/')[1]
            if floatNum in desired_float_numbers:
                url = self.thredds_url
                url += '/'.join(row['file'].split('/')[:2])
                url += "/profiles/catalog.xml"
                dac_urls.append(url)

        self.logger.debug('Found %s dac_urls', len(dac_urls))

        return dac_urls

    def get_profile_opendap_urls(self, catalog_url):
        '''Returns an iterable to the opendap urls for the profiles in catalog.
        The `catalog_url` is the .xml link for a directory on a THREDDS Data 
        Server.
        '''
        self.logger.debug("Parsing %s", catalog_url)
        req = requests.get(catalog_url)
        soup = BeautifulSoup(req.text, 'html.parser')

        # Expect that this is a standard TDS with dodsC used for OpenDAP
        base_url = '/'.join(catalog_url.split('/')[:4]) + '/dodsC/'

        # Pull out <dataset ... urlPath='...nc'> attributes from the XML
        for e in soup.findAll('dataset', attrs={'urlpath': re.compile("nc$")}):
            yield base_url + e['urlpath']

    def get_float_dataframe(self, float_wmo):
        '''Returns Pandas DataFrame for all the profile data from float_wmo.
        Uses cached data if present, populates cache if not present.
        '''
        float_df = pd.DataFrame()
        for dac_url in self.get_dac_urls([float_wmo]):
            for url in self.get_profile_opendap_urls(dac_url):
                key = self._url_to_naturalname(url)
                try:
                    df = self._get_df(key)
                except KeyError:
                    try:
                        df = self._profile_to_dataframe(url)
                        self._put_df(df, key)
                        self.logger.debug(df.head())
                    except RequiredVariableNotPresent:
                        self.logger.warn('RequiredVariableNotPresent in %s', url)
                        # Insert an empy DataFrame to mark this key as taken
                        self._put_df(pd.DataFrame(), key)

                float_df = float_df.append(df)

        return float_df

