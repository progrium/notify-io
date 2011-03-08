from webtest import TestApp
from api import application

app = TestApp(application())

def test_placeholder():
  app.post("/v1/notify/1234", status=404)

