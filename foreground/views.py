# -*- coding: utf-8 -*-
import os
from common import error_contrast
from common.log import logger
import config
from common.bus_func import is_app_crime, rest_rsp_json
from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse, HttpResponseNotFound


def ts_test(request):
    # rsptmp = WsProtoTest()
    # rsptmp.op_int = 1
    # rsptmp.re_int.extend([1,2,3,4])
    # rsptmp.op_str = '1234'
    # rsptmp.op_msg.ms_op_int = 1
    # for i in range(0,4):
    #     evt_list = rsptmp.re_msg.add()
    #     evt_list.ms_op_int = i
    # user = RedisUserMgr().get_user(1)
    # rsp = UserRoomCardChange()
    # rsp.room_card = user.card
    # rsp = rsp.SerializeToString()
    # logger.debug('rsp: %s', rsp.encode('utf-8'))
    # logger.debug('req:%s', req)
    # bridge_to_users(user.uin, 111, rsp)
    # rsptmp = rsptmp.SerializeToString()
    # bridge_to_other_game(1002, rsptmp)

    return HttpResponse('hope OK')


# 获取服务器配置
def pre_login_config(request):
    uin = request.REQUEST.get('uin')
    channel = request.GET.get('channel')
    version = request.GET.get('version', 0)

    if uin is None:
        return rest_rsp_json(
            ret=error_contrast.ERROR_INVALID_PARAMS,
            error="invalid http request. Need reason? Don't tell you!!!",
        )

    ret_dict = dict(
        ret=0,
        uin=str(uin),
    )

    error_code_list = []
    for code_conf in error_contrast.ERROR_CODE_LIST:
        error_code_list.append(dict(
            code=code_conf['id'],
            desc=code_conf['desc'],
        ))
    ret_dict.update(error_code_list=error_code_list)

    host = request.get_host().split(':')[0]
    # host = request.get_host()
    server_net_pair = [host, config.GATEWAY_WS_PORT]
    ret_dict['server_net_pair'] = server_net_pair

    try:
        version = int(version)
    except Exception, e:
        logger.error('error : %s', e.message)

    # 过申状态下返回域名
    ret_dict['current_censoring'] = False
    if is_app_crime(channel, version):
        ret_dict['current_censoring'] = True

    return rest_rsp_json(**ret_dict)


def get_source_address(request):
    """
    是否需要热更新
    """
    ret_dict = dict(
        code_url="http://mahjong.wzdexian.com/download/code/{0}/game_code_{0}.zip".format(config.APP_UPDATE_VERSION),
        update_url="http://mahjong.wzdexian.com/download/resource/{0}".format(config.APP_UPDATE_VERSION),
    )

    return rest_rsp_json(**ret_dict)


def download_file(request):
    # 定义文件分块下载函数
    def file_iterator(file_name, chunk_size=512):
        with open(file_name, 'rb') as f:  # 如果不加‘rb’以二进制方式打开，文件流中遇到特殊字符会终止下载，下载下来的文件不完整
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    path_root = "/data/release" + request.path_info
    file_name = request.path_info.split('/')
    # logger.debug('path_root:%s, file_name:%s', path_root, file_name[-1])
    response = StreamingHttpResponse(file_iterator(path_root))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="{0}"'.format(
        file_name[-1])  # 此处kwargs['fname']是要下载的文件的文件名称
    return response


def bug_view(request):
    logger.error("来了来了,forward:%s, real:%s, agent:%s", request.META.get('HTTP_X_FORWARDED_FOR'), request.META.get('HTTP_X_REAL_IP'), request.META.get('HTTP_USER_AGENT'))
    return HttpResponse(u'accesslog看到它好多天了，一直没空弄，20170804晚上抽空修掉')
    # return HttpResponseNotFound


def ws_test(request):

    return render(request, "websocket.html")
    # def render(self, request):
    #     with open("demo/websocket.html", "r") as f:
    #         content = f.read()
    #         f.close()
    #     return ToUtf8(content)

