# third_party/vello - Vello GPU 2D 渲染器

## 概述

`third_party/vello/` 包含 Vello GPU 2D 渲染器的 Skia 集成代码。Vello 是一个
实验性的 GPU 计算着色器驱动的 2D 渲染引擎，使用 Rust 编写，通过计算管线
而非传统的光栅化管线进行路径渲染。

## 目录结构

```
vello/
├── BUILD.bazel          # Bazel 构建配置
├── BUILD.gn             # GN 构建配置
├── build.rs             # Rust 构建脚本
├── Cargo.toml           # Rust 包配置
├── src/                 # Rust 源码
│   ├── lib.rs           # Crate 根
│   ├── encoding.rs      # 场景编码
│   └── shaders.rs       # 计算着色器定义
└── cpp/                 # C++ 接口
    ├── vello.h          # C++ 头文件
    └── path_iterator.h  # 路径迭代器
```

## 关键文件

- **src/lib.rs**: Vello 渲染引擎的 Rust 核心
- **src/shaders.rs**: GPU 计算着色器的定义和加载
- **cpp/vello.h**: 暴露给 Skia C++ 代码的接口

## 依赖关系

- Rust 工具链
- GPU 计算着色器支持
- Skia GPU 后端（Graphite）

## 相关文档与参考

- Vello 项目: https://github.com/linebender/vello
- Skia Graphite 后端: `src/gpu/graphite/`
