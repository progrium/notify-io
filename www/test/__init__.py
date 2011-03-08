from models import Account

def setup():
  import os

  os.environ['SERVER_NAME'] = 'localhost'
  os.environ['SERVER_PORT'] = '8081'
  os.environ['AUTH_DOMAIN'] = 'example.org'
  os.environ['USER_EMAIL'] = ''
  os.environ['USER_ID'] = ''

def reset_datastore():
  for klass in [Account]:
    for instance in klass.all():
      try:
        klass.delete(instance)
      except:
        pass

