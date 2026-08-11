from tasks.SwitchAccountOnce.base_channel_task import BaseChannelTask
from tasks.SwitchAccountMany.switch_account_many import SwitchAccountMany
""" 账号切换 """


class ScriptTask(BaseChannelTask):

    def run(self):
        sam = SwitchAccountMany(self.config)
        sam.run()