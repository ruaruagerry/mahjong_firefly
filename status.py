#!/usr/bin/env python
# coding: utf8
"""
查看服务器状态
@name: status.py 
@author: cbwfree
@create: 15/12/31 10:13
"""
import psutil, time, json


def GetProcess():
    """
    获取进程对象列表
    :return:
    """
    config = json.load(open("status.json", "r"))
    return [(psutil.Process(pid), name) for pid, name in config]


def ServerStatus(processes):
    """
    创建服务器状态数据
    :param processes:
    :return:
    """
    content = ["Name\tPID\tTIME\t\tCPU(%)\tMEM(%)\tUsed\t\tTHREADS\tSTATUS\t\tPATH"]
    for proc, name in processes:
        content.append("%s\t%s\t%s\t%s\t%s\t%s\t\t%s\t%s\t%s" % (
            name,
            proc.pid,
            formatRunTime(proc.create_time()),
            proc.cpu_percent(interval=None),
            float("%.2f" % proc.memory_percent()),
            bytes2human(proc.memory_info()[0]),
            proc.num_threads(),
            proc.status() + ("\t" if proc.status() == "running" else ""),
            proc.cwd()
        ))
    return "\n".join(content)


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


if __name__ == "__main__":
    try:
        import curses
    except:
        curses = None
    process = GetProcess()
    if curses:
        stdscr = curses.initscr()
        curses.start_color()
        # 设置显示颜色为绿色
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        # 关闭屏幕回显
        curses.noecho()
        try:
            while True:
                stdscr.addstr(0, 0, ServerStatus(process), curses.color_pair(1))
                stdscr.refresh()
                time.sleep(1)
        except:
            pass
        finally:
            curses.nocbreak()
            curses.echo()
            curses.endwin()
    else:
        ServerStatus(process)
        time.sleep(1)
    # 未安装curses和退出时显示
    print ServerStatus(process)

