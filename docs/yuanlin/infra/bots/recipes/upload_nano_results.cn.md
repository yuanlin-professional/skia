# Nanobench 结果上传 Recipe (upload_nano_results)

> 源文件: `infra/bots/recipes/upload_nano_results.py`

## 概述

此 recipe 负责将 nanobench（Skia 性能基准测试工具）的运行结果上传到 Google Cloud Storage (GCS)。上传的 JSON 文件包含性能指标数据，供 perf.skia.org 性能监控平台摄取和展示。它使用 Google Cloud 服务账号认证和 `gcloud storage cp` 命令进行文件传输。

## 架构位置

该 recipe 位于 Skia CI 性能测试流水线的上传阶段：

- **上游**: `perf.py` recipe 运行 nanobench 并生成 JSON 结果文件
- **下游**: GCS 存储 -> perf.skia.org 摄取和展示
- **数据流**: nanobench JSON -> gcloud storage -> GCS bucket (skia-perf) -> perf.skia.org

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表 |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，执行以下上传流程：

1. **查找结果文件**: 在 `start_dir/perf` 目录中搜索 `*.json` 文件，期望恰好找到一个
2. **构建 GCS 路径**: 格式为 `nano-json-v1/{year}/{month}/{day}/{hour}/{builder_name}`
3. **Trybot 路径隔离**: trybot 结果添加 `trybot/` 前缀和 `issue/patchset` 后缀
4. **获取服务账号令牌**: 通过 `api.service_account.default()` 获取具有 GCS 读写权限的访问令牌
5. **上传**: 使用 `gcloud storage cp --gzip-local=json` 上传，gzip 压缩 JSON 文件

### `GenTests(api)`

生成两个测试用例：普通 CI 构建和 trybot 构建。

## 内部实现细节

- **单文件验证**: 期望 perf 目录中恰好有一个 JSON 文件，多文件或无文件都会触发异常
- **服务账号认证**: 使用 `CLOUDSDK_AUTH_ACCESS_TOKEN` 环境变量传递 OAuth2 访问令牌给 gcloud 命令
- **gzip 压缩**: `--gzip-local=json` 在本地压缩 JSON 文件后上传，减少传输大小
- **路径格式**: 使用零填充日期时间组件（`zfill`）确保字典序即时间序
- **Trybot 隔离**: trybot 结果与 CI 结果分开存储，避免临时补丁的数据污染主数据集
- **infra_step=True**: 标记上传步骤为基础设施步骤，区分于测试步骤的失败

## 依赖关系

- **vars** -- 构建变量管理（builder 名称、trybot 检测）
- **recipe_engine/context** -- 执行上下文（设置 cwd 和环境变量）
- **recipe_engine/file** -- 文件操作（glob_paths）
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/service_account** -- 服务账号令牌获取
- **recipe_engine/step** -- 步骤执行
- **recipe_engine/time** -- 时间操作

## 设计模式与设计决策

- **gcloud 替代 gsutil**: 使用 `gcloud storage cp` 而非旧版 `gsutil`，这是 Google Cloud CLI 的现代推荐方式
- **服务账号认证**: 通过环境变量传递令牌，而非依赖机器级别的 gcloud 配置，提高了隔离性
- **Trybot 数据隔离**: trybot 结果存储在独立路径下，perf.skia.org 可以选择性地展示或忽略这些数据
- **时间戳路径分层**: 按年/月/日/时分层存储，便于数据生命周期管理和范围查询

## 性能考量

- 仅上传一个 JSON 文件，传输量很小（通常 KB 级别）
- gzip 压缩进一步减少传输大小
- 服务账号令牌获取有微小延迟，但不影响整体性能
- 使用 `infra_step=True` 确保上传失败被正确分类为基础设施问题而非测试问题

## 相关文件

- `infra/bots/recipes/perf.py` -- 上游 nanobench 性能测试 recipe
- `infra/bots/recipe_modules/vars/` -- 构建变量模块
- `tools/nanobench.cpp` -- nanobench 工具源代码
- perf.skia.org -- 性能数据展示平台
