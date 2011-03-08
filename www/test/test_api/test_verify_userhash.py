from webtest import TestApp
from api import application
from google.appengine.api import users
from models import Account
import test

app = TestApp(application())

def test_unauthenticated_request():
  """
  Should return a 403 if request does not provide a valid api key
  """
  response = app.get("/v1/users/abcdef", status=403)
  assert response.body == "403 Missing required parameters"

  test.reset_datastore()


def test_verify_non_existing_user():
  """
  Should return a 404 if userhash does not have a Notify.io account
  """
  user = users.User("source@example.com")
  account = Account(user=user)
  account.set_hash_and_key()
  account.put()

  response = app.get("/v1/users/abcdef?api_key=%s" % account.api_key, status=404)

  assert response.body == "404 User not found"

  test.reset_datastore()


def test_verify_existing_user():
  """
  Should return 200
  """
  user = users.User("target@example.com")
  account = Account(user=user)
  account.set_hash_and_key()
  account.put()

  response = app.get("/v1/users/%s?api_key=%s" % (account.hash,
    account.api_key), status=200)

  assert response.body == "200 OK"

  test.reset_datastore()

