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
import configparser
import difflib
from Utils import HEADERS, make_interval, log_tracer
from Utils import delete_comment_and_docstrings
from Utils import get_diff_file
from Utils import b2t, timethis



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


class GitHubCompare(object):
    def __init__(self, user, repo, pickle_filename, token, pid=1):
        self.user = user
        self.repo = repo
        df = pd.read_pickle(pickle_filename)
        df = df[df['status'] == 'modified']  # commit有四个类型，只有modified是前后变动的
        self.df = df.reset_index(drop=True)  # 重设index
        self.size = len(self.df)
        print(self.df)

        self.token = token

        self.contents_template = "https://api.github.com/repos/tensorflow/tensorflow/contents/{filename}?ref={sha}"
        self.limit_url = "https://api.github.com/rate_limit"  # 查询还剩多少次访问github的url

        self.headers = HEADERS
        self.headers['Authorization'] = "token " + token

        self.minus_lines = []  # 爬到的所有单行注释。后来想想没用，因为我们需要上下文信息。

        self.pid = pid # 进程编号，随便起的数字名称。

    def check_remaining(self):
        """查询还剩多少次访问github的机会，一个账号一个小时允许5000次
        返回剩余次数"""
        text = self.get_html_content(self.limit_url)
        text_json = json.loads(text)
        self.rate_limit = text_json["rate"]["limit"]
        rate_remaining = text_json["rate"]["remaining"]
        print("process {} limit rate: {}".format(self.pid, self.rate_limit))
        print("process {} remaining rate: {}".format(self.pid, rate_remaining))
        return rate_remaining

    def get_html_content(self, url, retry=5, params=None):
        """直接获取url的内容，出现错误就最多重试5次
        如果没有剩余查询次数，就返回中括号字符串，因为返回值要输入json，所以不能直接返回空值"""
        while retry > 0:
            try:
                logging.info(f"process {self.pid} Crawing {url}")
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
                    return "[]"  # if len(json.loads(get_html_content(url))) == 0: return

    def get_file_content(self, filename, sha):
        """给定文件目录和sha，爬取对应文件的base64编码后的内容"""
        url = self.contents_template.format(filename=filename, sha=sha)
        text = self.get_html_content(url=url)
        content = json.loads(text)
        if len(content) == 0:
            return ""
        return content.get('content')

    @timethis
    def traverse_df_add_columns(self):
        """增加两列，用于储存爬取完毕的commit文件和父提交文件"""
        origin_content = []
        for index, row in self.df.iterrows():
            print(f"process {self.pid} origin content crarwing {index / self.size * 100}%")
            origin_content.append(self.get_file_content(row['filename'], row['sha']))
        self.df['origin_content'] = origin_content

        # self.df['origin_content'] = self.df.apply(
        #     lambda row: self.get_file_content(row['filename'], row['sha']),
        #     axis=1)

        parent_content = []
        for index, row in self.df.iterrows():
            print(f"process {self.pid} parent content crarwing {index / self.size * 100}%")
            parent_content.append(self.get_file_content(row['filename'], row['parents_sha']))
        self.df['parent_content'] = parent_content

        # self.df['parent_content'] = self.df.apply(
        #     lambda row: self.get_file_content(row['filename'], row['parents_sha']),
        #     axis=1)
        self.df['pure_code'] = self.df.apply(
            lambda row: get_diff_file(b2t(row['parent_content']), b2t(row['origin_content'])),
            axis=1)

    def save_df(self, filename):
        self.df.to_pickle(f"{filename}.tar.gz")

    ##########################

    def get_diff(self, origin_file, parent_file):
        """比较输入的两份文本文件的差距行，把差距储存到self.minus_lines里面
        这种做法忽略了上下文，因此不可取"""
        origin_file_lines = origin_file.splitlines()
        parent_file_lines = parent_file.splitlines()
        d = difflib.Differ()
        diff = d.compare(parent_file_lines, origin_file_lines)
        minus_lines = []
        for line in list(diff):
            if line.startswith('-') and len(line) > 2:  # 排除空行，因为空行只包括两个符号：减号与空格
                minus_lines.append(line.lstrip('- '))
        return minus_lines

    def traverse_df_find_minus(self):
        for index, row in self.df.iterrows():
            origin_file = self.get_file(filename=row['filename'], sha=row['sha'])
            parent_file = self.get_file(filename=row['filename'], sha=row['parents_sha'])
            self.minus_lines.extend(self.get_diff(origin_file, parent_file))
            logging.info("total minus_lines: {}".format(len(self.minus_lines)))

    def save_minus_file(self, filename):
        with open(f"{filename}.txt", 'wt') as f:
            for line in self.minus_lines:
                f.write(line + '\n')


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

def test_github_compare(i):
    config = configparser.ConfigParser()
    config.read(os.path.abspath('config_compare.ini'))
    group = []
    for section in config.sections():
        di = {}
        for item in config.items(section):
            di[item[0]] = item[1]
        group.append(di)

    item = group[i]
    gc = GitHubCompare(pid=i, user=item['user'], repo=item['repo'], token=item['token'], pickle_filename=item['pickle_filename'])
    gc.traverse_df_add_columns()
    gc.save_df(item['pickle_filename'].split('.')[0])

def test_multiprocessing_compare():
    with ProcessPoolExecutor() as pool:
        pool.map(test_github_compare, [0,1,2,3,4,5,6,7])




def main():
    logging.basicConfig(
        filename="crawl.log",
        level=logging.INFO
    )
    # test_token()
    # test_github_crawler()
    # test_load_df()
    # test_end()
    # test_github_crawer_new(3)
    # test_ProcessPoolExecutor()
    test_multiprocessing_compare()


if __name__ == '__main__':
    main()
