from deploy.adb import AdbManager
from deploy.git import GitManager
from deploy.pip import PipManager
from deploy.process import ProcessManager
from module.logger import logger


class Installer(GitManager, PipManager, AdbManager, ProcessManager):
    def install(self):
        try:
            from deploy.patch import pre_checks
            pre_checks()

            self.git_install()
            self.process_kill()
            self.pip_install()
            self.adb_install()
        except Exception as e:
            logger.error(e)
            logger.error('install 失败')

    def kill_process_and_git_update(self):
        try:
            self.git_install()
            self.process_kill()
        except Exception as e:
            logger.error(e)
            logger.error('kill_process_and_git_update 失败')

    def git_update(self):
        try:
            self.git_install()
        except Exception as e:
            logger.error(e)
            logger.error('git_update 失败')


if __name__ == '__main__':
    # pass
    Installer().install()
