# -*- coding: utf-8 -*-

"""
WSGI config for mjango project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mjango.settings")

from common.bridge import Bridge
from django.core.wsgi import get_wsgi_application
from common.log import logger
from common.bus_func import module_register


application = get_wsgi_application()
module_register()
# Bridge().get_connect()

import threading
import time


def web_connect():
    Bridge(pro_name='web_server')

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mjango.settings")
    from django.conf import settings
    settings.BASE_DIR
    while 1:
        # 应该会有性能问题，先写着，到时候看看
        if Bridge().get_status():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                Bridge().close_connect()
                break
            except:
                logger.error('error\n', exc_info=True)
                Bridge().close_connect()
                break
        else:
            Bridge().get_connect()


# -------------------------------------------------------------------------
# 之前给target赋值时老是func()，结果悲剧了，还是要注意一下，只传fun_name，不要带括号
# -------------------------------------------------------------------------
bridge_t = threading.Thread(target=web_connect, name='web_connect')
bridge_t.setDaemon(True)
bridge_t.start()


