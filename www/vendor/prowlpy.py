#/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prowlpy V0.4.2

Written by Jacob Burch, 7/6/2009

Python module for posting to the iPhone Push Notification service Prowl: http://prowl.weks.net/
"""
__author__ = 'jacobburch@gmail.com'
__version__ = 0.42

from httplib2 import Http
from urllib import urlencode

API_DOMAIN = 'https://prowl.weks.net/publicapi'

class Prowl(object):
    def __init__(self, apikey, providerkey = None):
        """
        Initialize a Prowl instance.
        """
        self.apikey = apikey
        self.providerkey = providerkey
        # Aliasing
        self.add = self.post
        
    def post(self, application=None, event=None, description=None,priority=0):
        # Create the http object
        h = Http()
        
        # Set User-Agent
        headers = {'User-Agent': "Prowlpy/%s" % str(__version__)}
        
        # Perform the request and get the response headers and content
        data = {
            'apikey': self.apikey,
            'application': application,
            'event': event,
            'description': description,
            'priority': priority

        }
        if self.providerkey:
            data['providerkey'] = self.providerkey

        headers["Content-type"] = "application/x-www-form-urlencoded"
        resp,content = h.request("%s/add/" % API_DOMAIN, "POST", headers=headers, body=urlencode(data))
        
        if resp['status'] == '200':
            return True
        elif resp['status'] == '401': 
            raise Exception("Auth Failed: %s" % content)
        else:
            raise Exception("Failed")
        
    
    def verify_key(self):
        h = Http()
        headers = {'User-Agent': "Prowlpy/%s" % str(__version__)}
        verify_resp,verify_content = h.request("%s/verify?apikey=%s" % \
                                               (API_DOMAIN,self.apikey),
                                               headers=headers)
        if verify_resp['status'] != '200':
            raise Exception("Invalid API Key %s" % verify_content)
        else:
            return True
