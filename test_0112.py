#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/1/12 9:28
# @Author  : Zyt
# @Site    : 
# @File    : test_0112.py
# @Software: PyCharm

from github import Github

def test_github_repo():
    g = Github()
    repo = g.get_repo("tensorflow/tensorflow")
    commit = repo.get_commit(sha='511c27580ad8d2eebc19eb9e2d3dc68ce42b7aaa')
    print(type(commit), len(commit))


def main():
    test_github_repo()

if __name__ == '__main__':
    main()