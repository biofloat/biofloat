
# coding: utf-8

# In[1]:

#Saturated Oxygen Data Correction


# In[2]:

#This is to import libraries of different functions that allows the program do what it's doing
get_ipython().magic(u'pylab inline')
from netCDF4 import Dataset
import pandas as pd
from pandas import Series , DataFrame
import csv
from IPython.core.display import Image
import urllib2
import StringIO
from thredds_crawler.crawl import Crawl


# In[3]:

data = urllib2.urlopen("http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt").readlines()
data


# In[3]:

data = urllib2.urlopen("http://argo.jcommops.org/FTPRoot/Argo/Status/argo_all.txt").readlines()
data[1].replace('\0' , '').replace('\xff' , '').replace('\xfe' , '').replace('\r\n' , '')
#So this works for a specific row but not the whole thing O.o
#Make a loop that runs through all of the rows one by one (since all together doesn't work)


# In[4]:

d2 = [d.replace('\0' , '').replace('\xff' , '').replace('\xfe' , '').replace('\r\n' , '') for d in data]
d2


# In[5]:

#Latest attempt
df = pd.DataFrame(d2)
type(df)


# In[6]:

with open('d2.csv', 'w') as f:
    for row in d2:
        f.write(row + '\n')

df = pd.read_csv('d2.csv')
df


# In[63]:

#This prints out certain columns (of my choosing) with all the rows still present
fd_oga = df.loc[: , ['WMO' , 'OXYGEN' , 'GREYLIST' , 'AGE' , 'DATE_' , 'LAT_' , 'LON_'] ] # oga = oxygen, grey list, and age
fd_oga


# In[64]:

#This takes the fd_oga table and only shows the rows that have oxygen data
fd_oxygen = fd_oga.loc[ fd_oga.loc[: , 'OXYGEN'] == 1 , :]
fd_oxygen


# In[65]:

#This takes the fd_oga table and only shows the rows that aren't grey listed     #gl = grey list
fd_gl = fd_oga.loc[ fd_oga.loc[: , 'GREYLIST'] == 0 , :] #gl = grey list
fd_gl


# In[66]:

#This takes the fd_oga table and only shows the rows that are at least 340 days old
fd_age = fd_oga.loc[ fd_oga.loc[: , 'AGE'] >= 340. , :]
fd_age


# In[67]:

#Merging the fd_oxygen table with the fd_gl table
fd_merge_og = pd.merge(fd_oxygen , fd_gl) #og = oxygen and grey list
fd_merge_og


# In[68]:

#Later work will go off of this table

#FINALLY HAVE ONLY THE DATA I DESIRE
#PRAISE HELIX
#After all the trial and error (=^.^=)

fd_merge_oga = pd.merge(fd_merge_og , fd_age)
fd_merge_oga
#Merged the fd_merge_og table with the fd_age table

#Inactive -> active = 0


# In[69]:

#May or may not even need this
gd = open('argo_global_meta.txt') #gd = global data
 
gd_table = pd.read_csv(gd , comment = '#')
gd_table
#Now to get it so when a user inputs a float number, the DAC of that number shows up


# In[70]:

#Now to read it into pandas :DDD
#Thank you Based Mike ;)


# In[71]:

#idea

# 20150708 H1553

#to have the program look for the specific DAC off of the Grey list file name
#Have the program unconcatenate it in a sense where you keep the first part (the DAC location) and delete the rest
#Then have the program associate that location with the specific float ID
#Hell yeah nig B)


# In[4]:

a = 'abc'
b = a - 'bc'
b


# In[5]:

a = 'abc'
b = a + 'bc'
b


# In[6]:

#So you can concatenate but not unconcatenate? Great....


# In[21]:

c = Crawl("http://thredds.aodn.org.au/thredds/catalog/IMOS/Argo/dac/coriolis/6900877/profiles/catalog.xml")


# In[22]:

c.datasets


# In[52]:

from thredds_crawler.crawl import Crawl
c = Crawl("http://thredds.aodn.org.au/thredds/catalog/IMOS/Argo/dac/coriolis/1900650/profiles/catalog.xml")
urls = [s.get("url") for d in c.datasets for s in d.services if s.get("service").lower() == "opendap"]
print urls


# In[53]:

abcdefg = Dataset("http://thredds.aodn.org.au/thredds/dodsC/IMOS/Argo/dac/coriolis/1900650/profiles/D1900650_137.nc")


# In[54]:

for v in abcdefg.variables:
    print(v)


# In[58]:

abcdefg.variables['DOXY_ADJUSTED'][:]


# In[56]:

abcdefg.variables['LATITUDE'][:]


# In[59]:

np.average(abcdefg.variables['DOXY_ADJUSTED'][:])


# In[73]:

print fd_merge_oga.values

