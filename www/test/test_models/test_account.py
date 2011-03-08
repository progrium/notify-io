import unittest
from models import Account
from google.appengine.api import users

class TestAccount(unittest.TestCase):
  def test_placeholder(self):

    user = users.User("target@example.com")
    account = Account(user=user)
    account.set_hash_and_key()
    account.put()

    self.assertTrue(account.user.email() == "target@example.com")

