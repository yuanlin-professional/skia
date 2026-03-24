# third_party/etc1 - ETC1 纹理压缩

## 概述

`third_party/etc1/` 包含 ETC1（Ericsson Texture Compression 1）纹理压缩
格式的编解码实现。ETC1 是 OpenGL ES 2.0 标准支持的纹理压缩格式，广泛用于
移动设备上的 GPU 纹理优化。

## 目录结构

```
etc1/
├── BUILD.bazel          # Bazel 构建配置
├── etc1.cpp             # ETC1 编解码实现
├── etc1.h               # 头文件
├── LICENSE              # 许可证
└── README.google        # Google 维护说明
```

## 关键文件

- **etc1.h/cpp**: ETC1 纹理压缩和解压缩的完整实现，直接包含在 Skia 仓库中
  （非外部依赖）

## 依赖关系

- 无外部依赖（自包含实现）

## 相关文档与参考

- ETC1 规范: Khronos OpenGL ES 文档
- Skia GPU 纹理: `src/gpu/`
