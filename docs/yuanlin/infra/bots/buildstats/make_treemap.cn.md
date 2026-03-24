# make_treemap.py - 代码体积树状图生成器

> 源文件: `infra/bots/buildstats/make_treemap.py`

## 概述

`make_treemap.py` 是一个 Python 脚本,用于生成以 HTML 树状图形式展示二进制文件代码体积分布的 `.tar.gz` 压缩包。该工具通过 Docker 容器运行二进制体积分析脚本,将分析结果打包输出,帮助开发者可视化了解 Skia 编译产物的体积构成。

## 架构位置

位于 Skia 基础设施的构建统计(buildstats)子系统中。作为 CI/CD 流水线的一部分,在构建完成后运行以收集和可视化代码体积数据。

## 主要类与结构体

本文件为脚本文件,无类定义。核心逻辑在 `main()` 函数中实现。

## 公共 API 函数

- **`main()`**: 主入口函数。接受两个命令行参数:
  - `argv[1]`: 待分析的二进制文件路径(如 `skottie_tool`)
  - `argv[2]`: 输出目录路径

## 内部实现细节

1. 使用 Docker 镜像 `gcr.io/skia-public/binary-size:v1` 运行体积分析
2. 通过 Docker volume 挂载将输入文件和输出目录映射到容器内
3. 容器内执行 `/opt/binary_size/src/run_binary_size_analysis.py` 生成 HTML 树状图
4. 使用 `tar` 命令将输出目录打包为 `<binary_name>_tree.tar.gz`
5. 最后通过 Docker 清理临时目录中的文件

## 依赖关系

- **外部依赖**: Docker(`gcr.io/skia-public/binary-size:v1` 镜像)
- **Python 标准库**: `os`, `subprocess`, `sys`, `tempfile`

## 设计模式与设计决策

- **容器化隔离**: 使用 Docker 容器封装分析工具,避免对宿主机环境的依赖
- **临时目录模式**: 使用 `tempfile.mkdtemp` 创建临时输出目录,通过 Docker 容器清理,确保无残留

## 性能考量

脚本本身开销极小,主要耗时在 Docker 容器启动和二进制分析过程中。分析完成后通过 `tar` 压缩减少输出文件大小。

## 相关文件

- `infra/bots/buildstats/` 目录下其他构建统计脚本
- `tools/bloaty_treemap.py` - 类似的树状图生成工具(基于 Bloaty)
