# coding: utf8
from django.contrib import admin
# Register your models here.
from common.models import User, Commodity, WXUser


class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'channel', 'nick', 'client_ip', 'create_time', 'login_time', 'uuid', 'password', 'card']
    search_fields = ['id', 'nick', 'client_ip']
    list_filter = ['create_time']

admin.site.register(User, UserAdmin)


class CommodityAdmin(admin.ModelAdmin):
    list_display = ['item_id', 'bill_state', 'uin', 'channel', 'name', 'item_type', 'currency', 'amount', 'create_time']

admin.site.register(Commodity, CommodityAdmin)


class WXUserAdmin(admin.ModelAdmin):
    list_display = ['userid', 'native_id', 'create_time', 'appid']
    search_fields = ['native_id', 'userid']

admin.site.register(WXUser, WXUserAdmin)

