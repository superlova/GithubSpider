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
import pandas as pd
from fake_useragent import UserAgent
import random
import getpass

HEADERS = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-us",
           "Accept-Charset": "GB2312,utf-8;q=0.7,*;q=0.7"}


def make_interval(interval_second=1):
    """装饰器，每次执行之前停顿interval_second秒"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # random_offset = random.random()
            logging.info("interval waiting: {}s".format(interval_second))
            time.sleep(interval_second)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_tracer():
    """装饰器，被装饰的函数在执行前会打印该函数名称"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logging.info("Executing {}".format(func.__name__))
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
        self.SHAs = set()
        self.files = []

        self._init_token()
        self._init_user_agent()

    def _init_token(self):
        user_name = input("please input your user name:\n")
        token = str(input("please input your token:\n"))
        # print("please input your token:\n")
        # token = getpass.getpass()
        logging.info("USERNAME: {}".format(user_name))
        logging.info("TOKEN: {}".format(token))
        self.headers['X-Github-Username'] = user_name
        self.headers['X-Github-API-Token'] = token

    @log_tracer()
    def _init_user_agent(self):
        ua = UserAgent()
        self.headers["User-Agent"] = ua.random

    def _check_remaining(self):
        limit_url = "https://api.github.com/rate_limit"
        text = self.get_html_content(limit_url, params={'headers': self.headers})
        text_json = json.loads(text)
        rate_remaining = text_json["rate"]["remaining"]
        logging.info("remaining rate: {}".format(rate_remaining))
        return rate_remaining

    @make_interval(interval_second=1)
    def get_html_content(self, url, params):
        """直接获取url的内容，Exception由外部处理"""
        r = requests.get(url, params, timeout=10)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text

    def init_SHAs(self):
        """爬指定repo的全部commit链接以供之后使用"""
        url = self.url_temp.format(self.user_name, self.repo_name)
        page = 1
        while True:
            try:
                html_content = self.get_html_content(url, params={'headers': self.headers,
                                                                  'per_pages': self.per_page,
                                                                  'page': page})
                json_contents = json.loads(html_content)
                for content in json_contents:
                    self.SHAs.add(content.get('sha'))

            except requests.exceptions.ReadTimeout:
                logging.info("ReadTimeOut!")
            except requests.exceptions.ConnectionError:
                logging.info("ConnectionTimeOut!")
            except requests.exceptions.HTTPError as e:
                logging.info("HTTPError!, {}, {}".format(type(e), str(e)))
                if self._check_remaining() == 0:
                    print("No remaining rate! exit.")
                    break
            except Exception as e:
                logging.info("Fail!, {}, {}".format(type(e), str(e)))
                break
            finally:
                page += 1
                print("End with page {}".format(page - 1))

    def init_files(self):
        """遍历链接池，获取commit的内容paste字段"""
        for sha in self.SHAs:
            url = self.url_temp.format(self.user_name, self.repo_name) + '/' + sha
            try:
                html_content = self.get_html_content(url, params={'headers': self.headers})
                json_contents = json.loads(html_content)
                for files in json_contents.get('files'):
                    if files.get('filename').endswith('.py'):
                        self.files.append({'patch': files.get('patch'),
                                           'sha': sha,
                                           'status': files.get('status'),
                                           'filename': files.get('filename'),
                                           'parents_sha': json_contents.get('parents')[0].get('sha')})
            except requests.exceptions.ReadTimeout:
                logging.info("ReadTimeOut!")
            except requests.exceptions.ConnectionError:
                logging.info("ConnectionTimeOut!")
            except requests.exceptions.HTTPError as e:
                logging.info("HTTPError!, {}, {}".format(type(e), str(e)))
                if self._check_remaining() == 0:
                    print("No remaining rate! exit.")
                    break
            except Exception as e:
                logging.info("Fail!, {}, {}".format(type(e), str(e)))
            finally:
                print("End with length {}".format(len(self.files)))

    def save_SHAs(self):
        with open("{}-{}-SHAs.txt".format(self.user_name, self.repo_name), 'w') as f:
            for sha in self.SHAs:
                f.write(sha + '\n')

    def load_SHAs(self, SHAs_file_path, limit=100):
        logging.info("current SHAs number: {}".format(len(self.SHAs)))
        SHAs_temp = []
        with open(SHAs_file_path, 'r') as f:
            for line in f:
                SHAs_temp.append(line.strip(' \n'))
        self.SHAs = set(SHAs_temp[:limit])
        logging.info("after loaded SHAs number: {}".format(len(self.SHAs)))

    def save_file(self, text, sha):
        with open("{}-{}-files-{}.txt".format(self.user_name, self.repo_name, sha), 'w') as f:
            f.write(text)

    def save_files(self, filepath):
        df = pd.DataFrame(data=self.files, columns=['patch', 'sha', 'status', 'filename', 'parents_sha'])
        print(df)
        df.to_pickle(filepath)


def test_github_crawler():
    gc = GithubCommentCrawer(user_name='tensorflow', repo_name='tensorflow')
    # gc.init_SHAs()
    # gc.save_SHAs()

    gc.load_SHAs("tensorflow-tensorflow-SHAs.txt", limit=-1)
    gc.init_files()
    gc.save_files("tensorflow-tensorflow-SHAs.tar.bz2")


def test_load_df():
    df = pd.read_pickle("tensorflow-tensorflow-SHAs.tar.bz2")
    print(df.iloc[0]['patch'])


def test_token():
    gc = GithubCommentCrawer('tensorflow', "tensorflow")
    gc.init_SHAs()
    gc.save_SHAs()


def main():
    logging.basicConfig(
        level=logging.INFO
    )
    # test_github_crawler()
    # test_load_df()
    test_token()


if __name__ == '__main__':
    main()
