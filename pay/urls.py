# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    # unity pay
    url(r'^pay_code/$', 'pay.views.wx_code'),
    url(r'^only_pay/$', 'pay.views.wx_pay_test'),
    url(r'^only_pay/cb$', 'pay.views.wx_pay_test_cb'),
)
