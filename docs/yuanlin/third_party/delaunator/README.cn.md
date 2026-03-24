# third_party/delaunator - Delaunay 三角剖分

## 概述

`third_party/delaunator/` 包含 Delaunator 库的 Skia 构建配置。Delaunator 是一个
快速的 2D Delaunay 三角剖分算法实现，可能用于 Skia 的网格生成和几何处理。

## 目录结构

```
delaunator/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 Delaunator 的编译选项

## 依赖关系

- Delaunator 源码（通过 DEPS 拉取）

## 相关文档与参考

- Delaunator: https://github.com/delfrrr/delaunator-cpp
- Skia 几何处理: `src/gpu/ganesh/geometry/`
