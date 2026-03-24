# Find Tasks - 任务搜索工具

> 源文件: `infra/bots/find_tasks.py`

## 概述

`find_tasks.py` 是一个命令行工具，用于在 `tasks.json` 中搜索匹配指定条件的 CI 任务。支持按任务名称和维度（dimensions）进行正则表达式匹配，多个搜索项之间为 AND 关系。

## 架构位置

位于 `infra/bots/` 目录，是 Skia CI 基础设施的调试和查询工具，帮助开发者快速定位符合条件的任务配置。

## 主要类与结构体

无类定义。

## 公共 API 函数

- `main(terms)`: 加载 tasks.json 并输出匹配的任务名称
- `match_task(terms, name, task)`: 检查任务是否匹配所有搜索项
- `match_dimensions(term, task)`: 检查维度是否匹配搜索项
- `match_name(term, name)`: 检查任务名称是否匹配搜索项

## 内部实现细节

1. 从脚本所在目录加载 `tasks.json`
2. 遍历所有任务，对每个任务检查是否匹配所有搜索项
3. 每个搜索项可匹配任务名称或任意维度（OR 关系）
4. 所有搜索项之间为 AND 关系（必须全部满足）
5. 使用 `re.search` 进行正则匹配（子串匹配）

## 依赖关系

- `infra/bots/tasks.json`: 任务配置文件
- Python 标准库: `json`, `os`, `re`, `sys`

## 设计模式与设计决策

- 命令行过滤器模式: 类似 grep 的交互方式
- 使用 `^` 和 `$` 锚点实现精确匹配（如 `^os:Mac-14.5$`）
- 搜索项同时匹配名称和维度，提供灵活的查询能力

## 性能考量

线性扫描所有任务，对于 tasks.json 的规模（数千任务）足够高效。

## 相关文件

- `infra/bots/tasks.json`: 被搜索的任务配置
- `infra/bots/gen_tasks.go`: 生成 tasks.json 的工具
