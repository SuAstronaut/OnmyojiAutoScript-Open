# This Python file uses the following encoding: utf-8
# copy from alas https://github.com/LmeSzinc/AzurLaneAutoScript
from deploy.config import DeployConfig, ExecutionError
from deploy.logger import logger
from deploy.utils import *


class GitManager(DeployConfig):
    @cached_property
    def git(self):
        return self.filepath('GitExecutable')

    @staticmethod
    def remove(file):
        try:
            os.remove(file)
            logger.info(f'Removed file: {file}')
        except FileNotFoundError:
            logger.info(f'File not found: {file}')

    def git_repository_init(
            self, repo, source='origin', branch='master',
            proxy='', ssl_verify=True, keep_changes=False
    ):
        logger.hr('Git Init', 1)
        if not self.execute(f'{self.git} init', allow_failure=True):
            # A transient process-launch failure must never destroy repository
            # metadata. Let the normal fallback path handle the failure.
            logger.warning('Git init failed; preserving existing .git metadata')
            self.execute(f'{self.git} init')

        logger.hr('Set Git Proxy', 1)
        if proxy:
            self.execute(f'{self.git} config --local http.proxy {proxy}')
            self.execute(f'{self.git} config --local https.proxy {proxy}')
        else:
            self.execute(
                f'{self.git} config --local --unset http.proxy',
                allow_failure=True, output=False, silent=True
            )
            self.execute(
                f'{self.git} config --local --unset https.proxy',
                allow_failure=True, output=False, silent=True
            )

        if ssl_verify:
            self.execute(f'{self.git} config --local http.sslVerify true', allow_failure=True)
        else:
            self.execute(f'{self.git} config --local http.sslVerify false', allow_failure=True)

        logger.hr('Set Git Repository', 1)
        if not self.execute(f'{self.git} remote set-url {source} {repo}', allow_failure=True):
            self.execute(f'{self.git} remote add {source} {repo}')

        logger.hr('Fetch Repository Branch', 1)
        self.execute(f'{self.git} fetch {source} {branch}')

        logger.hr('Pull Repository Branch', 1)
        # Remove git lock
        for lock_file in [
            './.git/index.lock',
            './.git/HEAD.lock',
            './.git/refs/heads/master.lock',
        ]:
            if os.path.exists(lock_file):
                logger.info(f'Lock file {lock_file} exists, removing')
                os.remove(lock_file)
        if keep_changes:
            if self.execute(f'{self.git} stash', allow_failure=True):
                self.execute(f'{self.git} pull --ff-only {source} {branch}')
                if self.execute(f'{self.git} stash pop', allow_failure=True):
                    pass
                else:
                    # No local changes to existing files, untracked files not included
                    logger.info('Stash pop failed, there seems to be no local changes, skip instead')
            else:
                logger.info('Stash failed, this may be the first installation, drop changes instead')
                self.execute(f'{self.git} reset --hard {source}/{branch}')
                self.execute(f'{self.git} pull --ff-only {source} {branch}')
        else:
            self.execute(f'{self.git} reset --hard {source}/{branch}')
            self.execute(f'{self.git} pull --ff-only {source} {branch}')

        logger.hr('Show Version', 1)
        self.execute(f'{self.git} --no-pager log --no-merges -1')

    def git_install(self):
        logger.hr('Update Alas', 0)

        if not self.AutoUpdate:
            logger.info('AutoUpdate is disabled, skip')
            return

        kwargs = dict(
            repo=self.Repository,
            source='origin',
            branch=self.Branch,
            proxy=self.GitProxy,
            ssl_verify=self.SSLVerify,
            keep_changes=self.KeepLocalChanges,
        )

        try:
            self.git_repository_init(**kwargs)
            logger.info('内置 Git 更新成功')
        except ExecutionError:
            if self.git == 'git':
                raise
            logger.warning('内置 Git 更新失败，尝试使用系统默认 Git...')
            self.git = 'git'
            try:
                self.git_repository_init(**kwargs)
                logger.info('系统 Git 更新成功')
            except ExecutionError:
                logger.error('系统 Git 更新也失败了')
                raise


if __name__ == '__main__':
    GitManager().git_install()
