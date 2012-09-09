#!/usr/bin/python
#coding=utf-8

import sys
import time
import ConfigParser

import psutil 
from daemon import CDaemon


__cfg_file__ = 'prm.cfg'
__pid_file__ = '/var/run/prm.pid'
__log_file__ = '/var/log/prm.log'

__max_mem__ = 50
__max_cpu__ = 80
__max_time__ = 180
__sleep_time__ = 20


def config_load(config_file):
    """ Read config params """
    global __max_mem__,__max_cpu__,__max_time__,__sleep_time__,__pid_file__,__log_file__
    cp = ConfigParser.RawConfigParser()
    cp.read(config_file)
    sec = 'prm'

    def get(name,default):
        try:
            if type(default) == int:
                return cp.getint(sec,name)
            else:
                return cp.get(sec,name)
        except:
            return default
    
    __max_mem__ = get('max_mem',__max_mem__)
    __max_cpu__ = get('max_cpu',__max_cpu__)
    __max_time__ = get('max_time',__max_time__)
    __sleep_time__ = get('sleep_time',__sleep_time__)
    __pid_file__ = get('pid_file',__pid_file__)
    __log_file__ = get('log_file',__log_file__)

    print __max_mem__,__max_cpu__,__max_time__,__sleep_time__,__pid_file__,__log_file__


class PRMDaemon(CDaemon):
    """ Linux Process Resource Monitor Daemon
    """
    
    def run(self):
        self.info('Process Resource Monitor Daemon Started')
        processes = {}

        while True:
            # find bad processes
            pids = psutil.get_pid_list()
            for pid in pids:
                if pid not in processes:
                    try:
                        p = psutil.Process(pid)
                        p.time_mem = 0
                        p.time_cpu = 0
                        processes[pid] = p
                    except:
                        pass
                    continue

                p = processes[pid]

                try:
                    mem_percent = round(p.get_memory_percent())
                    cpu_percent = round(p.get_cpu_percent())
                except:
                    continue

                if mem_percent >= __max_mem__:
                    if not p.time_mem:
                        self.info('Starting monitor %s(%u) for high mem: %u' % (p.name,pid,mem_percent))
                        p.time_mem = time.time()
                else:
                    p.time_mem = 0

                if cpu_percent >= __max_cpu__:
                    if not p.time_cpu:
                        self.info('Starting monitor %s(%u) for high cpu: %u' % (p.name,pid,cpu_percent))
                        p.time_cpu = time.time()
                else:
                    p.time_cpu = 0

            # find and kill really process
            for pid in processes.keys():
                if not psutil.pid_exists(pid):
                    del processes[pid]
                    continue

                p = processes[pid]

                min = time.time() - __max_time__

                if p.time_mem and p.time_mem < min:
                    self.info('Kill %s(pid:%u, uid:%u) for high mem' % (p.name,pid,p.uid))
                    p.kill(9)

                if p.time_cpu and p.time_cpu < min:
                    self.info('Kill %s(pid:%u, uid:%u) for high cpu' % (p.name,pid,p.uid))
                    p.kill(9)

            time.sleep(__sleep_time__)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(0)

    config_load(__cfg_file__)

    d = PRMDaemon(__pid_file__,__log_file__)
    d.main(sys.argv[1])

