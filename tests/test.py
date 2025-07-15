#!/usr/bin/env python3

"""Python-Pinboard unit tests.

Before running the tests:

1. Update user credentials at conf.py (see sample_conf.py for example).
2. Consider to backup your data before running this test on real account
or use dedicated sandbox account (the second approach is recommended)."""

import conf
import unittest
import sys
import time

sys.path.insert(0, "..")

import pinboard


def api_wait():
    # Looks like there is no immediate consistency between API inputs
    # and outputs, that's why additional delays added here and below.
    print("API Threshold Delay (3 seconds)")
    time.sleep(3)
    print("API Resuming")


def get_tag_names(tags):
    for tag in tags:
        yield tag["name"]


class TestPinboardAccount(unittest.TestCase):

    def test_token(self):
        print("\nTest Token Auth and Common Cases")
        p = pinboard.open(token=conf.token)
        self.common_case(p)

    def test_canonical(self):
        print("\nTest Username/Pwd Auth and Common Cases")
        p = pinboard.open(conf.username, conf.password)
        self.common_case(p)

    def common_case(self, p):
        """Add some test bookmark records and than delete them"""
        print("Executing Common Cases")
        test_url = "http://github.com"
        test_tag = "__testing__"

        # Adding a test bookmark
        p.add(
            url=test_url,
            description="GitHub",
            extended="It's a GitHub!",
            tags=(test_tag),
            toread=False,
        )

        # Test only_toread parameter. Test bookmark should not be returned.
        posts = p.posts(tag=test_tag, only_toread=True)

        self.assertIs(type(posts), list)
        self.assertFalse(posts)

        api_wait()

        posts = p.posts(tag=test_tag)

        # Bookmark was added
        self.assertIs(type(posts), list)
        self.assertTrue(posts)

        api_wait()

        # Tags contains new tag
        tags = p.tags()
        self.assertIsInstance(tags, dict)
        self.assertIn(test_tag, get_tag_names(tags))

        # Deleting test bookmark(s)
        for post in posts:
            p.delete(post["href"])

        api_wait()

        # There are no posts with test tag
        posts = p.posts(tag=test_tag)
        self.assertFalse(posts)

        # And no test tag any more
        tags = p.tags()
        self.assertNotIn(test_tag, get_tag_names(tags))

    def test_delete_tag(self):
        """Test tag deletion"""
        p = pinboard.open(token=conf.token)

        test_url = "http://github.com"
        test_tag = "__testing__"

        # Clean pre-conditions
        p.delete(test_url)

        # Test pre-conditions (no test tag)
        tags = p.tags()
        self.assertNotIn(test_tag, get_tag_names(tags))

        # Adding a test bookmark
        p.add(
            url=test_url,
            description="GitHub",
            extended="It's a GitHub!",
            tags=(test_tag),
            toread=False,
            replace="yes",
        )

        api_wait()

        # Tags contains new tag
        tags = p.tags()
        self.assertIsInstance(tags, dict)
        self.assertIn(test_tag, get_tag_names(tags))

        # Deleting test tag
        p.delete_tag(test_tag)

        api_wait()

        # There are no posts with test tag
        posts = p.posts(tag=test_tag)
        self.assertFalse(posts)

        # And no test tag any more
        tags = p.tags()
        self.assertNotIn(test_tag, get_tag_names(tags))

        # Clean Up
        p.delete(test_url)


if __name__ == "__main__":
    unittest.main()
