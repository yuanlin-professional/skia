# DM 测试结果上传 Recipe (upload_dm_results)

> 源文件: `infra/bots/recipes/upload_dm_results.py`

## 概述

此 recipe 负责将 DM（Skia 测试驱动程序）的测试结果上传到 Google Cloud Storage (GCS)。上传内容包括测试生成的图像文件（PNG、PDF）和结果 JSON 文件（`dm.json`）以及可选的详细日志（`verbose.log`）。图像文件必须先于 JSON 文件上传，以确保当 JSON 被处理时所有引用的图像已经存在。

## 架构位置

该 recipe 位于 Skia CI 测试流水线的上传阶段：

- **上游**: `test.py` recipe 运行 DM 测试并生成结果
- **下游**: GCS 存储 -> Gold 服务处理 dm.json 并进行图像比对
- **数据流**: 测试图像/JSON -> gsutil -> GCS bucket (skia-infra-gm)

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表 |
| `DM_JSON` | 常量 | DM JSON 文件名: `dm.json` |
| `VERBOSE_LOG` | 常量 | 详细日志文件名: `verbose.log` |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，执行以下上传流程：

1. **上传图像** (关键 -- 必须先于 JSON)：
   - 搜索 `.png` 和 `.pdf` 格式的图像文件
   - 使用 `gsutil.cp` 多线程上传到 `gs://{bucket}/dm-images-v1`
   - 过滤掉 glob 返回的误匹配结果

2. **计算上传目标路径**：
   - 格式: `dm-json-v1/{year}/{month}/{day}/{hour}/{revision}/{builder_name}/{timestamp}`
   - Trybot 构建在路径前加 `trybot/` 前缀，并附加 `issue/patchset`

3. **上传 dm.json**：使用 `-Z` 参数（gzip 压缩）上传

4. **上传 verbose.log** (如存在)：同样使用 gzip 压缩

### `GenTests(api)`

生成 5 个测试用例：正常上传、备用 bucket、单次失败重试、全部失败、trybot。

## 内部实现细节

- **图像优先上传**: 注释明确说明图像必须先于 JSON 上传，因为 Gold 服务在处理 JSON 时会引用图像
- **glob 结果过滤**: `api.file.glob_paths` 有一个已知问题，在没有匹配时会返回结果目录本身，因此需要额外过滤 `str(f).endswith(ext)`
- **路径构建**: 使用零填充（`zfill`）确保日期时间字段的排序正确性（如 `01` 而非 `1`）
- **Trybot 隔离**: Trybot 结果放在 `trybot/` 子路径下，防止临时补丁的结果污染正式数据
- **gsutil 多线程**: 图像上传使用 `multithread=True` 加速大量小文件的传输
- **gzip 压缩**: JSON 和日志使用 `-Z` 参数进行传输时压缩

## 依赖关系

- **gsutil** -- Google Cloud Storage 操作模块
- **vars** -- 构建变量管理
- **recipe_engine/file** -- 文件操作（glob、listdir）
- **recipe_engine/json** -- JSON 处理
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/step** -- 步骤执行
- **recipe_engine/time** -- 时间操作

## 设计模式与设计决策

- **图像先行策略**: 严格保证图像在 JSON 之前上传，避免 Gold 服务处理 JSON 时找不到图像引用
- **时间戳路径**: 使用时间戳构建 GCS 路径，便于按时间范围查询和清理
- **Trybot 隔离**: trybot 结果与 CI 结果分开存储，防止数据污染
- **重试机制**: gsutil 模块内建重试（最多 5 次），应对网络不稳定
- **可选日志上传**: verbose.log 仅在存在时上传，不强制要求

## 性能考量

- 多线程 gsutil 上传显著加速图像传输（可能有数百到数千个小图像文件）
- gzip 压缩减少 JSON/日志文件的传输大小
- 使用通配符 `*%s` 批量上传同类型文件，减少 gsutil 调用次数

## 相关文件

- `infra/bots/recipes/test.py` -- 上游 DM 测试 recipe
- `infra/bots/recipe_modules/gsutil/` -- GCS 操作模块
- `infra/bots/recipe_modules/vars/` -- 构建变量模块
- `dm/` -- DM 测试驱动程序源代码
