#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import json
from http.cookiejar import CookieJar

class Lingualeo:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.cj = CookieJar()

    def auth(self):
        url = "http://api.lingualeo.com/api/login"
        values = {
            "email": self.email,
            "password": self.password
        }

        return self.get_content(url, values)

    def get_translates(self, word):
        url = "http://api.lingualeo.com/gettranslates?word=" + urllib.parse.quote_plus(word)
        return self.get_content(url, {})

    def get_content(self, url, values):
        data = urllib.parse.urlencode(values)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        req = opener.open(url, data.encode('utf-8'))
        return json.loads(req.read().decode('utf-8'))
