#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/1/18 12:15
# @Author  : Zyt
# @Site    : 
# @File    : Utils.py.py
# @Software: PyCharm

from functools import wraps
import time
import token
import tokenize
import logging
import difflib
from io import BytesIO
import base64
from time import process_time

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

def delete_comment_and_docstrings(source):
    modified = ""
    prev_toktype = token.INDENT
    first_line = None
    last_lineno = -1
    last_col = 0
#     tokgen = tokenize.generate_tokens(source.readline)
    tokens_iterator = tokenize.tokenize(BytesIO(source.encode('utf-8')).readline)
    for toktype, ttext, (slineno, scol), (elineno, ecol), ltext in tokens_iterator:
        if slineno > last_lineno:
            last_col = 0
        if scol > last_col:
            modified = modified + " " * (scol - last_col)
        if toktype == token.STRING and (prev_toktype == token.INDENT or prev_toktype == token.NEWLINE):
            # Docstring
            pass
        elif toktype == tokenize.COMMENT:
            # Comment
            pass
        else:
            modified = modified + ttext
        prev_toktype = toktype
        last_col = ecol
        last_lineno = elineno
    return modified

def get_diff_file(origin_file, modified_file):
    """比较输入的两份文本的差距行，对"""
    origin_file = delete_comment_and_docstrings(origin_file)
    modified_file = delete_comment_and_docstrings(modified_file)

    origin_lines = origin_file.splitlines()
    modified_lines = modified_file.splitlines()
    d = difflib.Differ()
    diff = d.compare(origin_lines, modified_lines)

    minus_lines = []
    for line in list(diff):
        if len(line.lstrip(' ')) == 0 or len(line.lstrip('- ')) == 0 or line.startswith('+') or line.startswith(
                '?'):
            continue
        if line.startswith('-'):
            minus_lines.append('#' + line[2:])
        else:
            minus_lines.append(line[2:])
    return '\n'.join(minus_lines)

def b2t(base64_text):
    """给定文件目录和sha，爬取指定文件的内容"""
    decoded_content = base64.b64decode(base64_text).decode('utf8')
    return decoded_content

def timethis(func):
    """计时函数装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = process_time()
        r = func(*args, **kwargs)
        end = process_time()
        print('{} executing time: {}s'.format(func.__name__, end - start))
        return r
    return wrapper