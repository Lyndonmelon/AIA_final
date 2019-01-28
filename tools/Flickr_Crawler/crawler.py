# be sure to pip install flickrapi
# This program will download relevant images from Flickr.com using the provided api key and secrets (for now just use mine)
# The parameters of the flickr.walk should be further tuned for optimization
# To use this code, simply enter the keyword at the bottom and run in terminal

import os
import argparse
import flickrapi

import urllib
import requests

api_key='7edc3b247153f681ddfa4c11d1b8688d'
api_secret='70292aaa71fc9e29'

flickr=flickrapi.FlickrAPI(api_key,api_secret,cache=True)


def save_photo(url, filename):
    r = requests.get(url, allow_redirects=True)
    open('downloads/'+filename, 'wb').write(r.content)
    
    
def flickr_walk(keyward):
    photos = flickr.walk(text=keyward,
                         tag_mode='all',
                         tags=keyward,
                         sort="relevance",
                         extras='url_c',
                         per_page=10)

    for photo in photos:
        try:
            url=photo.get('url_c')            
            filename = url.split('/')[-1]
            save_photo(url, filename)
            print('image downloaded')
        except Exception as e:
            print('failed to download image')


flickr_walk('paper cup')

    
    
    
    