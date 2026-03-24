# third_party/d3d12allocator - Direct3D 12 内存分配器

## 概述

`third_party/d3d12allocator/` 包含 AMD 的 D3D12 Memory Allocator 库的 Skia
构建配置。该库提供了高效的 Direct3D 12 GPU 内存分配策略，用于 Skia 的
Direct3D 12 后端。

## 目录结构

```
d3d12allocator/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 D3D12 内存分配器的编译选项

## 依赖关系

- D3D12 Memory Allocator 源码（通过 DEPS 拉取）
- Windows SDK（Direct3D 12）

## 相关文档与参考

- D3D12MA: https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator
- Skia D3D 后端: `src/gpu/ganesh/d3d/`
