# GrDriverBugWorkarounds

> 源文件
> - include/gpu/ganesh/GrDriverBugWorkarounds.h
> - src/gpu/ganesh/GrDriverBugWorkarounds.cpp

## 概述

`GrDriverBugWorkarounds` 是 Skia 图形库中用于管理 GPU 驱动程序缺陷规避策略的系统模块。由于不同厂商、不同版本的 GPU 驱动程序存在各种已知问题,Skia 需要一个统一的机制来识别和启用特定的规避方案。该类通过布尔标志的集合来表示各种驱动 bug 的规避开关,允许运行时动态配置和合并规避策略。

该模块支持从整数数组初始化、应用叠加配置等操作,并通过宏生成机制自动管理所有已知的驱动 bug 类型。这种设计使得添加新的规避策略变得简单,只需修改配置文件并重新生成头文件即可。

## 架构位置

该模块位于 Skia GPU 初始化和配置层,在 GPU 上下文创建时被使用:

```
应用层 (GrDirectContext 创建)
    ↓
GPU 配置层 (GrContextOptions, GrDriverBugWorkarounds) ← 当前模块
    ↓
GPU 能力检测层 (GrCaps)
    ↓
GPU 后端实现层 (GrGLGpu, GrVkGpu, GrMtlGpu)
```

该类的实例通常由 `GrCaps` 的子类在构造时创建和配置,然后在整个 GPU 后端生命周期中被查询,以决定是否需要采取特定的规避措施。

## 主要类与结构体

### GrDriverBugWorkarounds

管理所有驱动 bug 规避标志的容器类。

**继承关系:**
- 无继承关系(独立类)

**关键成员变量:**

该类的成员变量通过宏 `GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)` 动态生成。每个已知的驱动 bug 都对应一个布尔成员变量,例如:

| 成员变量示例 | 类型 | 默认值 | 说明 |
|-------------|------|-------|------|
| 各种驱动 bug 标志 | `bool` | `false` | 通过宏展开生成,具体名称取决于 `GrDriverBugWorkaroundsAutogen.h` |

### GrDriverBugWorkaroundType

枚举所有已知驱动 bug 的类型标识符。

```cpp
enum GrDriverBugWorkaroundType {
#define GPU_OP(type, name) type,
  GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)
#undef GPU_OP
  NUMBER_OF_GPU_DRIVER_BUG_WORKAROUND_TYPES
};
```

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `GrDriverBugWorkarounds()` | 默认构造函数,所有标志初始化为 false |
| `GrDriverBugWorkarounds(const GrDriverBugWorkarounds&)` | 拷贝构造函数 |
| `explicit GrDriverBugWorkarounds(const std::vector<int32_t>&)` | 从整数数组初始化,启用指定的规避策略 |
| `GrDriverBugWorkarounds& operator=(const GrDriverBugWorkarounds&)` | 拷贝赋值运算符 |
| `void applyOverrides(const GrDriverBugWorkarounds&)` | 应用叠加配置,启用额外的规避策略(仅开启,不关闭) |
| `~GrDriverBugWorkarounds()` | 默认析构函数 |

## 内部实现细节

### 宏驱动的代码生成

核心实现依赖于 `GPU_DRIVER_BUG_WORKAROUNDS` 宏,该宏在 `GrDriverBugWorkaroundsAutogen.h` 中定义。通过不同的宏展开策略,可以生成:

1. **枚举类型定义**:
```cpp
#define GPU_OP(type, name) type,
GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)
#undef GPU_OP
```

2. **成员变量声明**:
```cpp
#define GPU_OP(type, name) bool name = false;
GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)
#undef GPU_OP
```

### 从整数数组初始化

构造函数接受一个整数向量,每个整数对应一个 `GrDriverBugWorkaroundType` 枚举值:

```cpp
GrDriverBugWorkarounds::GrDriverBugWorkarounds(
        const std::vector<int>& enabled_driver_bug_workarounds) {
    for (auto id : enabled_driver_bug_workarounds) {
        switch (id) {
#define GPU_OP(type, name)                        \
            case GrDriverBugWorkaroundType::type: \
                name = true;                      \
                break;
            GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)
#undef GPU_OP
            default:
                SK_ABORT("Not implemented");
        }
    }
}
```

这允许外部系统(如 Chrome)通过整数列表来配置规避策略。

### 叠加应用规避策略

`applyOverrides()` 使用按位或操作来叠加规避策略,确保已启用的标志不会被关闭:

```cpp
void GrDriverBugWorkarounds::applyOverrides(
        const GrDriverBugWorkarounds& workarounds) {
#define GPU_OP(type, name) \
    name |= workarounds.name;
    GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)
#undef GPU_OP
}
```

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrDriverBugWorkaroundsAutogen.h` | 自动生成的宏定义文件,列举所有已知驱动 bug |
| `SkTypes.h` | Skia 基础类型定义 |
| C++ 标准库 | `std::vector`, `<cstdint>` |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| `GrCaps` 及其子类 | 在能力检测时创建和配置规避策略 |
| `GrGLCaps` | OpenGL 特定的驱动 bug 检测 |
| `GrVkCaps` | Vulkan 特定的驱动 bug 检测 |
| `GrMtlCaps` | Metal 特定的驱动 bug 检测 |
| `GrD3DCaps` | Direct3D 特定的驱动 bug 检测 |
| `GrContextOptions` | 用户可通过选项强制启用某些规避策略 |

## 设计模式与设计决策

### 数据驱动设计

使用自动代码生成而非手动维护每个标志:
- 所有规避策略在外部配置文件中定义
- 通过构建工具生成 `GrDriverBugWorkaroundsAutogen.h`
- 宏展开机制自动生成枚举、成员变量和 switch case

这种设计的优势:
- 添加新规避策略只需修改配置文件
- 代码自动同步,避免手动维护不一致
- 减少样板代码

### 位标志集合模式

虽然使用独立的布尔成员而非位域或位掩码,但提供类似位标志集合的语义:
- 每个标志独立存储,访问性能最优(无需位运算)
- 支持批量启用(通过 `applyOverrides`)
- 类型安全(每个标志有明确的名称)

### 只增不减策略

`applyOverrides()` 只能启用额外的规避策略,不能禁用已有的:

```cpp
name |= workarounds.name;  // 使用 |= 而非 =
```

这是安全设计:如果某个规避策略被某个系统判定为必要,后续的配置不应该禁用它。

### 可扩展的初始化方式

支持多种初始化方式:
1. 默认构造(所有标志为 false)
2. 从整数数组构造(用于外部系统集成)
3. 拷贝构造
4. 叠加配置(`applyOverrides`)

这种灵活性使得该类适用于不同的配置场景。

### 外部配置支持

通过 `SK_GPU_WORKAROUNDS_HEADER` 宏,允许嵌入式系统使用自定义的规避策略列表:

```cpp
#ifdef SK_GPU_WORKAROUNDS_HEADER
#include SK_GPU_WORKAROUNDS_HEADER
#else
#include "include/gpu/ganesh/GrDriverBugWorkaroundsAutogen.h"
#endif
```

## 性能考量

### 零开销抽象

使用布尔成员变量而非虚函数或运行时查表:
- 每个标志访问是简单的内存读取
- 编译器可以内联和优化
- 无函数调用开销

### 紧凑的内存布局

所有布尔标志连续存储,假设有 N 个规避策略:
- 理论大小: N 字节(每个 bool 1 字节)
- 实际大小: 可能有对齐填充,但仍然非常紧凑
- 整个对象通常不超过 100 字节

### 构造时一次性配置

规避策略在 GPU 上下文初始化时配置一次,之后只读访问:
- 无需运行时动态修改
- 无需同步机制
- 支持多线程只读访问

### Switch-case 优化

从整数数组初始化时使用 switch-case,现代编译器会优化为跳转表或二分查找,性能优于线性查找。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/gpu/ganesh/GrDriverBugWorkaroundsAutogen.h` | 自动生成的宏定义文件 |
| `include/gpu/ganesh/GrContextOptions.h` | 用户可配置的上下文选项 |
| `src/gpu/ganesh/GrCaps.h` | GPU 能力检测基类,使用规避策略 |
| `src/gpu/ganesh/gl/GrGLCaps.cpp` | OpenGL 驱动 bug 检测实现 |
| `src/gpu/ganesh/vk/GrVkCaps.cpp` | Vulkan 驱动 bug 检测实现 |
| `tools/generate_workarounds` | 构建工具,生成规避策略代码 |
