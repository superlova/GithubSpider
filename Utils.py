#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/1/18 12:15
# @Author  : Zyt
# @Site    : 
# @File    : Utils.py.py
# @Software: PyCharm

from functools import wraps
import time
import logging

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