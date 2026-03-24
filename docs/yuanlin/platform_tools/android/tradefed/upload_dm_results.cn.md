# upload_dm_results.py - DM 测试结果上传工具

> 源文件: `platform_tools/android/tradefed/upload_dm_results.py`

## 概述

本文件是一个 Python 脚本，用于将 Skia DM（Drawing Manager）测试工具生成的 PNG 图像文件和 JSON 摘要结果上传到 Google Cloud Storage（GCS）。它是 Skia Android 持续集成管线中 TradeFed（Trade Federation）测试框架的组成部分，负责在 Android 设备上运行测试后收集和归档测试产物。

## 架构位置

该文件位于 `platform_tools/android/tradefed/` 目录下，属于 Skia 的 Android CI/CD 工具链层。它在测试执行完成后被调用，将测试结果从本地设备或构建机器上传到集中的 GCS 存储桶中，供后续的结果比较和回归检测系统使用。

## 主要类与结构体

本文件不定义类，仅包含一个主函数和相关的配置常量：

- **ACL 配置**: 使用 `PRIVATE` 预定义 ACL，并通过细粒度 ACL 授予 `google.com` 域的读取权限
- **GCS 桶名**: `skia-android-dm`（用于存储图像和 JSON 摘要）

## 公共 API 函数

- **`main(dm_dir, build_number, builder_name)`**: 脚本主入口函数
  - `dm_dir`: DM 输出目录路径，包含 PNG 文件和 `dm.json` 摘要
  - `build_number`: 当前构建编号
  - `builder_name`: 构建器名称

## 内部实现细节

### 上传流程

1. **校验**: 检查 `dm_dir` 中是否存在 `dm.json` 文件，不存在则退出
2. **分离**: 将 `dm.json` 移动到临时目录，使 `dm_dir` 中只剩图像文件
3. **图像上传**: 将所有 PNG 图像上传到 `skia-android-dm/dm-images-v1/`，仅上传新文件（`IF_NEW` 策略）
4. **JSON 上传**: 将 JSON 摘要上传到按时间层级组织的路径：`dm-json-v1/YYYY/MM/DD/HH/build-number/builder-name/dm.json`
5. **还原**: 将 `dm.json` 移回原目录，清理临时目录

### 路径组织策略

JSON 摘要采用时间层级路径（年/月/日/时/构建号/构建器名），便于按时间范围查询和清理历史数据。图像则统一存放在扁平目录中，依靠去重策略（`IF_NEW`）避免重复上传。

### 权限模型

- 默认为私有访问（`PRIVATE`）
- 通过 `GROUP_BY_DOMAIN` 细粒度 ACL 授予 `google.com` 域内用户的 `READ` 权限
- 确保测试结果仅对 Google 内部可见

## 依赖关系

- **`gs_utils`**: 位于 `common/py/utils/` 的 Google Storage 工具库，通过动态路径插入导入
- **标准库**: `datetime`（时间戳生成）、`os`（路径操作）、`shutil`（文件移动）、`sys`（参数和路径处理）、`tempfile`（临时目录创建）

## 设计模式与设计决策

- **分离上传策略**: 图像和 JSON 摘要分开上传到不同路径，便于独立管理和查询
- **增量上传**: 图像采用 `IF_NEW` 策略，仅上传不存在的新文件，节省带宽和时间
- **时间层级归档**: JSON 摘要按 UTC 时间层级组织，支持高效的时间范围查询
- **原子性设计**: 操作完成后将 `dm.json` 移回原位，保持文件系统状态一致

## 性能考量

- `IF_NEW` 上传策略避免重复上传已存在的图像，显著减少大规模测试的上传时间
- 使用临时目录隔离 JSON 文件，避免在图像批量上传时误包含 JSON 文件
- UTC 时间戳在脚本开始时获取一次，确保路径一致性
- `gs_utils` 库内部可能使用并行上传，批量处理图像目录中的多个文件
- 动态导入 `gs_utils` 避免了模块级别的导入开销，仅在实际运行时加载

### 错误处理

- 如果 `dm.json` 不存在，脚本通过 `sys.exit()` 立即终止并输出错误信息
- GCS 上传失败会由 `gs_utils` 内部处理和上报
- 临时目录在正常流程结束时被清理（`os.rmdir`），但异常退出时可能残留

### 命令行使用

脚本通过命令行参数调用：
```
python upload_dm_results.py <dm_dir> <build_number> <builder_name>
```

其中 `dm_dir` 是 DM 测试输出目录的完整路径。

## 相关文件

- `dm/` - Skia DM 测试工具源码
- `common/py/utils/gs_utils.py` - Google Storage 工具库
- `platform_tools/android/tradefed/` - TradeFed 集成工具目录
- `tools/dm/` - DM 测试工具的配置和辅助脚本
