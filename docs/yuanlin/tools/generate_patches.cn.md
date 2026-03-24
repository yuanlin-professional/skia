# generate_patches - Bazel 第三方依赖补丁生成器

> 源文件: `tools/generate_patches.py`

## 概述

`generate_patches.py` 生成用于 Bazel `git_repository` 规则的补丁文件。当 Skia 需要向第三方依赖(如 FreeType)添加自定义配置文件时,此脚本将源文件转换为 git patch 格式,供 Bazel 在检出时自动应用。

## 架构位置

属于 Skia Bazel 构建系统的依赖管理工具链。

## 公共 API 函数

- **`create_single_file_patch(source_file, destination_path)`**: 将源文件内容转换为 git "new file" 补丁格式
- **`main()`**: 处理成对的源文件/目标路径参数

## 内部实现细节

- 生成 `new file mode 100644` 格式的补丁
- 使用 stub index(`0000000..fffffff`),Bazel patch 工具不检查
- 每行前添加 `+` 前缀表示新增

## 依赖关系

- Python 标准库: `sys`

## 设计模式与设计决策

- **补丁方案**: 解决了 Bazel 外部依赖无法使用其他外部依赖文件的include路径问题

## 性能考量

脚本本身开销极小,仅在 Bazel 配置变更时需要重新运行。

## 相关文件

- `bazel/Makefile:generate_third_party_patches` - 调用此脚本的 Make 目标
