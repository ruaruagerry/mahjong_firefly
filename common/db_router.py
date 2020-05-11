# -*- coding: utf-8 -*-


class DBRouter(object):

    def db_for_read(self, model, **hints):
        return self._app_router(model)

    def db_for_write(self, model, **hints):
        return self._app_router(model)

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == obj2._meta.app_label:
            return True

    def allow_syncdb(self, db, model):
        return self._app_router(model) == db

    def _app_router(self, model):
        if model._meta.model_name == 'deskrecord':
            return 'other'

        return 'default'
