# 构建统计结果上传 Recipe (upload_buildstats_results)

> 源文件: `infra/bots/recipes/upload_buildstats_results.py`

## 概述

此 recipe 负责将 `compute_buildstats.py` recipe 生成的构建统计 JSON 文件上传到 Google Cloud Storage (GCS)。上传的数据包括二进制文件大小、代码段分布等信息，供 perf.skia.org 性能监控平台摄取。与 `upload_nano_results.py` 类似，它使用 `gcloud storage cp` 命令进行传输，并为 trybot 构建的结果提供独立的存储路径。

## 架构位置

该 recipe 位于 Skia CI 构建分析流水线的上传阶段：

- **上游**: `compute_buildstats.py` recipe 生成分析 JSON
- **下游**: GCS 存储 -> perf.skia.org 摄取展示
- **数据流**: buildstats JSON -> gcloud storage -> GCS bucket (skia-perf) -> perf.skia.org

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表 |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，执行以下上传流程：

1. **查找结果文件**: 在 `start_dir/perf` 目录中搜索所有 `*.json` 文件
2. **遍历上传**: 对每个 JSON 文件：
   - 在文件名前添加 revision 前缀
   - 构建 GCS 路径: `buildstats-json-v1/{year}/{month}/{day}/{hour}/{builder_name}`
   - Trybot 路径添加 `trybot/` 前缀和 `issue/patchset` 后缀
   - 使用 `gcloud storage cp --gzip-local=json` 上传

### `GenTests(api)`

生成两个测试用例：普通 CI 构建和 trybot 构建。

## 内部实现细节

- **多文件上传**: 与 `upload_nano_results.py`（期望单文件）不同，此 recipe 遍历所有找到的 JSON 文件逐一上传
- **文件名前缀**: 将 revision 哈希添加到文件名前，便于在 GCS 中按 revision 查找文件
- **路径格式**: `buildstats-json-v1/` 前缀（对比 nanobench 的 `nano-json-v1/`），标识数据类型
- **gzip 压缩**: `--gzip-local=json` 在本地压缩后上传，减少传输大小
- **infra_step=True**: 标记为基础设施步骤，上传失败不计入测试失败

## 依赖关系

- **vars** -- 构建变量管理
- **recipe_engine/context** -- 执行上下文
- **recipe_engine/file** -- 文件操作（glob_paths）
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/step** -- 步骤执行
- **recipe_engine/time** -- 时间操作

## 设计模式与设计决策

- **与 upload_nano_results 对称设计**: 两个上传 recipe 结构相似，但 buildstats 支持多文件上传
- **Trybot 数据隔离**: 与其他上传 recipe 一致，trybot 数据存储在独立路径
- **Revision 前缀**: 文件名添加 revision 前缀确保即使多次分析同一构建也不会覆盖结果
- **时间戳路径**: 按时间分层便于数据管理和清理

## 性能考量

- 构建统计 JSON 文件通常很小（KB 级别），上传速度快
- gzip 压缩进一步减少传输大小
- 逐文件上传有微小的命令启动开销，但文件数量通常很少（2-3 个）

## 相关文件

- `infra/bots/recipes/compute_buildstats.py` -- 上游构建统计分析 recipe
- `infra/bots/recipes/upload_nano_results.py` -- 类似的 nanobench 结果上传 recipe
- `infra/bots/recipe_modules/vars/` -- 构建变量模块
- perf.skia.org -- 性能数据展示平台
