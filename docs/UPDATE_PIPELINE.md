# OAS 更新管线

## 发布方向

`main` 是经过检查的正式源码分支。每次向 GitHub 的 `main` 推送提交后，
`.github/workflows/mirror-gitee.yml` 会把相同提交同步到以下 Gitee 仓库：

`https://gitee.com/solar-astronauts/onmyoji-auto-script-open`

OAS 客户端最终只从这个 Gitee 仓库更新。

## 凭据

Gitee 用户名和私人令牌只保存在 GitHub Actions Repository secrets 中：

- `GITEE_USERNAME`
- `GITEE_TOKEN`

不要把令牌写入源码、日志或远程地址配置文件。

## 外部更新

外部仓库不能直接覆盖 `main`。后续的上游检查任务会先在隔离分支中抓取、
分类并测试改动；授权、设备绑定、可执行文件和核心控制层改动必须经过检查。
