# coding: utf8
import sys
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mjango.settings")
# 日志模块这里初始化，方便别的地方引用，这里一定要写上，不然gateway打不出日志
from django.conf import settings
settings.BASE_DIR
from firefly.server.server import FFServer
from common.bus_func import module_register, signal_register
from ProcessHandler.lib.arbiter import Arbiter


class Darkness(Arbiter):
    name = None

    def __init__(self, name):
        super(Darkness, self).__init__(None, section=name)
        self.name = name

    # 重载worker_class
    def worker_class(self):
        import initialize
        server = FFServer()
        server.set_name(self.name)
        server.set_config()

        if name not in ['_gateway_', '_transfer_']:
            module_register()
            signal_register()

        return server.start()
        # return server


if os.name != 'nt' and os.name != 'posix':
    from twisted.internet import epollreactor
    epollreactor.install()

if __name__ == "__main__":
    args = sys.argv
    name = None
    if len(args) > 1:
        name = args[1]
    else:
        raise ValueError

    app = Darkness(name)
    app.run()






