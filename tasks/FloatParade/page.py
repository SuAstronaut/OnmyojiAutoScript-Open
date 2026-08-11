from tasks.FloatParade.assets import FloatParadeAssets
from tasks.GameUi.assets import GameUiAssets as G
from tasks.GameUi.page import Page, page_main

# 花车主界面
page_fp_main = Page(FloatParadeAssets.I_FP_TASKS)
page_fp_main.link(G.I_BACK_YELLOW, destination=page_main)
page_main.link(FloatParadeAssets.I_FP_ACCESS, destination=page_fp_main)
# 花车任务界面
page_fp_task = Page(FloatParadeAssets.I_FP_UPGRADE)
page_fp_task.link(G.I_BACK_YELLOW, destination=page_fp_main)
page_fp_main.link(FloatParadeAssets.I_FP_TASKS, destination=page_fp_task)
# 花车放置界面
page_fp_placement = Page(FloatParadeAssets.I_FP_PR_CHECK)
page_fp_placement.link(G.I_BACK_RED, destination=page_fp_main)
page_fp_main.link(FloatParadeAssets.I_FP_PLACEMENT_REWARD_ENTER, destination=page_fp_placement)