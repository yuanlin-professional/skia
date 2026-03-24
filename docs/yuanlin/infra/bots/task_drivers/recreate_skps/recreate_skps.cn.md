# recreate_skps - SKP 资源重建任务驱动

> 源文件: `infra/bots/task_drivers/recreate_skps/recreate_skps.go`

## 概述

`recreate_skps` 是一个复杂的任务驱动程序,用于从 Chromium 源码构建 Chrome 浏览器,然后使用该浏览器捕获 SKP(Skia Picture)文件并上传。SKP 文件是 Skia 的序列化绘图记录格式,用于性能测试和回归检测。该程序整合了 Chromium 的 `bot_update`、GN 构建系统和 Ninja,完成端到端的 SKP 重建流程。

## 架构位置

位于 Skia 基础设施的任务驱动层,是 CI/CD 流水线中负责 SKP 资源管理的关键组件。它与 Chromium 构建系统紧密集成,依赖 depot_tools 工具链。

## 主要类与结构体

无显式结构体定义。核心功能通过函数组织实现。

## 公共 API 函数

- **`main()`**: 程序入口,解析多个命令行参数包括:
  - `--skia_revision`: Skia 版本
  - `--patch_ref`: 补丁引用
  - `--dm_path`: DM 二进制路径
  - `--dry_run`: 干运行模式
  - `--skip-sync` / `--skip-build`: 跳过同步/构建步骤
- **`botUpdate()`**: 执行 Chromium 的 bot_update 流程,同步代码

## 内部实现细节

1. **认证初始化**: 使用 Gerrit 认证作用域初始化 HTTP 客户端
2. **depot_tools 检出**: 在临时目录中检出 depot_tools 仓库
3. **Chromium 同步**: 通过 `bot_update.py` 同步 Chromium 源码,支持 git 缓存和补丁引用
4. **Chrome 构建**: 使用 `gn gen` 和 `ninja` 构建 Chrome 浏览器
5. **SKP 捕获**: 运行 `create_and_upload.py` 脚本捕获并上传 SKP
6. **指标上报**: 通过 Pushgateway 上报构建和 SKP 创建的成功/失败指标

## 依赖关系

- `go.skia.org/infra/go/depot_tools` - depot_tools 环境配置
- `go.skia.org/infra/go/gerrit` - Gerrit 认证
- `go.skia.org/infra/go/git` - Git 操作
- `go.skia.org/infra/promk/go/pushgateway` - Prometheus 指标推送
- Chromium 构建工具链(GN, Ninja)

## 设计模式与设计决策

- **可恢复执行**: 通过 `--skip-sync` 和 `--skip-build` 标志支持跳过耗时步骤,便于本地调试
- **故障指标**: 分离了构建失败和 SKP 创建失败两种指标,便于故障诊断
- **环境隔离**: 设置多个 GIT 环境变量禁用交互提示和自动更新

## 性能考量

- Chromium 完整构建非常耗时(数十分钟到数小时)
- 支持 git 缓存目录加速代码同步
- SKP 捕获过程涉及浏览器渲染,也是主要耗时环节

## 相关文件

- `infra/bots/assets/skp/create_and_upload.py` - SKP 捕获和上传脚本
- `bin/fetch-sk` - sk 工具获取脚本
