# example/ - Skia 示例代码

## 概述

`example/` 包含展示如何使用 Skia API 的示例代码，包括 Vulkan 渲染示例和
外部客户端集成示例。这些示例面向希望在自己项目中集成 Skia 的开发者。

## 目录结构

```
example/
├── BUILD.bazel              # Bazel 构建配置
├── VulkanBasic.cpp          # Vulkan 基础渲染示例
└── external_client/         # 外部客户端集成示例
    ├── BUILD.bazel          # Bazel 构建规则
    ├── MODULE.bazel         # Bazel 模块配置
    ├── MODULE.bazel.lock    # 模块锁定文件
    ├── README.md            # 集成说明
    ├── custom_skia_config/  # 自定义 Skia 配置
    └── src/                 # 示例源码
```

## 关键文件

### VulkanBasic.cpp
展示使用 Skia Ganesh Vulkan 后端进行基础渲染的完整示例：
- 初始化 Vulkan 设备和扩展
- 创建 `GrDirectContext`
- 创建渲染表面
- 执行基本绘制操作

### external_client/
演示外部客户端如何使用自己的 C++ 工具链依赖和构建 Skia：
- `WORKSPACE.bazel` / `MODULE.bazel` 展示 Skia 依赖配置
- `custom_skia_config/` 展示如何自定义 Skia 构建选项
- `BUILD.bazel` 展示使用 Skia 模块化构建规则

## 依赖关系

- Skia 核心库
- Vulkan SDK（VulkanBasic 示例）
- Bazel 构建系统

## 相关文档与参考

- Skia Vulkan 后端: `include/gpu/ganesh/vk/`
- Skia 构建指南: https://skia.org/docs/dev/build/
