import unittest

from h5rdmtoolbox._repr import process_string_for_link


class TestRepr(unittest.TestCase):

    def test_process_string_for_link(self):
        string_without_url = "This is a string without a web URL"
        processed_string, has_url = process_string_for_link(string_without_url)
        self.assertFalse(has_url)
        self.assertEqual(processed_string, string_without_url)

        string_with_url = "This is a string with a web URL: https://www.example.com which goes on and on and on"
        string_with_href = 'This is a string with a web URL: ' \
                           '<a href="https://www.example.com">https://www.example.com</a> which goes on and on and on'
        processed_string, has_url = process_string_for_link(string_with_url)
        self.assertTrue(has_url)
        self.assertEqual(processed_string, string_with_href)
