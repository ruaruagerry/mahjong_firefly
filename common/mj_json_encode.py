# coding: utf8
import json
import copy
from common.log import logger
from firefly_map import JsonRegisterObj


# 暂时只能封成这蠢样儿了
def json_encoder_analyze(inst):
    # 如果inst是空值就返回空
    if not inst:
        return None

    tmp_dict = {}
    # 这个保留着吧，解析的时候做个标记
    tmp_dict['pk'] = inst.__class__.__name__
    tmp_dict.update(inst.__dict__)
    # logger.debug('tmp_dict:%s', tmp_dict)
    register_dict = JsonRegisterObj().get_registered_dict()

    for k, v in inst.__dict__.items():
        # 这两类干掉吧
        if k == 'r_obj' or k == 'lock_obj':
            tmp_dict.pop(k)
        # 列表也要检查一下
        # if isinstance(v, list) and v and v[0].__class__.__name__ in register_dict:
        if isinstance(v, list) and v:
            for i, it_inst in enumerate(v):
                if it_inst and it_inst.__class__.__name__ in register_dict:
                    tmp_dict[k][i] = json_encoder_analyze(it_inst)
        else:
            if v.__class__.__name__ in register_dict:
                tmp_dict[k] = json_encoder_analyze(v)

    # logger.debug('tmp_dict:%s', tmp_dict)
    return tmp_dict


def json_encoder(inst):
    if not inst:
        return
    return json.dumps(json_encoder_analyze(inst))


# 有点不敢相信竟然这样就可以了
# 所以说嘛，还是要改的
def json_decoder_analyse(json_result):
    tmp_inst = None
    register_dict = JsonRegisterObj().get_registered_dict()
    # logger.debug('register_dict:%s', register_dict)

    if isinstance(json_result, dict):
        for k, v in json_result.items():
            if isinstance(v, dict) and 'pk' in v:
                json_result[k] = json_decoder_analyse(v)
            if isinstance(v, list) and v:
                for i, it_dict in enumerate(v):
                    # 再加一个限制，是字典才进去，因为只有是字典才有可能是module中的object
                    if isinstance(it_dict, dict):
                        v[i] = json_decoder_analyse(it_dict)

    # 这里走重复了，去掉吧
    # if isinstance(json_result, list) and json_result:
    #     for i, it_dict in enumerate(json_result):
    #         if isinstance(it_dict, dict) and 'pk' in it_dict:
    #             json_result[i] = json_decoder_analyse(it_dict)
            # if isinstance(it_dict, list) and it_dict:
            #     for j, it_dict_tmp in enumerate(it_dict):
            #         it_dict[j] = json_decoder_analyse(it_dict_tmp)

    if isinstance(json_result, dict) and 'pk' in json_result:
        pk_name = json_result.pop('pk')

        if isinstance(pk_name, unicode):
            pk_name = pk_name.encode('utf8')

        if pk_name in register_dict:
            # logger.debug('enter, pk_name:%s', pk_name)
            tmp_inst = register_dict[pk_name]()
            # logger.debug('json_result:%s', json_result)
            tmp_inst.__dict__ = json_result

    # logger.debug('tmp_inst:%s', tmp_inst)
    return tmp_inst


def json_decoder(json_str):
    # logger.debug('json_str:%s', json_str)
    if not json_str:
        return
    return json_decoder_analyse(json.loads(json_str))

