# SkUserConfig

> 源文件: example/external_client/custom_skia_config/SkUserConfig.h

## 概述

SkUserConfig.h 是一个客户端自定义配置文件模板,用于覆盖 Skia 的默认编译配置。该文件当前为空模板,但提供了一个扩展点,允许外部客户端在不修改 Skia 源代码的情况下自定义编译行为,例如禁用某些功能、修改默认值或启用实验性特性。

这是 Skia 构建系统的一部分,展示了如何为外部集成项目提供编译时配置能力。

## 架构位置

```
skia/
└── example/external_client/
    └── custom_skia_config/
        └── SkUserConfig.h          # 客户端自定义配置(13行)
```

该文件通过构建系统的 `-include` 标志或类似机制在 Skia 核心头文件之前被包含,从而实现配置覆盖。

## 主要类与结构体

该文件不定义类或结构体,仅包含预处理器宏定义。当前为空模板,可添加如下类型的配置:

### 可能的配置宏示例

```cpp
// 示例配置(未在此文件中实际定义)

// 禁用 PDF 支持
// #define SK_SUPPORT_PDF 0

// 修改默认字体缓存大小
// #define SK_DEFAULT_FONT_CACHE_LIMIT (2 * 1024 * 1024)

// 启用调试日志
// #define SK_DEBUG

// 禁用 GPU 后端
// #define SK_SUPPORT_GPU 0
```

## 公共 API 函数

该文件不包含函数,仅通过预处理器宏影响编译。

### 常用配置宏参考

用户可在此文件中定义的常见宏(需参考 `include/config/SkUserConfig.h`):

```cpp
// 调试相关
SK_DEBUG                    // 启用调试检查
SK_RELEASE                  // 发布模式

// 功能开关
SK_SUPPORT_PDF              // PDF 支持
SK_SUPPORT_GPU              // GPU 支持
SK_ENCODE_PNG               // PNG 编码
SK_ENCODE_JPEG              // JPEG 编码

// 内存配置
SK_DEFAULT_FONT_CACHE_LIMIT        // 字体缓存限制
SK_DEFAULT_IMAGE_CACHE_LIMIT       // 图像缓存限制
SK_DEFAULT_GLOBAL_DISCARDABLE_MEMORY_POOL_SIZE  // 全局可丢弃内存池

// 平台配置
SK_BUILD_FOR_ANDROID        // Android 平台
SK_BUILD_FOR_IOS            // iOS 平台
SK_BUILD_FOR_MAC            // macOS 平台
SK_BUILD_FOR_WIN            // Windows 平台
```

## 内部实现细节

### 包含机制

该文件通过构建系统在编译时被包含,典型的包含顺序:

```
1. SkUserConfig.h (此文件) - 客户端配置
2. include/config/SkUserConfig.h - Skia 默认配置
3. include/core/*.h - Skia 核心头文件
```

### 头文件保护

```cpp
#ifndef ClientCustomUserConfig_DEFINED
#define ClientCustomUserConfig_DEFINED
// ... 配置宏 ...
#endif
```

使用独特的保护宏名称避免与 Skia 内部头文件冲突。

### 注释指引

```cpp
// See Skia's include/config/SkUserConfig.h for defines that could be here.
```

指引用户参考 Skia 的默认配置文件了解可用选项。

## 依赖关系

### 被依赖于
- Skia 核心头文件(间接依赖)
- 所有 Skia 编译单元

### 依赖于
- 无(这是配置的起点)

### 构建系统集成

在 Bazel BUILD 文件或 GN 配置中:
```python
# Bazel 示例
cc_library(
    name = "skia",
    includes = ["example/external_client/custom_skia_config"],
    # ...
)

# GN 示例
config("skia_user_config") {
  include_dirs = [ "//example/external_client/custom_skia_config" ]
}
```

## 设计模式与设计决策

### 1. 配置分离模式

将客户端配置与库源代码分离:
- **优点**: 升级 Skia 时不会覆盖客户端配置
- **缺点**: 需要构建系统支持

### 2. 预处理器配置

使用预处理器宏而非运行时配置:
- **编译时优化**: 未使用的代码完全被剔除
- **零运行时开销**: 无需检查配置标志
- **类型安全**: 编译时验证

### 3. 设计决策

#### (1) 为何提供空模板?

- **示例作用**: 展示配置文件的位置和结构
- **渐进式配置**: 用户按需添加配置
- **避免混淆**: 不包含可能不适用的默认设置

#### (2) 为何不直接修改 Skia 源码?

- **可维护性**: 更新 Skia 版本时保留配置
- **版本控制**: 客户端配置与 Skia 源码分离
- **多项目**: 同一 Skia 源码支持不同配置

#### (3) 配置优先级

```
客户端 SkUserConfig.h (最高)
    ↓
Skia include/config/SkUserConfig.h
    ↓
Skia 默认值 (最低)
```

## 性能考量

### 1. 编译时优化

通过配置宏禁用未使用功能可显著减小二进制大小:

```cpp
// 禁用 PDF 支持
#define SK_SUPPORT_PDF 0
```

**影响**:
- PDF 相关代码被完全剔除
- 减少链接时间
- 减小最终二进制文件大小(可能减少数百 KB)

### 2. 内存配置优化

```cpp
// 针对嵌入式设备减少缓存
#define SK_DEFAULT_FONT_CACHE_LIMIT (512 * 1024)  // 默认 2MB -> 512KB
#define SK_DEFAULT_IMAGE_CACHE_LIMIT (16 * 1024 * 1024)  // 默认 32MB -> 16MB
```

**权衡**:
- 减少内存使用
- 可能增加缓存未命中,影响性能

### 3. 调试 vs 发布

```cpp
#ifdef NDEBUG
  #define SK_RELEASE 1
#else
  #define SK_DEBUG 1
#endif
```

- **调试模式**: 启用断言和额外检查,性能降低 10-30%
- **发布模式**: 禁用所有检查,最大性能

## 相关文件

### Skia 配置文件
- **include/config/SkUserConfig.h**: Skia 默认用户配置
- **include/config/SkUserConfigManual.h**: 手动配置选项参考

### 外部客户端示例
- **example/external_client/BUILD.bazel**: Bazel 构建配置
- **example/external_client/src/**: 使用此配置的示例程序

### 配置文档
- **site/docs/user/build.md**: Skia 构建文档
- **docs/examples/**: 配置示例

### 常见配置场景

#### 移动应用配置
```cpp
#define SK_DEFAULT_FONT_CACHE_LIMIT (1 * 1024 * 1024)
#define SK_DEFAULT_IMAGE_CACHE_LIMIT (8 * 1024 * 1024)
#define SK_SUPPORT_PDF 0  // 移动端通常不需要 PDF
```

#### 服务器端渲染配置
```cpp
#define SK_DEFAULT_FONT_CACHE_LIMIT (16 * 1024 * 1024)
#define SK_SUPPORT_GPU 0  // 无头服务器可能不需要 GPU
```

#### 调试配置
```cpp
#define SK_DEBUG 1
#define SK_DEBUG_TRACE_WINDING 1  // 路径填充调试
#define SK_SUPPORT_LEGACY_AA_CHOICE 1  // 抗锯齿选项调试
```

该配置文件虽然简单,但是 Skia 构建灵活性的关键组成部分,允许客户端根据具体需求定制 Skia 的编译行为和资源使用。
