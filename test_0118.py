#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/1/18 12:04
# @Author  : Zyt
# @Site    : 
# @File    : test_0118.py
# @Software: PyCharm

import os
import configparser
# import requests
# from requests.adapters import HTTPAdapter
# from requests.packages.urllib3.util.retry import Retry
#
# def test_requests_get_retry():
#     s = requests.Session()
#     retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
#     s.mount('http://', HTTPAdapter(max_retries=retries))
#     try:
#         url = "https://api.github.com/rate_limit"
#         requests.get(url)
#     except

def test_split_sha_files(filename, filename1, filename2):
    contents = []
    with open(filename, 'rt') as f:
        for line in f:
            contents.append(line)
    split_pivot = len(contents) // 2
    with open(filename1, 'wt') as f:
        for line in contents[:split_pivot]:
            f.write(line)
    with open(filename2, 'wt') as f:
        for line in contents[split_pivot:]:
            f.write(line)


def test_configparser():
    config = configparser.ConfigParser()
    config.read(os.path.abspath('config.ini'))
    # print(config.sections()) #所有section的名称
    # print(config.options('config1')) # section的字段名称
    # print(config.items('config1')) # 以元组的形式输出字段名和字段值
    # print(config.get('config1', 'user'))

    group = []
    for section in config.sections():
        di = {}
        for item in config.items(section):
            di[item[0]] = item[1]
            # print(item)
        group.append(di)
    print(repr(group))

def test_json_accept_none():
    import json
    print(len(json.loads("[]")))

def test_load_txt_to_head10(name, prefix, count=10):
    temp = []
    with open(f"{name}.txt", 'rt') as f:
        for line in f:
            temp.append(line)
            count -= 1
            if count <= 0:
                break

    with open(f"{prefix}_{name}.txt", 'wt') as f:
        for line in temp:
            f.write(line)

    with open(f"{prefix}_{name}.txt", 'rt') as f:
        for line in f:
            print(line)

def test_split_dot():
    print('sha_files.txt'.split('.')[0])

def main():
    # test_configparser()
    test_split_sha_files("sha1.txt", "split_sha1.txt", "split_sha2.txt")
    test_split_sha_files("sha2.txt", "split_sha3.txt", "split_sha4.txt")
    test_split_sha_files("sha3.txt", "split_sha5.txt", "split_sha6.txt")
    test_split_sha_files("sha4.txt", "split_sha7.txt", "split_sha8.txt")
    # test_requests_get_retry()
    # test_json_accept_none()
    # test_load_txt_to_head10(name='sha1', prefix='tiny', count=10)
    # test_load_txt_to_head10(name='sha2', prefix='tiny', count=10)
    # test_load_txt_to_head10(name='sha3', prefix='tiny', count=10)
    # test_load_txt_to_head10(name='sha4', prefix='tiny', count=10)
    # test_split_dot()


if __name__ == '__main__':
    main()