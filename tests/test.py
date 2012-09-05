#!/usr/bin/env python

"""Python-Pinboard unit tests.

This script requires 'token.txt' file to be placed in the same directory.

Consider to backup your data before running this test on real account
or use dedicated sandbox account (the second approach is recommended).

NO WARRANTY OF ANY KIND IS EXPRESSED OR IMPLIED. YOU USE AT YOUR OWN
RISK. THE AUTHOR WILL NOT BE LIABLE FOR DATA LOSS, DAMAGES, LOSS OF PROFITS
OR ANY OTHER KIND OF LOSS WHILE USING OR MISUSING THIS SOFTWARE."""

import conf
import unittest
import sys
import time

sys.path.insert(0, '..')

import pinboard


def get_tag_names(tags):
    for tag in tags:
        yield tag['name']


class TestPinboardAccount(unittest.TestCase):

    def test_token(self):
        p = pinboard.open(token=conf.token)
        self.common_case(p)

    def test_canonical(self):
        p = pinboard.open(conf.username, conf.password)
        self.common_case(p)

    def common_case(self, p):
        """Add some test bookmark records and than delete them"""
        test_url = 'http://github.com'
        test_tag = '__testing__'

        # Adding a test bookmark
        p.add(url=test_url,
              description='GitHub',
              extended='It\'s a GitHub!',
              tags=(test_tag))

        posts = p.posts(tag=test_tag)

        # Bookmark was added
        self.assertIs(type(posts), list)
        self.assertTrue(posts)

        # Looks like there is no immediate consistency between API inputs
        # and outputs, that's why additional delays added here and below.
        time.sleep(3)

        # Tags contains new tag
        tags = p.tags()
        self.assertTrue(type(tags), dict)
        self.assertIn(test_tag, get_tag_names(tags))

        # Deleting test bookmark(s)
        for post in posts:
            p.delete(post['href'])

        time.sleep(3)

        # There are no posts with test tag
        posts = p.posts(tag=test_tag)
        self.assertFalse(posts)

        # And no test tag any more
        tags = p.tags()
        self.assertNotIn(test_tag, get_tag_names(tags))


if __name__ == '__main__':
    unittest.main()
