# coding: utf8
"""
启动服务器
@name: startmaster.py 
@author: cbwfree
@create: 15/12/29 20:02
"""
import sys, os
# sys.path.insert(0, '../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mjango.settings")
# from django.conf import settings
# settings.BASE_DIR
from firefly.master.master import Master, MULTI_SERVER_MODE
from twisted.application import service
from firefly.server.config import Config, ServerConfig
# 注释掉这一行单独启动master进程，然后通过appmain可单独控制子模块，这样就能放到superviosr里面去了
# import initialize

APP_NAME = "firefly"
APP_SCRIPT = "appmain.py"

# 创建Application容器
application = service.Application(APP_NAME)

# 创建守护进程
master = Master()
master.set_script(APP_SCRIPT)
master.set_mode(MULTI_SERVER_MODE)              # 设置启动模式
master.start(application)                       # 启动守护进程

