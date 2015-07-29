import re
import sys
import time
import logging
import urllib2
import requests
import pandas as pd

from netCDF4 import Dataset
from datetime import datetime
from thredds_crawler.crawl import Crawl
from BeautifulSoup import BeautifulSoup


logger = logging.getLogger(__name__)
ch = logging.StreamHandler()

formatter = logging.Formatter('%(levelname)s %(asctime)s %(filename)s '
                              '%(funcName)s():%(lineno)d %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)


class RequiredVariableNotPresent(Exception):
    pass


def get_oxy_floats(age=340):
    '''Starting with listing of all floats convert the response so that
    the data can be put into a Pandas DataFrame.
    '''
    argo_all = 'http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt'
    logger.debug('Reading data from %s', argo_all)
    data = urllib2.urlopen(argo_all).readlines()
    d2 = [d.replace('\0' , '').replace('\xff' , '').replace('\xfe' , '').
            replace('\r\n' , '') for d in data]

    # Write the data to a file so that it can be read into a Pandas DataFrame
    with open('d2.csv', 'w') as f:
        for row in d2:
            f.write(row + '\n')
    df = pd.read_csv('d2.csv')

    # Select only the rows that have oxygen data, not greylisted, and > age
    fd_oxy = df.loc[df.loc[:, 'OXYGEN'] == 1, :]
    fd_gl  = df.loc[df.loc[:, 'GREYLIST'] == 0 , :] 
    fd_age = df.loc[df.loc[:, 'AGE'] >= age, :]
    logger.debug('len(oxy) = %d, len(gl) = %d, len(age) = %d' % (len(fd_oxy), len(fd_gl), len(fd_age))) 

    # Use Pandas to merge these selections
    logger.debug('Merging records with oxygen, not greylisted, and age >= %s',
                  age)
    fd_merge = pd.merge(pd.merge(fd_oxy, fd_gl), fd_age)
    logger.debug('len(fd_merge) = %d', len(fd_merge))

    # Pull out only the float numbers and return a normal Python list of them
    oxy_floats = []
    for index,row in fd_merge.loc[:,['WMO']].iterrows():
        oxy_floats.append(row['WMO'])

    return oxy_floats

def get_dac_urls(desired_float_numbers):
    '''Return list of Data Assembly Centers where profile data are archived
    '''
    global_meta = "ftp://ftp.ifremer.fr/ifremer/argo/ar_index_global_meta.txt"
    logger.debug('Reading data from %s', global_meta)
    with open('gd1.csv', 'w') as f:
        for row in urllib2.urlopen(global_meta):
            f.write(row)

    # Put into a Pandas DataFrame, because this is what we like to do now
    gd_table = pd.read_csv('gd1.csv' , comment = '#')

    dac_urls = []
    for index,row in gd_table.loc[:,['file']].iterrows():
        floatNum = row['file'].split('/')[1]
        if floatNum in desired_float_numbers:
            url = "http://thredds.aodn.org.au/thredds/catalog/IMOS/Argo/dac/"
            url += '/'.join(row['file'].split('/')[:2])
            url += "/profiles/catalog.xml"
            dac_urls.append(url)

    logger.debug('Found %d dac_urls' % len(dac_urls))

    return dac_urls

def get_profile_opendap_urls(catalog_url, use_beautifulsoup=True):
    '''Crawl the THREDDS catalog to return all the opendap urls to the profiles.
    The thredds_crawler is rrreeeeaaaallllyyy slow so the default is to use
    BeautifulSoup to simply parse the .xml and then build the TDS urls.
    '''
    start_time = time.time()
    if use_beautifulsoup:
        logger.debug("Parsing %s", catalog_url)
        req = requests.get(catalog_url)
        soup = BeautifulSoup(req.text)

        # Expect that this is a standard TDS with dodsC used for OpenDAP
        base_url = '/'.join(catalog_url.split('/')[:4]) + '/dodsC/'

        # Pull out <dataset ... urlPath='...nc'> attributes from the XML
        urls = []
        for e in soup.findAll('dataset', attrs={'urlpath': re.compile("nc$")}):
            urls.append(base_url + e['urlpath'])

    else:
        logger.debug("Crawling %s", catalog_url)
        sys.stdout.flush()
        c = Crawl(catalog_url, debug=True)

        # Use list comprehension to get only the opendap urls
        urls = [s.get("url") for d in c.datasets for s in d.services 
                if s.get("service").lower() == "opendap"]

    sec_diff = time.time() - start_time
    logger.debug("Found %s netCDF files in %.1f seconds" % (len(urls), sec_diff))

    return urls

def get_profile_data(url):
    '''Return a dictionary of lists of varaibles
    '''
    logger.debug('Opening %s', url)
    ds = Dataset(url)
    logger.debug('Checking %s', url)
    for v in ('PRES_ADJUSTED', 'TEMP_ADJUSTED', 'PSAL_ADJUSTED',
            'DOXY_ADJUSTED', 'LATITUDE', 'LONGITUDE', 'JULD'):
        if v not in ds.variables:
            raise RequiredVariableNotPresent(url + ' missing ' + v)

    import pdb; pdb.set_trace()
    p = ds.variables['PRES_ADJUSTED'][0][:]
    t = ds.variables['TEMP_ADJUSTED'][0][:]
    s = ds.variables['PSAL_ADJUSTED'][0][:]
    o = ds.variables['DOXY_ADJUSTED'][0][:]

    lat = ds.variables['LATITUDE'][0]
    lon = ds.variables['LONGITUDE'][0]

    # Compute a datetime value for the profile
    epoch = datetime.strptime(ds.variables['REFERENCE_DATE_TIME'], 
            '%Y%m%d%H%M%S')
    dt = epoch + timedelta(days=ds.variables['JULD'][0])

    return {'p': p, 't': t, 's': s, 'o': o, 'lat': lat, 'lon': lon, 'dt': dt}

