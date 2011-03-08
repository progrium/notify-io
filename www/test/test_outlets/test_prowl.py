import unittest
from outlet_types import Prowl

class TestProwl(unittest.TestCase):
  def test_placeholder(self):
    self.assertEqual(Prowl.name, "Prowl")

