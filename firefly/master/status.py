# coding: utf8
"""
服务器状态
@name: status.py 
@author: cbwfree
@create: 15/12/31 10:13
"""
import psutil, os, time
from firefly.server.globalobject import GlobalObject


def getServerInfo():
    """
    获取服务器状态
    :return:
    """
    process = psutil.Process(os.getpid())
    result = {
        'pid': process.pid,
        'cwd': process.cwd(),
        'children': {}
    }
    process.cpu_percent(interval=None)
    for proc in process.children():
        proc.cpu_percent(interval=None)
        result['children'][proc.pid] = {
            'pid': proc.pid,
            'cwd': proc.cwd()
        }
    time.sleep(1)
    result['cpu'] = process.cpu_percent(interval=None)
    result['mem'] = process.memory_percent()
    result['used'] = bytes2human(process.memory_info()[0])
    result['create'] = process.create_time()
    result['status'] = process.status()
    result['threads'] = process.num_threads()
    for proc in process.children():
        result['children'][proc.pid]['cpu'] = proc.cpu_percent(interval=None)
        result['children'][proc.pid]['mem'] = proc.memory_percent()
        result['children'][proc.pid]['used'] = bytes2human(proc.memory_info()[0])
        result['children'][proc.pid]['create'] = proc.create_time()
        result['children'][proc.pid]['status'] = proc.status()
        result['children'][proc.pid]['threads'] = proc.num_threads()
    return result


def buildConsoleResult(info):
    """
    构建控制台显示结果
    :param info:
    :return:
    """
    process = dict([(proc.transport.pid, name) for name, proc in GlobalObject().server.process.protocols.items()])
    content = [
        "Name\tPID\tTIME\t\tCPU(%)\tMEM(%)\tUsed\t\tTHREADS\tSTATUS\t\tPATH",
        "%s\t%s\t%s\t%s\t%s\t%s\t\t%s\t%s\t%s" % (
            "master",
            info.get("pid"),
            formatRunTime(info.get("create")),
            info.get("cpu"),
            float("%.2f" % info.get("mem")),
            info.get("used"),
            info.get("threads"),
            info.get("status") + ("\t" if info.get("status") == "running" else ""),
            info.get("cwd")
        )
    ]
    for pid, proc in info.get("children", {}).items():
        child = "%s\t%s\t%s\t%s\t%s\t%s\t\t%s\t%s\t%s"  % (
            process.get(pid),
            pid,
            formatRunTime(proc.get("create")),
            proc.get("cpu"),
            float("%.2f" % proc.get("mem")),
            proc.get("used"),
            proc.get("threads"),
            proc.get("status") + ("\t" if proc.get("status") == "running" else ""),
            proc.get("cwd")
        )
        content.append(child)
    return "\n".join(content) + "\n"


def formatRunTime(create):
    """
    格式化运行时间
    :param create:
    :return:
    """
    diff = int((time.time() - create))
    hour = diff // 3600
    diff-= hour * 3600
    minutes = diff // 60
    diff-= minutes * 60
    hour = str(hour)
    hour = "0" * (2 - len(hour)) + hour
    minutes = str(minutes)
    minutes = "0" * (2 - len(minutes)) + minutes
    diff = str(diff)
    diff = "0" * (2 - len(diff)) + diff
    return "%s:%s:%s%s" % (hour, minutes, diff, " " * (4 - len(hour)))


def bytes2human(n):
    """
    转换字节单位
    :param n:
    :return:
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.2f%s' % (value, s)
    return '%.2fB' % n


def float2percent(x, y):
    """
    浮点数转百分比
    :param x:
    :param y:
    :return:
    """
    return float("%.2f" % (float(x) / float(y) * 100))