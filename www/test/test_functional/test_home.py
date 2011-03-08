from webtest import TestApp
from main import application

app = TestApp(application())

def test_foo():
  app.get("/")

