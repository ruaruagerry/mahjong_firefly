# -*- coding: utf-8 -*-

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 后台h5表格模板
"""

from django import forms


class DeskQueryForm(forms.Form):
    desk_id = forms.IntegerField(label=u'桌子ID')


class ModifyRoomCardForm(forms.Form):
    user_id = forms.IntegerField(label=u'用户ID')
    room_card_num = forms.IntegerField(label=u'修改房卡数(请输入差值，正数在原基础上加，负数在原基础上减)')
    remark = forms.CharField(label=u'备注(必填)')


class BillBroadcast(forms.Form):
    content = forms.CharField(label=u'公告内容', widget=forms.Textarea)

