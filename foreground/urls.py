# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(r'^pull/ti7_login_config', 'foreground.views.pre_login_config'),
    url(r'^ws_test', 'foreground.views.ws_test'),
    url(r'^transfer_to_firefly', 'foreground.views.ts_test'),
    url(r'^update/ti7_address', 'foreground.views.get_source_address'),
    url(r'^ti7_download', 'foreground.views.download_file'),
    url(r'^accounts/login/$', 'foreground.views.bug_view'),
)
