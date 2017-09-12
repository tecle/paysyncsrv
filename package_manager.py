#! ./python
# coding: utf-8

import os
import subprocess

cur_path = os.path.split(os.path.abspath(__file__))[0]


class PackageManager(object):
    def __init__(self):
        self.python = os.path.join(cur_path, 'python')
        self.pip = os.path.join(cur_path, 'pip')
        self.tmp_dir = os.path.join(cur_path, '.tmp')
        print self.pip

    def install_by_pip(self, package_name, package_version=None):
        print "begin pip install [%s==%s]" % (package_name, package_version)
        cmd = [self.pip, 'install', package_name if not package_version else "%s==%s" % (package_name, package_version)]
        code = subprocess.call(cmd)
        if code:
            print "pip install [%s] with version [%s] failed, code[%s]." % (package_name, package_version, code)
            exit(1)

    def install_by_tgz(self, file_path, setup_file):
        if not file_path.endswith('.tar.gz'):
            print "invalid file[%s], expect :*.tar.gz" % file_path
            exit(1)
        print "begin install tgz file[%s]" % file_path
        if file_path.startswith('http'):
            cmd = ['wget', '-P', self.tmp_dir, file_path]
            code = subprocess.call(cmd)
            if code:
                print "install failed, code[%s]." % code
                exit(1)
            file_path = os.path.join(self.tmp_dir, os.path.basename(file_path))
        cmd = ['tar', '-zxf', file_path]
        if subprocess.call(cmd, cwd=self.tmp_dir):
            print "unzip file failed with cmd:%s" % cmd
            exit(1)
        print 'unzip file :[tar -zxf %s] finished.' % file_path
        file_path = file_path[:-len('.tar.gz')]
        cmd = [self.python, setup_file, 'install']
        if subprocess.call(cmd, cwd=file_path):
            print "install from tgz failed. cmd:%s" % cmd
            exit(1)


if __name__ == '__main__':
    pip_pack_list = [
        ('tornado', None),
        ('mysql-python', None),
        ('torndb', None),
        ('supervisor', None),
        ('futures', None),
        ('pydes', None)
    ]
    tgz_pack_list = [
        ('https://pypi.python.org/packages/6e/1e/aa15cc90217e086dc8769872c8778b409812ff036bf021b15795638939e4/'
         'repoze.lru-0.6.tar.gz', 'setup.py'),
        ('https://pypi.python.org/packages/60/db/645aa9af249f059cc3a368b118de33889219e0362141e75d4eaf6f80f163/'
         'pycrypto-2.6.1.tar.gz', 'setup.py')
    ]
    manager = PackageManager()
    for pack in pip_pack_list:
        manager.install_by_pip(*pack)
    for pack in tgz_pack_list:
        manager.install_by_tgz(*pack)
