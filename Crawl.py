#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/1/12 13:56
# @Author  : Zyt
# @Site    : 
# @File    : Crawl.py
# @Software: PyCharm
import requests
import os
import json
from concurrent.futures import ProcessPoolExecutor
import logging
import pandas as pd
from fake_useragent import UserAgent
import configparser
from Utils import HEADERS, make_interval, log_tracer


class GiuHubCommitCrawer(object):
    def __init__(self, user_name, repo_name, token):
        self.url_temp = "https://api.github.com/repos/{}/{}/commits"
        self.limit_url = "https://api.github.com/rate_limit"
        self.user_name = user_name
        self.repo_name = repo_name

        self.SHAs = set()
        self.files = []

        self.headers = HEADERS
        self.headers['Authorization'] = "token " + token

    def check_remaining(self):
        logging.info(str(repr(self.headers)))
        text = self.get_html_content(self.limit_url)
        text_json = json.loads(text)
        self.rate_limit = text_json["rate"]["limit"]
        rate_remaining = text_json["rate"]["remaining"]
        logging.info("limit rate: {}".format(self.rate_limit))
        logging.info("remaining rate: {}".format(rate_remaining))
        return rate_remaining

    def get_html_content(self, url, retry=5, params=None):
        """直接获取url的内容，Exception由外部处理"""
        while retry > 0:
            try:
                r = requests.get(url, params, headers=self.headers, timeout=10)
                r.raise_for_status()
                r.encoding = r.apparent_encoding
                return r.text
            except requests.exceptions.ReadTimeout:
                logging.info("ReadTimeOut!")
                retry -= 1
            except requests.exceptions.ConnectionError:
                logging.info("ConnectionTimeOut!")
                retry -= 1
            except requests.exceptions.HTTPError as e:
                logging.info("HTTPError!, {}, {}".format(type(e), str(e)))
                retry -= 1
                if self.check_remaining() == 0:
                    print("No remaining rate! exit.")
                    return "[]" # if len(json.loads(get_html_content(url))) == 0: return

    def crawl_commits_sha(self):
        """爬指定repo的全部commit链接以供之后使用"""
        url = self.url_temp.format(self.user_name, self.repo_name)
        page = 1
        while True:
            try:
                logging.info("crawling page {}".format(page))
                html_content = self.get_html_content(url, params={'per_page': 100,
                                                                  'page': page})
                json_contents = json.loads(html_content)
                if len(json_contents) == 0:
                    break  # end of content
                for content in json_contents:
                    self.SHAs.add(content.get('sha'))
                page += 1
            except Exception as e:
                logging.critical("Fail!, {}, {}".format(type(e), str(e)))
                logging.info("length of shas: {}".format(len(self.SHAs)))
                break
            finally:
                print("End with page {}".format(page))

    def save_SHAs(self):
        filename = "{}-{}-SHAs.txt".format(self.user_name, self.repo_name)
        with open(filename, 'w+') as f:
            for sha in self.SHAs:
                f.write(sha + '\n')

    def load_SHAs(self, SHAs_file_path, limit=-1):
        logging.info("current SHAs number: {}".format(len(self.SHAs)))
        SHAs_temp = []
        with open(SHAs_file_path, 'r') as f:
            for line in f:
                SHAs_temp.append(line.strip(' \n'))
        self.SHAs = set(SHAs_temp[:limit])
        logging.info("after loaded SHAs number: {}".format(len(self.SHAs)))

    def crawl_commits_by_sha(self):
        """遍历链接池，获取commit的内容paste字段"""
        watched_shas = set()
        for sha in self.SHAs:
            logging.info("crawling SHA {}".format(sha))
            url = self.url_temp.format(self.user_name, self.repo_name) + '/' + sha
            try:
                html_content = self.get_html_content(url)
                json_contents = json.loads(html_content)
                if len(json_contents) == 0:
                    break
                for files in json_contents.get('files'):
                    if files.get('filename').endswith('.py'):
                        data = {'patch': files.get('patch'),
                                'sha': sha,
                                'status': files.get('status'),
                                'filename': files.get('filename')}
                        if len(json_contents.get('parents')) >= 1:
                            data['parents_sha'] = json_contents.get('parents')[0].get('sha')
                        else:
                            data['parents_sha'] = ""
                        self.files.append(data)
            except Exception as e:
                logging.critical("Fail!, {}, {}".format(type(e), str(e)))
                break
            finally:
                watched_shas.add(sha)
                print("End with length {}".format(len(self.files)))
        # self.SHAs = self.SHAs - watched_shas
        print("watched_shas: {}".format(len(watched_shas)))
        # self.save_SHAs()

    def save_files(self, filename):
        df = pd.DataFrame(data=self.files, columns=['patch', 'sha', 'status', 'filename', 'parents_sha'])
        print(df)
        df.to_pickle(f"{self.user_name}-{self.repo_name}-{filename}.tar.bz2")


class GithubCommentCrawer(object):
    def __init__(self, user_name, repo_name):
        self.url_temp = "https://api.github.com/repos/{}/{}/commits"
        self.user_name = user_name
        self.repo_name = repo_name

        self.headers = HEADERS
        self.per_page = 100
        self.SHAs = set()
        self.files = []
        self._init_user_agent()
        self._init_token()

    def _init_token(self):
        token = str(input("please input your token:\n"))
        logging.info("TOKEN: {}".format(token))
        self.headers['Authorization'] = "token " + token
        self._check_remaining()

    @log_tracer()
    def _init_user_agent(self):
        ua = UserAgent()
        self.headers["User-Agent"] = ua.random

    def _check_remaining(self):
        limit_url = "https://api.github.com/rate_limit"
        logging.info(str(repr(self.headers)))
        text = self.get_html_content(limit_url)
        text_json = json.loads(text)
        self.rate_limit = text_json["rate"]["limit"]
        rate_remaining = text_json["rate"]["remaining"]
        logging.info("limit rate: {}".format(self.rate_limit))
        logging.info("remaining rate: {}".format(rate_remaining))
        return rate_remaining

    # @make_interval(interval_second=1)
    def get_html_content(self, url, params=None):
        """直接获取url的内容，Exception由外部处理"""
        r = requests.get(url, params, headers=self.headers, timeout=10)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text

    def init_SHAs(self):
        """爬指定repo的全部commit链接以供之后使用"""
        url = self.url_temp.format(self.user_name, self.repo_name)
        page = 1
        while True:
            try:
                logging.info("crawling page {}".format(page))
                html_content = self.get_html_content(url, params={'per_page': self.per_page,
                                                                  'page': page})
                json_contents = json.loads(html_content)
                if len(json_contents) == 0:
                    break  # end of content
                for content in json_contents:
                    self.SHAs.add(content.get('sha'))
                page += 1
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
                logging.critical("Fail!, {}, {}".format(type(e), str(e)))
                logging.info("length of shas: {}".format(len(self.SHAs)))
                break
            finally:
                print("End with page {}".format(page))

    def init_files(self):
        """遍历链接池，获取commit的内容paste字段"""
        watched_shas = set()
        for sha in self.SHAs:
            logging.info("crawling SHA {}".format(sha))
            url = self.url_temp.format(self.user_name, self.repo_name) + '/' + sha
            try:
                html_content = self.get_html_content(url)
                json_contents = json.loads(html_content)
                for files in json_contents.get('files'):
                    if files.get('filename').endswith('.py'):
                        data = {'patch': files.get('patch'),
                                'sha': sha,
                                'status': files.get('status'),
                                'filename': files.get('filename')}
                        if len(json_contents.get('parents')) >= 1:
                            data['parents_sha'] = json_contents.get('parents')[0].get('sha')
                        else:
                            data['parents_sha'] = ""
                        self.files.append(data)
            except requests.exceptions.ReadTimeout:
                logging.info("ReadTimeOut!")
                continue
            except requests.exceptions.ConnectionError:
                logging.info("ConnectionTimeOut!")
                continue
            except requests.exceptions.HTTPError as e:
                logging.info("HTTPError!, {}, {}".format(type(e), str(e)))
                if self._check_remaining() == 0:
                    print("No remaining rate! exit.")
                    break
            except Exception as e:
                logging.critical("Fail!, {}, {}".format(type(e), str(e)))
            finally:
                watched_shas.add(sha)
                print("End with length {}".format(len(self.files)))
        self.SHAs = self.SHAs - watched_shas
        logging.info("watched_shas: {}".format(len(watched_shas)))
        self.save_SHAs()

    def save_SHAs(self):
        filename = "{}-{}-SHAs.txt".format(self.user_name, self.repo_name)
        with open(filename, 'w') as f:
            for sha in self.SHAs:
                f.write(sha + '\n')

    def load_SHAs(self, SHAs_file_path, limit=-1):
        logging.info("current SHAs number: {}".format(len(self.SHAs)))
        SHAs_temp = []
        with open(SHAs_file_path, 'r') as f:
            for line in f:
                SHAs_temp.append(line.strip(' \n'))
        self.SHAs = set(SHAs_temp[:limit])
        logging.info("after loaded SHAs number: {}".format(len(self.SHAs)))

    def text_to_file(self, text, sha):
        with open("{}-{}-files-{}.txt".format(self.user_name, self.repo_name, sha), 'w') as f:
            f.write(text)

    def save_files(self, filepath):
        df = pd.DataFrame(data=self.files, columns=['patch', 'sha', 'status', 'filename', 'parents_sha'])
        print(df)
        df.to_pickle(filepath)


def test_github_crawler():
    gc = GithubCommentCrawer(user_name='tensorflow', repo_name='tensorflow')
    gc.init_SHAs()
    gc.save_SHAs()

    gc.load_SHAs("tensorflow-tensorflow-shas.txt", limit=-1)
    gc.init_files()
    gc.save_files("tensorflow-tensorflow-SHAs.tar.bz2")

def test_github_crawer_new(i):
    config = configparser.ConfigParser()
    config.read(os.path.abspath('config.ini'))
    group = []
    for section in config.sections():
        di = {}
        for item in config.items(section):
            di[item[0]] = item[1]
        group.append(di)

    item = group[i]
    # item = group[1]
    # item = group[2]
    # item = group[3]
    gcc = GiuHubCommitCrawer(user_name=item['user'], repo_name=item['repo'], token=item['token'])
    gcc.load_SHAs(item['sha_file'])
    gcc.crawl_commits_by_sha()
    gcc.save_files(item['sha_file'].split('.')[0])

def test_ProcessPoolExecutor():
    with ProcessPoolExecutor() as pool:
        pool.map(test_github_crawer_new, [0,1,2,3,4,5,6,7])

def test_load_df():
    df = pd.read_pickle("tensorflow-tensorflow-SHAs.tar.bz2")
    print(df.iloc[0]['patch'])


def test_token():
    gc = GithubCommentCrawer('tensorflow', "tensorflow")

    gc.init_SHAs()
    gc.save_SHAs()

def test_end():
    gc = GithubCommentCrawer("tensorflow", "tensorflow")

    text = gc.get_html_content(url="https://api.github.com/repos/tensorflow/tensorflow/commits?per_page=100&page=1030")
    content = json.loads(text)
    print(len(content))

    text = gc.get_html_content(url="https://api.github.com/repos/tensorflow/tensorflow/commits?per_page=100&page=1031")
    content = json.loads(text)
    print(len(content))


def main():
    logging.basicConfig(
        level=logging.INFO
    )
    # test_token()
    # test_github_crawler()
    # test_load_df()
    # test_end()
    # test_github_crawer_new(3)
    test_ProcessPoolExecutor()


if __name__ == '__main__':
    main()
