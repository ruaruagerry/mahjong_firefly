# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : redis句柄
"""

from redis import StrictRedis
import config

rds = StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)
rds_tmp = StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB_TMP)
