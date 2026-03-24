# Check DEPS - 依赖文件检查工具

> 源文件: `infra/bots/check_deps.py`

## 概述

`check_deps.py` 是一个 Skia CI 工具脚本，用于验证 DEPS 文件中所有依赖条目的正确性。它确保所有依赖仓库托管在 `googlesource.com` 上，并且所有版本号为有效的 40 字符十六进制 Git commit hash。

## 架构位置

位于 `infra/bots/` 目录，作为 Skia 依赖管理的自动化检查工具。通常在 CI 的 Housekeeper 任务中运行。

## 主要类与结构体

无类定义。

## 公共 API 函数

- `main()`: 加载并验证 DEPS 文件的所有条目

## 内部实现细节

1. 定位 Skia 根目录（从脚本位置向上两级）
2. 通过 `gclient revinfo` 命令获取所有依赖信息
3. 解析输出的 `名称: 仓库@版本` 格式
4. 跳过 `skia` 自身条目和 `chrome-infra-packages`（CIPD 包）
5. 验证规则：
   - 所有仓库必须托管在 `googlesource.com`（否则指向 `http://go/new-skia-git-mirror`）
   - 版本号必须匹配正则 `^[a-z0-9]{40}$`（40 字符十六进制 hash）
6. 收集所有错误后统一输出，非零退出码表示失败

## 依赖关系

- `infra/bots/utils.py`: 提供 `WHICH` 和 `GCLIENT` 常量
- Python 标准库: `os`, `re`, `subprocess`, `sys`
- 外部工具: `gclient` (depot_tools)

## 设计模式与设计决策

- 批量验证模式: 收集所有错误后一次性报告，而非遇到第一个错误就停止
- 通过 `which gclient` 找到 `gclient.py` 的实际路径，避免触发 `update_depot_tools`
- 使用正则表达式验证 commit hash 格式

## 性能考量

无特殊性能考量，通常作为 CI 检查步骤运行。

## 相关文件

- `DEPS`: 被检查的依赖文件
- `infra/bots/utils.py`: 提供平台相关常量
- `infra/bots/infra_tests.py`: 调用此检查的测试运行器
