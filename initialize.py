# coding:utf8
"""
初始化配置文件
"""
from firefly.server.config import Config, ServerConfig

# =============   配置服务器信息   ================
# 设置master信息
Config().setMaster(
    roothost="127.0.0.1",
    rootport=9999,
    webport=9998
)
# 设置memcached缓存
Config().setCache({
    'urls': ["127.0.0.1:11211"],
    'hostname': "firefly"
})
# 设置数据库连接
Config().setDb(
    db="db_name",
    host="127.0.0.1",
    port=3306,
    user="root",
    passwd="123456",
    charset="utf8",
    conv={10: str, 246: float}
)


# =============   设置服务器节点   ================
# Net节点
# 还是改叫Gateway节点吧，习惯一点
node = ServerConfig("_gateway_")
# node.set_log()
node.set_net(20000)
# node.set_web(22000)
node.set_ws(21000)
node.set_remote("_transfer_")
Config().addServer(node)

# Gate节点
# 现在叫Transfer节点，主要负责转发消息
node = ServerConfig("_transfer_")
# node.set_log()
# node.set_db()
# node.set_reload()
node.set_root(20001)
# node.set_remote("share", "middle", "logs")
Config().addServer(node)

# Sync节点
# node = ServerConfig("sync")
# node.set_log()
# node.set_db()
# node.set_mem()
# Config().addServer(node)

# Auth节点
node = ServerConfig("_auth_")
# node.set_log()
# node.set_db()
# node.set_mem()
# node.set_reload()
node.set_remote("_transfer_")
Config().addServer(node)

# Hall节点
node = ServerConfig("_hall_")
# node.set_log()
# node.set_db()
# node.set_mem()
# node.set_reload()
node.set_remote("_transfer_")
Config().addServer(node)

# Play节点
node = ServerConfig("_play_")
# node.set_log()
# node.set_db()
# node.set_mem()
# node.set_reload()
node.set_remote("_transfer_")
Config().addServer(node)

# Common节点
node = ServerConfig("_common_")
# node.set_log()
# node.set_db()
# node.set_mem()
# node.set_reload()
node.set_remote("_transfer_")
Config().addServer(node)