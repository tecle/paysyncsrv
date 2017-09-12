import time
import os
import sys
from datetime import datetime, date
from signal import SIGTERM
import errno

CUR_DIR = os.path.split(os.path.realpath(__file__))[0]
LOG_PATH = os.path.join(CUR_DIR, "../logs")

class Daemon(object):
    def __init__(self, pid_file_name, umask = 0, work_dir = ".",
                 stdin = os.devnull, stdout_name = "stdout",
                 stderr_name = "stderr"):
        self.pidfile = pid_file_name
        self.umask = umask
        self.work_dir = work_dir
        self.stdin = stdin
        self.stdout = os.path.join(LOG_PATH, stdout_name)
        self.stderr = os.path.join(LOG_PATH, stderr_name)

    def _console_log(self, level, msg):
        d = datetime.now()
        output = ("[%s] [%s] [%s]\n" %
                  (d.strftime("%Y-%m-%d %H:%M:%S"), level.upper(), msg))
        sys.stderr.write(output)
        sys.stderr.flush()

    def _instance_run(self):
        pid = str(os.getpid())
        if self.pidfile:
            file(self.pidfile, 'w+').write("%s\n" % pid)
        self.run()

    def _daemonize(self):
        """Fork the process into the background.
        """
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            self._console_log('error', ("fork #1 failed: (%d) %s\n" %
                                        (e.errno, e.strerror)))
            sys.exit(1)

        os.chdir(self.work_dir)
        os.umask(self.umask)
        os.setsid()

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            self._console_log('error', ("fork #2 failed: (%d) %s\n" %
                                        (e.errno, e.strerror)))
            sys.exit(1)

        if not self.stderr:
            self.stderr = self.stdout

        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+', 0)
        se = file(self.stderr, 'a+', 0)

        pid = str(os.getpid())
        self._console_log('info', 'daemon %s started' % pid)

        os.dup2(si.fileno(), sys.stdin.fileno())
        sys.stdout = so
        sys.stderr = se

        self._instance_run()

    def stop(self):
        """stop behaviour.
        """
        try:
            pf = file(self.pidfile, 'r')
            content = pf.read().strip()
            if not content.isdigit():
                self._console_log('error', ("pid file %s content error, stop nothing"
                                            % self.pidfile))
                return
            self._console_log('info', ("file's content(pid): %s " % content))
            pid = int(content)
            pf.close()
        except IOError:
            self._console_log('error', ("pid file %s missing, stop nothing"
                                        % self.pidfile))
            return

        try:
            begin = time.time()
            while time.time() - begin < 20:
                os.kill(pid, SIGTERM)
                time.sleep(1)
            self._console_log('error', 'stop %s timeout' % str(pid))
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                os.remove(self.pidfile)
                self._console_log('info', 'stop %s success' % pid)
            else:
                self._console_log('error', err)

    def start(self):
        """check and start behaviour.
        """
        pid = None
        try:
            pf = file(self.pidfile, 'r')
            content = pf.read().strip()
            if not content.isdigit():
                self._console_log('warning', ("pid file %s content error, ignore"
                                              % self.pidfile))
            else:
                pid = int(content)
            pf.close()
        except IOError:
            self._console_log('info', ("pid file %s read error, ignore"
                                          % self.pidfile))
        if pid:
            try:
                os.kill(pid, 0)
            except OSError, err:
                if err.errno == errno.ESRCH:
                    self._console_log('info', 'process not running')
                    pass
                else:
                    raise
            else:
                self._console_log('info', 'process %s is running, do noting' % pid)
                return
        self._console_log('info', 'daemonizeing...')
        self._daemonize()

    def test(self):
        """test run behaviour.
        """
        pid = None
        try:
            pf = file(self.pidfile, 'r')
            content = pf.read().strip()
            if not content.isdigit():
                self._console_log('warning', ("pid file %s content error, ignore"
                                              % self.pidfile))
            else:
                pid = int(content)
            pf.close()
        except IOError:
            self._console_log('info', ("pid file %s read error, ignore"
                                          % self.pidfile))
        if pid:
            try:
                os.kill(pid, 0)
            except OSError, err:
                if err.errno == errno.ESRCH:
                    self._console_log('info', 'process not running')
                    pass
                else:
                    raise
            else:
                self._console_log('info', 'process %s is running, do noting' % pid)
                return
        self._console_log('info', 'test running...')
        self._instance_run()

    def getpid(self):
        """get pid
        """
        pid = None
        try:
            pf = file(self.pidfile, 'r')
            content = pf.read().strip()
            if not content.isdigit():
                self._console_log('warning', ("pid file %s content error, ignore"
                                              % self.pidfile))
            else:
                pid = int(content)
            pf.close()
        except IOError:
            self._console_log('info', ("pid file %s read error, ignore"
                                          % self.pidfile))
        return pid
