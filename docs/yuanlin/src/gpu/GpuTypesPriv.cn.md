# GpuTypesPriv

> 源文件: src/gpu/GpuTypesPriv.h

## 概述

`GpuTypesPriv` 是 Skia GPU 模块的私有类型定义头文件,提供了一系列内部使用的类型、枚举和工具函数。该模块补充了公共 API 头文件 `GpuTypes.h`,定义了仅在 Skia 内部使用的类型,包括线程安全标志、时钟类型、压缩格式转换函数和后端 API 字符串表示等。

这些类型和函数主要用于内部实现细节,不暴露给 Skia 的用户,但在 GPU 模块的各个子系统之间广泛共享。该文件体现了良好的封装实践,将内部实现细节与公共接口分离。

## 架构位置

在 Skia 架构中,`GpuTypesPriv` 位于以下位置:

- **私有类型层**: 为 GPU 模块提供内部类型定义
- **跨模块共享**: 被 Ganesh、Graphite 等后端使用
- **类型转换**: 提供不同类型系统之间的转换桥梁
- **平台抽象**: 处理跨平台的时钟和线程差异

该模块是头文件,不包含实现代码,所有函数都是内联或 `constexpr` 的。

## 主要类与结构体

### ThreadSafe 枚举

线程安全标志枚举。

```cpp
enum class ThreadSafe : bool {
    kNo = false,
    kYes = true,
};
```

**用途**: 标记 GPU 对象是否线程安全,用于断言检查和资源管理策略。

**设计说明**: 使用 `bool` 作为底层类型,可隐式转换为布尔值,但保持类型安全。

### StdSteadyClock 类型别名

跨平台的稳定时钟类型。

```cpp
#if defined(__GLIBCXX__) && (__GLIBCXX__ < 20130000)
using StdSteadyClock = std::chrono::monotonic_clock;
#else
using StdSteadyClock = std::chrono::steady_clock;
#endif
```

**用途**: 用于资源的空闲时间追踪和性能测量。

**平台差异**:
- **旧 libstdc++** (2013年前): 使用草案名称 `monotonic_clock`
- **现代标准库**: 使用标准名称 `steady_clock`

**注意事项**: 旧版本可能不保证单调性,但对空闲资源清理的影响有限。

## 公共 API 函数

### CompressionTypeToSkColorType
```cpp
static constexpr SkColorType CompressionTypeToSkColorType(
    SkTextureCompressionType compression)
```

**功能**: 将纹理压缩格式转换为对应的 `SkColorType`。

**参数**: `compression` - 纹理压缩类型。

**返回值**: 对应的 `SkColorType`。

**映射表**:

| 压缩类型 | 返回的 SkColorType | 说明 |
|---------|-------------------|------|
| `kNone` | `kUnknown_SkColorType` | 无压缩 |
| `kETC2_RGB8_UNORM` | `kRGB_888x_SkColorType` | ETC2 RGB |
| `kBC1_RGB8_UNORM` | `kRGB_888x_SkColorType` | BC1 RGB (DXT1) |
| `kBC1_RGBA8_UNORM` | `kRGBA_8888_SkColorType` | BC1 RGBA (DXT1a) |

**设计说明**: 虽然压缩格式和颜色类型概念不同,但 `SkImage` 仍需要 `SkColorType`,这个函数提供了必要的桥接。

### CompressionTypeToStr
```cpp
static constexpr const char* CompressionTypeToStr(
    SkTextureCompressionType compression)
```

**功能**: 将压缩类型转换为字符串表示。

**参数**: `compression` - 纹理压缩类型。

**返回值**: C 字符串字面量。

**映射表**:

| 压缩类型 | 返回字符串 |
|---------|-----------|
| `kNone` | `"kNone"` |
| `kETC2_RGB8_UNORM` | `"kETC2_RGB8_UNORM"` |
| `kBC1_RGB8_UNORM` | `"kBC1_RGB8_UNORM"` |
| `kBC1_RGBA8_UNORM` | `"kBC1_RGBA8_UNORM"` |

**用途**: 日志记录、错误报告、调试输出。

### BackendApiToStr
```cpp
static constexpr const char* BackendApiToStr(BackendApi backend)
```

**功能**: 将 GPU 后端 API 枚举转换为字符串。

**参数**: `backend` - GPU 后端 API 类型。

**返回值**: C 字符串字面量。

**映射表**:

| 后端 API | 返回字符串 |
|---------|-----------|
| `kDawn` | `"kDawn"` |
| `kMetal` | `"kMetal"` |
| `kVulkan` | `"kVulkan"` |
| `kMock` | `"kMock"` |
| `kUnsupported` | `"kUnsupported"` |

**用途**: 后端识别、日志记录、配置管理。

### 位域操作宏
```cpp
SK_MAKE_BITFIELD_CLASS_OPS(GpuStatsFlags)
```

**功能**: 为 `GpuStatsFlags` 枚举生成位域操作符。

**生成的操作符**:
- `operator|` (按位或)
- `operator&` (按位与)
- `operator^` (按位异或)
- `operator~` (按位取反)
- `operator|=`, `operator&=`, `operator^=` (复合赋值)

**用途**: 支持类型安全的标志组合操作:
```cpp
GpuStatsFlags flags = GpuStatsFlags::kDraws | GpuStatsFlags::kPrograms;
```

## 内部实现细节

### constexpr 设计
所有转换函数都是 `constexpr`,可以在编译时求值:
- 减少运行时开销
- 支持静态断言和模板元编程
- 字符串字面量存储在只读数据段

### 边界检查
所有转换函数使用 `switch` 语句覆盖所有枚举值,未匹配的值触发 `SkUNREACHABLE`,确保类型安全。

### 平台兼容性处理
`StdSteadyClock` 的条件编译处理了 libstdc++ 的历史遗留问题:
- 检查 `__GLIBCXX__` 宏识别 libstdc++
- 比较版本号判断是否为旧版本
- 使用标准库的适当类型

### 名称空间
所有类型定义在 `skgpu` 命名空间中,避免全局名称污染。

### 宏生成的操作符
`SK_MAKE_BITFIELD_CLASS_OPS` 宏(定义在 `SkMacros.h`)为枚举类型生成类型安全的位操作符,替代传统的 C 风格位操作,提供更好的类型检查。

## 依赖关系

### 依赖的模块

| 模块 | 依赖内容 | 用途 |
|------|----------|------|
| `include/core/SkColorType.h` | `SkColorType` | 颜色类型枚举 |
| `include/core/SkTextureCompressionType.h` | `SkTextureCompressionType` | 压缩格式枚举 |
| `include/gpu/GpuTypes.h` | `BackendApi`, `GpuStatsFlags` | 公共 GPU 类型 |
| `include/private/base/SkMacros.h` | `SK_MAKE_BITFIELD_CLASS_OPS` | 位域操作宏 |
| `<chrono>` | `std::chrono` 时钟类型 | 时间测量 |

### 被依赖的模块

| 模块 | 使用内容 | 用途 |
|------|----------|------|
| Ganesh 资源管理 | `StdSteadyClock`, `ThreadSafe` | 资源生命周期管理 |
| Graphite 后端 | 压缩类型转换函数 | 纹理创建 |
| GPU 统计系统 | `GpuStatsFlags` 操作符 | 性能监控 |
| 调试工具 | 字符串转换函数 | 日志和错误报告 |
| 纹理压缩路径 | `CompressionTypeToSkColorType` | 格式兼容性处理 |

## 设计模式与设计决策

### 1. 私有接口模式
将内部类型与公共类型分离,防止实现细节泄漏到公共 API:
- `GpuTypes.h`: 公共类型
- `GpuTypesPriv.h`: 私有类型

### 2. 编译时计算
使用 `constexpr` 函数将类型转换推迟到编译时,零运行时开销。

### 3. 类型安全枚举
使用 `enum class` 而非 C 风格枚举,提供强类型检查:
```cpp
ThreadSafe::kYes  // 必须显式作用域
```

### 4. 平台抽象类型别名
通过类型别名(`using`)抽象平台差异,调用代码无需条件编译:
```cpp
StdSteadyClock::now()  // 跨平台统一接口
```

### 5. 转换函数的完整性
所有转换函数覆盖所有枚举值,通过 `SkUNREACHABLE` 确保完整性,防止遗漏新增的枚举值。

### 6. 宏辅助的代码生成
使用宏生成重复的位操作符代码,减少手动编写错误。

## 性能考量

### 1. 零运行时开销
- `constexpr` 函数在编译时求值
- 字符串转换返回字面量指针,无内存分配
- 类型别名无额外抽象层

### 2. 内联优化
所有函数在头文件中定义,编译器可完全内联,消除函数调用开销。

### 3. 分支优化
`switch` 语句会被编译器优化为跳转表或二分查找,O(1) 时间复杂度。

### 4. 缓存友好
- 字符串字面量在只读数据段,永久缓存
- 枚举值本身只是整数,无内存占用

### 5. 类型安全的零成本抽象
`enum class` 和 `using` 在编译后与普通整数和指针无异,类型检查在编译时完成。

### 6. 时钟性能
`StdSteadyClock::now()` 调用底层系统时钟,通常是 `clock_gettime` 或 `mach_absolute_time`,纳秒级精度。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/GpuTypesPriv.h` | 定义 | 私有 GPU 类型 |
| `include/gpu/GpuTypes.h` | 公共对应 | 公共 GPU 类型定义 |
| `include/core/SkColorType.h` | 依赖 | 颜色类型定义 |
| `include/core/SkTextureCompressionType.h` | 依赖 | 压缩格式定义 |
| `src/gpu/ganesh/GrResourceCache.h` | 使用者 | 资源缓存系统 |
| `src/gpu/graphite/ResourceCache.cpp` | 使用者 | Graphite 资源管理 |
| `include/private/base/SkMacros.h` | 依赖 | 通用宏定义 |

**备注**: 该模块虽小但关键,提供了 GPU 模块内部共享的类型和工具。设计体现了良好的模块化原则,将内部类型与公共接口分离,同时通过 `constexpr` 和类型安全枚举提供了高性能和高可维护性的解决方案。
