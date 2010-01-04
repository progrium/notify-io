import os

try:
    is_dev = os.environ['SERVER_SOFTWARE'].startswith('Dev')
except:
    is_dev = False

API_VERSION = 'v1'
if is_dev:
    API_HOST = 'localhost:9090'
    WWW_HOST = 'localhost:8081'
else:
    API_HOST = 'api.notify.io'
    WWW_HOST = 'www.notify.io'