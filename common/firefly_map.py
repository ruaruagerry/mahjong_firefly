# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 和firefly相关需要全局保存的信息都放这里
"""

from log import logger


def singleton(cls, *args, **kw):
    instances = {}
    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]
    return _singleton


# 记住：singleton只在单进程内有效
# 把它放在transfer里面处理吧，这样其它模块就都不需要关心这个问题了
@singleton
class FireflyMap(object):
    """
    user_id和conn_id的对应关系
    """
    user_conn_map = None

    def __init__(self):
        self.user_conn_map = {}

    def attach_user_conn(self, user_id, conn_id):
        if user_id in self.user_conn_map:
            # logger.critical("user has exist, login in otherwhere")
            # 被顶了首先刷新链接，然后把老的链接断掉
            # 2017-3-28 这里有个思想，如果链接是老链接，就复用老的链接
            old_conn_id = self.user_conn_map[user_id]
            self.user_conn_map[user_id] = conn_id
            return False, old_conn_id
        self.user_conn_map[user_id] = conn_id
        return True, -1

    def detach_user_conn(self, user_id):
        if user_id not in self.user_conn_map:
            logger.critical("user not exist")
            return False
        self.user_conn_map.pop(user_id)
        return True

    def get_conn_by_user(self, user_id):
        return self.user_conn_map.get(user_id, None)

    # dict结构原因，必须要遍历一遍
    def get_user_by_conn(self, conn_id):
        for k, v in self.user_conn_map.items():
            if v == conn_id:
                return k
        return None


@singleton
class JsonRegisterObj(object):
    """
    使用json.dumps/loads之前来这里注册一下
    """
    registered_module_map = None

    def __init__(self):
        self.registered_module_map = {}

    def register_module(self, obj_class_list):
        for obj_class in obj_class_list:
            class_name = obj_class.__name__
            if class_name in self.registered_module_map:
                return
            self.registered_module_map[class_name] = obj_class

    def delete_module(self, obj_class):
        class_name = obj_class.__name__
        if class_name not in self.registered_list:
            return
        self.registered_module_map.pop(class_name)

    def get_registered_dict(self, class_name=None):
        if class_name:
            return self.registered_module_map.get(class_name, None)
        else:
            return self.registered_module_map


