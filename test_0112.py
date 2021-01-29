#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/1/12 9:28
# @Author  : Zyt
# @Site    : 
# @File    : test_0112.py
# @Software: PyCharm

from github import Github
import pandas as pd
import base64

def test_github_repo():
    g = Github()
    repo = g.get_repo("tensorflow/tensorflow")
    commit = repo.get_commit(sha='511c27580ad8d2eebc19eb9e2d3dc68ce42b7aaa')
    print(type(commit), len(commit))

def test_size():
    df = pd.read_pickle(r'C:/Users/zyt/Desktop/df_0.tar.gz')
    # df = df[:10]
    # print(df.iloc[0]['pure_code'])
    # decoded_content = base64.b64decode(df.iloc[0]['parent_content']).decode('utf8')
    # print(decoded_content)
    count = 0
    for index, row in df.iterrows():
        for line in row['pure_code'].splitlines():
            if line.startswith('#'):
                count += 1
    print(count)


def main():
    # test_github_repo()
    test_size()

if __name__ == '__main__':
    main()