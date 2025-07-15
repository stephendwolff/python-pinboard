#!/usr/bin/env python3
"""Python-Pinboard

Python module for access to pinboard <http://pinboard.in/> via its API.
Recommended: Python 2.6 or later (untested on previous versions)

This library was built on top of Paul Mucur's original work on the python-delicious
which was supported for python 2.3.  Morgan became a contributor and ported this library
to pinboard.in when it was announced in December 2010 that delicious servers may be
shutting down.

The port to pinboard resulted in the inclusion of gzip support

"""

__version__ = "1.0"
__license__ = "BSD"
__copyright__ = "Copyright 2011, Morgan Craft"
__author__ = "Morgan Craft <http://www.morgancraft.com/>"

_debug = False

USER_AGENT = (
    "Python-Pinboard/%s +http://morgancraft.com/service_layer/python-pinboard/"
    % __version__
)

import urllib.parse
import urllib.request
import urllib.error
import sys
import re
import time
import io
import gzip
from xml.dom import minidom
from collections import UserDict
import datetime

StringTypes = str
ListType = list
TupleType = tuple

PINBOARD_API = "https://api.pinboard.in/v1"
AUTH_HANDLER_REALM = "API"
AUTH_HANDLER_URI = "https://api.pinboard.in/"


def open(username=None, password=None, token=None):
    """Open a connection to a pinboard.in account"""
    return PinboardAccount(username, password, token)


def connect(username=None, password=None, token=None):
    """Open a connection to a pinboard.in account (alias for pinboard.open())."""
    return open(username, password, token)


class PinboardError(Exception):
    """Error in the Python-Pinboard module"""

    pass


class ThrottleError(PinboardError):
    """Error caused by pinboard.in throttling requests"""

    def __init__(self, url, message):
        self.url = url
        self.message = message

    def __str__(self):
        return "%s: %s" % (self.url, self.message)


class AddError(PinboardError):
    """Error adding a post to pinboard.in"""

    pass


class DeleteError(PinboardError):
    """Error deleting a post from pinboard.in"""

    pass


class BundleError(PinboardError):
    """Error bundling tags on pinboard.in"""

    pass


class DeleteBundleError(PinboardError):
    """Error deleting a bundle from pinboard.in"""

    pass


class RenameTagError(PinboardError):
    """Error renaming a tag in pinboard.in"""

    pass


class DateParamsError(PinboardError):
    """Date params error"""

    pass


class PinboardAccount(UserDict):
    """A pinboard.in account"""

    __allposts = 0
    __postschanged = 0
    __lastrequest = None
    __token = None

    def __init__(self, username=None, password=None, token=None):
        super().__init__()
        if _debug:
            sys.stderr.write("Initialising Pinboard Account object.\n")

        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        if token:
            self.__token = urllib.parse.quote_plus(token)
            opener = urllib.request.build_opener()
        else:
            password_mgr.add_password(
                AUTH_HANDLER_REALM, AUTH_HANDLER_URI, username, password
            )
            auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
            opener = urllib.request.build_opener(auth_handler)

        opener.addheaders = [("User-agent", USER_AGENT), ("Accept-encoding", "gzip")]
        urllib.request.install_opener(opener)
        if _debug:
            sys.stderr.write(
                "URL opener with HTTP authentication installed globally.\n"
            )

        self["last_updated"] = self.last_update()
        if _debug:
            sys.stderr.write("Time of last update loaded into class dictionary.\n")

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            if key == "tags":
                return self.tags()
            elif key == "dates":
                return self.dates()
            elif key == "posts":
                return self.posts()
            elif key == "bundles":
                return self.bundles()

    def __setitem__(self, key, value):
        if key == "posts":
            if _debug:
                sys.stderr.write("The value of posts has been changed.\n")
            self.__postschanged = 1
        return super().__setitem__(key, value)

    def has_key(self, key):
        return key in self.data

    def __request(self, url):
        if self.__lastrequest and (time.time() - self.__lastrequest) < 2:
            if _debug:
                sys.stderr.write(
                    "It has been less than two seconds since the last request; halting execution for one second.\n"
                )
            time.sleep(1)
        if _debug and self.__lastrequest:
            sys.stderr.write(
                "The delay between requests was %d.\n"
                % (time.time() - self.__lastrequest)
            )
        self.__lastrequest = time.time()
        if _debug:
            sys.stderr.write("Opening %s.\n" % url)

        if self.__token:
            sep = "&" if "?" in url else "?"
            url = "%s%sauth_token=%s" % (url, sep, self.__token)

        try:
            req = urllib.request.Request(url)
            req.add_header("Accept-encoding", "gzip")
            raw_xml = urllib.request.urlopen(req)
            compresseddata = raw_xml.read()
            compressedstream = io.BytesIO(compresseddata)
            gzipper = gzip.GzipFile(fileobj=compressedstream)
            xml = gzipper.read()
        except urllib.error.URLError as e:
            raise e

        self["headers"] = {}
        for header, value in raw_xml.getheaders():
            self["headers"][header.lower()] = value
        if hasattr(raw_xml, "status") and raw_xml.status == 429:
            raise ThrottleError(url, "429 HTTP status code returned by pinboard.in")
        if _debug:
            sys.stderr.write("%s opened successfully.\n" % url)
        return minidom.parseString(xml)

    def last_update(self):
        """Return the last time that the pinboard account was updated."""
        return self.__request("%s/posts/update" % PINBOARD_API).firstChild.getAttribute(
            "time"
        )

    def posts(
        self, tag="", date="", todt="", fromdt="", count=0, offset=0, only_toread=False
    ):
        """Return pinboard.in bookmarks as a list of dictionaries."""
        query = {}

        if date and (todt or fromdt):
            raise DateParamsError

        if not count and not date and not todt and not fromdt and not tag:
            path = "all"
            if _debug:
                sys.stderr.write(
                    "Checking to see if a previous download has been made.\n"
                )
            if (
                not self.__postschanged
                and self.__allposts
                and self.last_update() == self["last_updated"]
            ):
                if _debug:
                    sys.stderr.write("It has; returning old posts instead.\n")
                return self["posts"]
            elif not self.__allposts:
                if _debug:
                    sys.stderr.write("Making note of request for all posts.\n")
                self.__allposts = 1
        elif date:
            path = "get"
        elif todt or fromdt:
            path = "all"
        elif count and offset:
            path = "all"
        else:
            path = "recent"

        if count and not offset:
            query["count"] = count
        if count and offset:
            query["start"] = offset
            query["results"] = count
        if tag:
            query["tag"] = tag

        if todt and (isinstance(todt, ListType) or isinstance(todt, TupleType)):
            query["todt"] = "-".join([str(x) for x in todt[:3]])
        elif todt and (
            isinstance(todt, datetime.datetime) or isinstance(todt, datetime.date)
        ):
            query["todt"] = "-".join([str(todt.year), str(todt.month), str(todt.day)])
        elif todt:
            query["todt"] = todt

        if fromdt and (isinstance(fromdt, ListType) or isinstance(fromdt, TupleType)):
            query["fromdt"] = "-".join([str(x) for x in fromdt[:3]])
        elif fromdt and (
            isinstance(fromdt, datetime.datetime) or isinstance(fromdt, datetime.date)
        ):
            query["fromdt"] = "-".join(
                [str(fromdt.year), str(fromdt.month), str(fromdt.day)]
            )
        elif fromdt:
            query["fromdt"] = fromdt

        if date and (isinstance(date, ListType) or isinstance(date, TupleType)):
            query["dt"] = "-".join([str(x) for x in date[:3]])
        elif date and (
            isinstance(date, datetime.datetime) or isinstance(date, datetime.date)
        ):
            query["dt"] = "-".join([str(date.year), str(date.month), str(date.day)])
        elif date:
            query["dt"] = date

        postsxml = self.__request(
            "%s/posts/%s?%s" % (PINBOARD_API, path, urllib.parse.urlencode(query))
        ).getElementsByTagName("post")
        posts = []
        if _debug:
            sys.stderr.write("Parsing posts XML into a list of dictionaries.\n")

        for post in postsxml:
            postdict = {}
            for name, value in post.attributes.items():
                if name == "tag":
                    name = "tags"
                    value = value.split(" ")
                if name == "time":
                    postdict["time_parsed"] = time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
                postdict[name] = value

            if (
                self.has_key("posts")
                and isinstance(self["posts"], ListType)
                and postdict not in self["posts"]
                and not only_toread
                or (
                    only_toread
                    and ("toread" in postdict)
                    and postdict["toread"] == "yes"
                )
            ):
                self["posts"].append(postdict)
            if not only_toread or (
                only_toread and "toread" in postdict and postdict["toread"] == "yes"
            ):
                posts.append(postdict)
        if _debug:
            sys.stderr.write("Inserting posts list into class attribute.\n")
        if not self.has_key("posts"):
            self["posts"] = posts
        if _debug:
            sys.stderr.write(
                "Resetting marker so module doesn't think posts has been changed.\n"
            )
        self.__postschanged = 0
        return posts

    def suggest(self, url):
        query = {"url": url}
        tags = self.__request(
            "%s/posts/suggest?%s" % (PINBOARD_API, urllib.parse.urlencode(query))
        )

        popular = [t.firstChild.data for t in tags.getElementsByTagName("popular")]
        recommended = [
            t.firstChild.data for t in tags.getElementsByTagName("recommended")
        ]

        return {"popular": popular, "recommended": recommended}

    def tags(self):
        """Return a dictionary of tags with the number of posts in each one"""
        tagsxml = self.__request("%s/tags/get?" % PINBOARD_API).getElementsByTagName(
            "tag"
        )
        tags = []
        if _debug:
            sys.stderr.write("Parsing tags XML into a list of dictionaries.\n")
        for tag in tagsxml:
            tagdict = {}
            for name, value in tag.attributes.items():
                if name == "tag":
                    name = "name"
                elif name == "count":
                    value = int(value)
                tagdict[name] = value
            if (
                self.has_key("tags")
                and isinstance(self["tags"], ListType)
                and tagdict not in self["tags"]
            ):
                self["tags"].append(tagdict)
            tags.append(tagdict)
        if _debug:
            sys.stderr.write("Inserting tags list into class attribute.\n")
        if not self.has_key("tags"):
            self["tags"] = tags
        return tags

    def bundles(self):
        """Return a dictionary of all bundles"""
        bundlesxml = self.__request(
            "%s/tags/bundles/all" % PINBOARD_API
        ).getElementsByTagName("bundle")
        bundles = []
        if _debug:
            sys.stderr.write("Parsing bundles XML into a list of dictionaries.\n")
        for bundle in bundlesxml:
            bundledict = {}
            for name, value in bundle.attributes.items():
                bundledict[name] = value
            if (
                self.has_key("bundles")
                and isinstance(self["bundles"], ListType)
                and bundledict not in self["bundles"]
            ):
                self["bundles"].append(bundledict)
            bundles.append(bundledict)
        if _debug:
            sys.stderr.write("Inserting bundles list into class attribute.\n")
        if not self.has_key("bundles"):
            self["bundles"] = bundles
        return bundles

    def dates(self, tag=""):
        """Return a dictionary of dates with the number of posts at each date"""
        if tag:
            query = urllib.parse.urlencode({"tag": tag})
        else:
            query = ""
        datesxml = self.__request(
            "%s/posts/dates?%s" % (PINBOARD_API, query)
        ).getElementsByTagName("date")
        dates = []
        if _debug:
            sys.stderr.write("Parsing dates XML into a list of dictionaries.\n")
        for date in datesxml:
            datedict = {}
            for name, value in date.attributes.items():
                if name == "date":
                    datedict["date_parsed"] = time.strptime(value, "%Y-%m-%d")
                elif name == "count":
                    value = int(value)
                datedict[name] = value
            if (
                self.has_key("dates")
                and isinstance(self["dates"], ListType)
                and datedict not in self["dates"]
            ):
                self["dates"].append(datedict)
            dates.append(datedict)
        if _debug:
            sys.stderr.write("Inserting dates list into class attribute.\n")
        if not self.has_key("dates"):
            self["dates"] = dates
        return dates

    def add(
        self,
        url,
        description,
        extended="",
        tags=(),
        date="",
        toread="no",
        replace="no",
        shared="yes",
    ):
        """Add a new post to pinboard.in"""
        query = {}
        query["url"] = url
        query["description"] = description
        query["toread"] = toread
        query["replace"] = replace
        query["shared"] = shared
        if extended:
            query["extended"] = extended
        if tags and (isinstance(tags, TupleType) or isinstance(tags, ListType)):
            query["tags"] = " ".join(tags)
        elif tags and isinstance(tags, StringTypes):
            query["tags"] = tags

        if date and isinstance(date, StringTypes) and len(date) < 20:
            date = re.split("\D", date)
            while "" in date:
                date.remove("")
        if date and (isinstance(date, ListType) or isinstance(date, TupleType)):
            date = list(date)
            if len(date) > 2 and len(date) < 6:
                for i in range(6 - len(date)):
                    date.append(0)
            query["dt"] = "%.4d-%.2d-%.2dT%.2d:%.2d:%.2dZ" % tuple(map(int, date))
        elif date and (
            isinstance(date, datetime.datetime) or isinstance(date, datetime.date)
        ):
            query["dt"] = "%.4d-%.2d-%.2dT%.2d:%.2d:%.2dZ" % date.utctimetuple()[:6]
        elif date:
            query["dt"] = date
        try:
            response = self.__request(
                "%s/posts/add?%s" % (PINBOARD_API, urllib.parse.urlencode(query))
            )
            if response.firstChild.getAttribute("code") != "done":
                raise AddError
            if _debug:
                sys.stderr.write(
                    "Post, %s (%s), added to pinboard.in\n" % (description, url)
                )
        except Exception:
            if _debug:
                sys.stderr.write(
                    "Unable to add post, %s (%s), to pinboard.in\n" % (description, url)
                )

    def bundle(self, bundle, tags):
        """Bundle a set of tags together"""
        query = {}
        query["bundle"] = bundle
        if tags and (isinstance(tags, TupleType) or isinstance(tags, ListType)):
            query["tags"] = " ".join(tags)
        elif tags and isinstance(tags, StringTypes):
            query["tags"] = tags
        try:
            response = self.__request(
                "%s/tags/bundles/set?%s" % (PINBOARD_API, urllib.parse.urlencode(query))
            )
            if response.firstChild.getAttribute("code") != "done":
                raise BundleError
            if _debug:
                sys.stderr.write("Tags, %s, bundled into %s.\n" % (repr(tags), bundle))
        except Exception:
            if _debug:
                sys.stderr.write(
                    "Unable to bundle tags, %s, into %s to pinboard.in\n"
                    % (repr(tags), bundle)
                )

    def delete(self, url):
        """Delete post from pinboard.in by its URL"""
        try:
            response = self.__request(
                "%s/posts/delete?%s"
                % (PINBOARD_API, urllib.parse.urlencode({"url": url}))
            )
            if response.firstChild.getAttribute("code") != "done":
                raise DeleteError
            if _debug:
                sys.stderr.write("Post, %s, deleted from pinboard.in\n" % url)
        except Exception:
            if _debug:
                sys.stderr.write("Unable to delete post, %s, from pinboard.in\n" % url)

    def delete_bundle(self, name):
        """Delete bundle from pinboard.in by its name"""
        try:
            response = self.__request(
                "%s/tags/bundles/delete?%s"
                % (PINBOARD_API, urllib.parse.urlencode({"bundle": name}))
            )
            if response.firstChild.getAttribute("code") != "done":
                raise DeleteBundleError
            if _debug:
                sys.stderr.write("Bundle, %s, deleted from pinboard.in\n" % name)
        except Exception:
            if _debug:
                sys.stderr.write(
                    "Unable to delete bundle, %s, from pinboard.in\n" % name
                )

    def rename_tag(self, old, new):
        """Rename a tag"""
        query = {"old": old, "new": new}
        try:
            response = self.__request(
                "%s/tags/rename?%s" % (PINBOARD_API, urllib.parse.urlencode(query))
            )
            if response.firstChild.getAttribute("code") != "done":
                raise RenameTagError
            if _debug:
                sys.stderr.write("Tag, %s, renamed to %s\n" % (old, new))
        except Exception:
            if _debug:
                sys.stderr.write(
                    "Unable to rename %s tag to %s in pinboard.in\n" % (old, new)
                )

    def delete_tag(self, name):
        """Delete a tag from pinboard.in by its name"""
        try:
            response = self.__request(
                "%s/tags/delete?%s"
                % (PINBOARD_API, urllib.parse.urlencode({"tag": name}))
            )
            if response.firstChild.getAttribute("code") != "done":
                raise DeleteBundleError
            if _debug:
                sys.stderr.write("Tag, %s, deleted from pinboard.in\n" % name)
        except Exception:
            if _debug:
                sys.stderr.write("Unable to delete tag, %s, from pinboard.in\n" % name)


if __name__ == "__main__":
    if sys.argv[1:]:
        if sys.argv[1] == "-v" or sys.argv[1] == "--version":
            print(__version__)
