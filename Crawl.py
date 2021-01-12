#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/1/12 13:56
# @Author  : Zyt
# @Site    : 
# @File    : Crawl.py
# @Software: PyCharm
import requests
import json
from functools import wraps
import time
import logging

HEADERS = {"User-Agent" : "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
  "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
  "Accept-Language" : "en-us",
  "Connection" : "keep-alive",
  "Accept-Charset" : "GB2312,utf-8;q=0.7,*;q=0.7"}


def make_interval(interval_second=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logging.info("interval waiting: {}s".format(interval_second))
            time.sleep(interval_second)
            return func(*args, **kwargs)
        return wrapper
    return decorator


class GithubCommentCrawer(object):
    def __init__(self, user_name, repo_name):
        self.url_temp = "https://api.github.com/repos/{}/{}/commits"
        self.user_name = user_name
        self.repo_name = repo_name
        self.headers = HEADERS
        self.per_page = 1000
        self.shas = set()
        self.files = []

    @make_interval(interval_second=6)
    def get_html_content(self, url, params):
        r = requests.get(url, params)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text

    def init_shas(self):
        url = self.url_temp.format(self.user_name, self.repo_name)
        page = 1
        try:
            while True:
                html_content = self.get_html_content(url, params={'headers': self.headers,
                                                                  'per_pages': self.per_page,
                                                                  'page': page})
                json_contents = json.loads(html_content)
                for content in json_contents:
                    self.shas.add(content.get('sha'))
                page += 1

        except Exception as e:
            logging.info("Fail!", type(e), str(e))
        finally:
            print("End with page {}".format(page - 1))

    def init_files(self):
        for sha in self.shas:
            url = self.url_temp.format(self.user_name, self.repo_name) + '/' + sha
            try:
                html_content = self.get_html_content(url, params={'headers': self.headers})
                json_contents = json.loads(html_content)
                for files in json_contents.get('files'):
                    if files.get('filename').endswith('.py'):
                        self.files.append(files.get('patch'))
            except Exception as e:
                logging.info("Fail!", type(e), str(e))
            finally:
                print("End with length {}".format(len(self.files)))

    def save_shas(self):
        with open("{}-{}-shas.txt".format(self.user_name, self.repo_name), 'w') as f:
            for sha in self.shas:
                f.write(sha + '\n')

    def load_shas(self, shas_file_path):
        logging.info("current shas number: {}".format(len(self.shas)))
        with open(shas_file_path, 'r') as f:
            for line in f:
                self.shas.add(line.strip(' \n'))
        logging.info("after loaded shas number: {}".format(len(self.shas)))

    def save_files(self):
        with open("{}-{}-files.txt".format(self.user_name, self.repo_name), 'w') as f:
            for file in self.files:
                f.write(file + '\n')


def test_github_crawler():
    gc = GithubCommentCrawer(user_name='tensorflow', repo_name='tensorflow')
    # gc.init_shas()
    # gc.save_shas()

    gc.load_shas("tensorflow-tensorflow-shas.txt")
    gc.init_files()
    gc.save_files()


def main():
    logging.basicConfig(
        level=logging.INFO
    )
    test_github_crawler()


if __name__ == '__main__':
    main()