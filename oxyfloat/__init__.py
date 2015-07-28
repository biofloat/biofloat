import pandas as pd
import urllib2

def get_oxy_floats(age=340):
    '''Starting with listing of all floats convert the response so that
    the data can be put into a Pandas DataFrame.
    '''
    argo_all = 'http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt'
    print 'Reading data from', argo_all
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

    # Use Pandas to merge these selections
    print 'Pulling out records with oxygen, not greylisted, and older than', age
    fd_merge = pd.merge(pd.merge(fd_oxy , fd_gl), fd_age)

    # Pull out only the float numbers and return a normal Python list of them
    oxy_floats = []
    for index,row in fd_merge.loc[:,['WMO']].iterrows():
        oxy_floats.append(row['WMO'])

    return oxy_floats

def get_dac_urls(desired_float_numbers):
    '''Return list of Data Assembly Centers where profile data are archived
    '''
    global_meta = "ftp://ftp.ifremer.fr/ifremer/argo/ar_index_global_meta.txt"
    print 'Reading data from', global_meta
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

    print 'Found %d dac_urls' % len(dac_urls)

    return dac_urls
