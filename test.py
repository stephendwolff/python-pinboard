#!/usr/bin/env python

"""Python-Pinboard unit tests.

This script requires 'token.txt' file to be placed in the same directory.

Consider to backup your data before running this test on real account
or use dedicated sandbox account (the second approach is recommended).

NO WARRANTY OF ANY KIND IS EXPRESSED OR IMPLIED. YOU USE AT YOUR OWN
RISK. THE AUTHOR WILL NOT BE LIABLE FOR DATA LOSS, DAMAGES, LOSS OF PROFITS
OR ANY OTHER KIND OF LOSS WHILE USING OR MISUSING THIS SOFTWARE."""

import unittest
import sys
import time

sys.path.insert(0, '.')

import pinboard


TOKEN = 'token.txt'


def get_token():
    try:
        with open(TOKEN, 'r') as f:
            return f.read().strip()
    except:
        print('error reading token from ' + TOKEN)
        raise


def gate_tag_names(tags):
    for tag in tags:
        yield tag['name']


# TODO: Cover PinboardAccount functionality

class TestPinboardAccount(unittest.TestCase):

    # PinboardAccount instance (new for each test)
    __p = None

    def setUp(self):
        self.__p = pinboard.open(token=get_token())

    def test_basics(self):
        """Add some test bookmark records and than delete them"""
        p = self.__p
        test_url = 'http://github.com'
        test_tag = '__testing__'

        # Adding a test bookmark
        p.add(url=test_url,
              description='GitHub',
              extended='It\'s a GitHub!',
              tags=(test_tag))

        posts = p.posts(tag=test_tag)

        # Looks like there is no immediate consistency between API inputs
        # and outputs, that's why additional delays added here and below.
        time.sleep(1)

        # Bookmark was added
        self.assertIs(type(posts), list)
        self.assertTrue(posts)

        time.sleep(1)

        # Tags contains new tag
        tags = p.tags()
        self.assertTrue(type(tags), dict)
        self.assertIn(test_tag, gate_tag_names(tags))

        # Deleting test bookmark(s)
        for post in posts:
            p.delete(post['href'])

        time.sleep(1)

        # There are no posts with test tag
        posts = p.posts(tag=test_tag)
        self.assertFalse(posts)

        # And no test tag any more
        tags = p.tags()
        self.assertNotIn(test_tag, gate_tag_names(tags))


if __name__ == '__main__':
    unittest.main()
