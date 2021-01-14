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

HEADERS = {"User-Agent" : "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
  "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
  "Accept-Language" : "en-us",
  "Connection" : "keep-alive",
  "Accept-Charset" : "GB2312,utf-8;q=0.7,*;q=0.7"}


def make_interval(interval_second=1):
    """装饰器，每次执行之前停顿interval_second秒"""
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
        self.headers["User-Agent"] = UserAgent().random
        logging.info(self.headers)
        self.per_page = 1000
        self.shas = set()
        self.files = []

    @make_interval(interval_second=6)
    def get_html_content(self, url, params):
        """直接获取url的内容，Exception由外部处理"""
        r = requests.get(url, params, timeout=6)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text

    def init_shas(self):
        """爬指定repo的全部commit链接以供之后使用"""
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
        """遍历链接池，获取commit的内容paste字段"""
        for sha in self.shas:
            url = self.url_temp.format(self.user_name, self.repo_name) + '/' + sha
            try:
                html_content = self.get_html_content(url, params={'headers': self.headers})
                json_contents = json.loads(html_content)
                for files in json_contents.get('files'):
                    if files.get('filename').endswith('.py'):
                        self.files.append({'patch':files.get('patch'),
                                           'sha':sha,
                                           'parents_sha':json_contents.get('parents')[0].get('sha')})
            except requests.exceptions.ReadTimeout:
                logging.info("ReadTimeOut!")
            except requests.exceptions.ConnectionError:
                logging.info("ConnectionTimeOut!")
            except requests.exceptions.HTTPError as e:
                logging.info("HTTPError!", type(e), str(e))
                time.sleep(55)
            except Exception as e:
                logging.info("Fail!", type(e), str(e))
            finally:
                print("End with length {}".format(len(self.files)))

    def save_shas(self):
        with open("{}-{}-shas.txt".format(self.user_name, self.repo_name), 'w') as f:
            for sha in self.shas:
                f.write(sha + '\n')

    def load_shas(self, shas_file_path, limit=100):
        logging.info("current shas number: {}".format(len(self.shas)))
        shas_temp = []
        with open(shas_file_path, 'r') as f:
            for line in f:
                shas_temp.append(line.strip(' \n'))
        self.shas = set(shas_temp[:limit])
        logging.info("after loaded shas number: {}".format(len(self.shas)))

    def save_file(self, text, sha):
        with open("{}-{}-files-{}.txt".format(self.user_name, self.repo_name, sha), 'w') as f:
            f.write(text)

    def save_files(self, filepath):
        df = pd.DataFrame(data=self.files, columns=['patch', 'sha', 'parents_sha'])
        print(df)
        df.to_pickle(filepath)


def test_github_crawler():
    gc = GithubCommentCrawer(user_name='tensorflow', repo_name='tensorflow')
    # gc.init_shas()
    # gc.save_shas()

    gc.load_shas("tensorflow-tensorflow-shas.txt", limit=10)
    gc.init_files()
    gc.save_files("tensorflow-tensorflow-shas.tar.bz2")


def main():
    logging.basicConfig(
        level=logging.INFO
    )
    test_github_crawler()


if __name__ == '__main__':
    main()