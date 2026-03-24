# buildstats - 构建统计工具

## 概述

`buildstats/` 目录包含用于收集和分析 Skia 构建产物体积统计信息的 Python 脚本。这些脚本用于追踪不同构建目标（C++、Flutter、WASM、Web）的二进制大小变化趋势。

## 目录结构

```
buildstats/
├── buildstats_cpp.py       # C++ 构建产物统计
├── buildstats_flutter.py   # Flutter 引擎构建统计
├── buildstats_wasm.py      # WebAssembly 构建统计
├── buildstats_web.py       # Web（CanvasKit）构建统计
└── make_treemap.py         # 生成体积树状图
```

## 关键文件

### buildstats_cpp.py
分析 C++ 编译产物的体积，追踪 Skia 核心库的大小变化。

### buildstats_flutter.py
分析 Flutter 引擎中 Skia 相关部分的体积统计。

### buildstats_wasm.py
分析 WebAssembly 构建产物（如 CanvasKit WASM 模块）的体积。

### buildstats_web.py
分析 Web 相关构建产物的体积统计。

### make_treemap.py
使用构建产物的符号信息生成交互式体积树状图，便于可视化分析代码体积分布。

## 依赖关系

- `infra/bots/recipes/compute_buildstats.py` - 调用这些脚本的 Recipe
- `infra/bots/recipes/upload_buildstats_results.py` - 上传统计结果的 Recipe
- `infra/docker/binary-size/` - 二进制体积分析 Docker 镜像

## 相关文档与参考

- 父目录中关于构建统计 Recipe 的说明
- [Skia Perf 服务](https://perf.skia.org/) - 查看构建体积趋势
