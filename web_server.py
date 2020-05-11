# -*- coding: utf-8 -*-
import pymysql
# django中使用mysql orm必需初始化
pymysql.install_as_MySQLdb()

# web_server的gunicorn配置
proc_name = 'mahjong_web'
worker_class = 'gevent' # gevent异步 sync同步
bind = ['0.0.0.0:32999']
workers = 2
timeout = 1800