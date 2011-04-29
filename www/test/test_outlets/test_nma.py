import unittest
from outlet_types import NMA

class TestNMA(unittest.TestCase):
  def test_placeholder(self):
    self.assertEqual(NMA.name, "NotifyMyAndroid")

