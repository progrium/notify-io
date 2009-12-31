import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

try:
    is_dev = os.environ['SERVER_SOFTWARE'].startswith('Dev')
except:
    is_dev = False

API_VERSION = 'v1'
if is_dev:
    API_HOST = 'localhost:8191'
    WWW_HOST = 'localhost:8091'
else:
    API_HOST = 'api.notify.io'
    WWW_HOST = 'www.notify.io'
    

class RequestHandler(webapp.RequestHandler):
    def initialize(self, request, response):
        super(RequestHandler, self).initialize(request, response)
    
    def render(self, template_path, locals):
        self.response.out.write(template.render(template_path, locals))