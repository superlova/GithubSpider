#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/1/11 17:21
# @Author  : Zyt
# @Site    : 
# @File    : test_0111.py
# @Software: PyCharm

# import os, sys

import requests
import json


# from github import Github
# from pprint import pprint

def getHTMLContent(url, params):
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Accept-Language': 'zh-CN,zh;q=0.8'
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text
    except Exception as e:
        print("fail", e)
        return None


def get_json_content(json_string):
    json_content = json.loads(json_string)
    return json_content



def test_get_html_content():
    # url = "https://api.github.com/repos/tensorflow/tensorflow"
    # url = "https://api.github.com/users/superlova/repos"
    url = "https://api.github.com/repos/tensorflow/tensorflow/commits/511c27580ad8d2eebc19eb9e2d3dc68ce42b7aaa"
    # url = "https://api.github.com/repos/tensorflow/tensorflow/git/commits"
    # params = {'q': 'windows+language:python+state:open'}
    getHTMLContent(url)

def test_get_json():
    url_temp = "https://api.github.com/repos/{}/{}/commits"
    user_name = "tensorflow"
    repo_name = "tensorflow"
    url = url_temp.format(user_name, repo_name)
    json_contents = get_json_content(getHTMLContent(url, params={'per_page':100}))
    shas = []
    for content in json_contents:
        shas.append(content['sha'])



def main():
    test_get_html_content()


if __name__ == '__main__':
    main()
