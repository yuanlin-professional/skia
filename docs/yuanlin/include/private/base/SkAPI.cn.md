# SkAPI

> 源文件: `include/private/base/SkAPI.h`

## 概述
SkAPI 是 Skia 库的符号可见性控制头文件,定义了用于 API 导出/导入的宏。它解决了在不同平台上构建动态链接库(DLL/shared library)时的符号导出问题,确保公共 API 能够正确地对外可见。

## 架构位置
该文件位于 Skia 基础设施层的最底层,属于编译配置子系统。它被几乎所有公共头文件包含,是 Skia API 边界定义的基础组件。

## 主要宏定义

### SKIA_IMPLEMENTATION
```cpp
#if !defined(SKIA_IMPLEMENTATION)
    #define SKIA_IMPLEMENTATION 0
#endif
```

**说明**: 编译时标志,用于区分是在编译 Skia 库本身还是使用 Skia 库:
- 值为 1: 正在编译 Skia 库,需要导出符号
- 值为 0 或未定义: 正在使用 Skia 库,需要导入符号

### SK_API
主要的 API 导出/导入宏,根据编译环境自动配置:

**Windows (MSVC) 配置**:
```cpp
#if SKIA_IMPLEMENTATION
    #define SK_API __declspec(dllexport)  // 编译 Skia 时导出符号
#else
    #define SK_API __declspec(dllimport)  // 使用 Skia 时导入符号
#endif
```

**GCC/Clang 配置**:
```cpp
#define SK_API __attribute__((visibility("default")))
```

**静态链接配置**:
```cpp
#define SK_API  // 空定义,无需特殊处理
```

### SK_SPI
```cpp
#if !defined(SK_SPI)
    #define SK_SPI SK_API
#endif
```

**说明**: "Skia Private Interface" 的缩写,功能上与 SK_API 相同,但语义上用于标记:
- 不如公共 API 稳定的接口
- 主要在 src 目录内部使用
- 可能在版本间发生变化

### SK_API_AVAILABLE
```cpp
#if defined(SK_ENABLE_API_AVAILABLE)
#   define SK_API_AVAILABLE API_AVAILABLE
#else
#   define SK_API_AVAILABLE(...)
#endif
```

**说明**: 用于标记 API 的可用性版本(主要在 macOS/iOS 上):
- 启用时使用系统的 `API_AVAILABLE` 宏(来自 `<os/availability.h>`)
- 默认情况下为空操作
- 用于标记某个 API 需要特定的操作系统版本

## 内部实现细节

### 条件编译逻辑
文件使用多层条件编译来适配不同的构建场景:

1. **首先检查是否已定义 SK_API**: 允许用户自定义符号导出策略
2. **检查是否为 DLL 构建**: 通过 `SKIA_DLL` 宏判断
3. **检查编译器类型**: 区分 MSVC 和 GCC/Clang
4. **检查是否在构建 Skia**: 通过 `SKIA_IMPLEMENTATION` 判断

### 符号可见性机制

**MSVC 机制**:
- `__declspec(dllexport)`: 将符号添加到导出表,使其对外可见
- `__declspec(dllimport)`: 告诉链接器从 DLL 导入符号,优化调用性能

**GCC/Clang 机制**:
- `__attribute__((visibility("default")))`: 设置符号为默认可见性
- 通常配合编译选项 `-fvisibility=hidden` 使用,只导出显式标记的符号

### 依赖关系
```cpp
#include "include/private/base/SkLoadUserConfig.h" // IWYU pragma: keep
```
该包含确保在定义 API 宏之前加载用户配置,允许用户通过配置文件覆盖默认行为。

## 公共 API 函数
该文件不包含函数,仅定义预处理器宏。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkLoadUserConfig.h | 加载用户自定义配置,可能覆盖宏定义 |

### 被依赖的模块
几乎所有 Skia 公共头文件都直接或间接依赖此文件:
- include/core/*.h (核心 API)
- include/effects/*.h (效果 API)
- include/gpu/*.h (GPU 相关 API)
- include/private/*.h (私有接口)

## 设计模式与设计决策

### 平台抽象模式
通过宏定义抽象了不同平台的符号导出机制,使得相同的源代码能够在多个平台上正确编译:
- 统一的 `SK_API` 标记
- 平台特定的底层实现
- 用户代码无需关心平台差异

### 条件编译策略
采用守卫式条件编译,允许多级覆盖:
1. 用户可以通过预定义宏完全自定义
2. 检测 `SKIA_DLL` 决定是否需要导出/导入
3. 默认情况下不做特殊处理(静态链接)

### 接口稳定性标记
通过 `SK_API` 和 `SK_SPI` 的区分,清晰标记接口的稳定性级别:
- `SK_API`: 公共稳定 API
- `SK_SPI`: 内部或不稳定接口

## 性能考量

### 导入优化
在 Windows 上,使用 `__declspec(dllimport)` 而非运行时查找:
- 链接器生成直接调用代码
- 避免运行时的间接跳转开销
- 减少启动时的符号解析时间

### 符号表大小
使用 `-fvisibility=hidden` 配合显式导出:
- 减小最终库文件大小
- 加快动态链接器的符号解析速度
- 减少符号冲突的可能性

### 内联友好性
宏定义不影响内联优化:
- 标记的是符号可见性,不是调用约定
- 编译器仍然可以内联跨模块的小函数

## 平台相关说明

### Windows (MSVC)
- 必须明确区分导出和导入
- 使用 `__declspec` 关键字
- 支持导出整个类或单个函数

### Linux/Unix (GCC/Clang)
- 默认所有符号可见(除非使用 `-fvisibility=hidden`)
- 使用 `visibility` 属性控制
- 支持更细粒度的可见性控制(hidden, protected, internal)

### macOS/iOS
- 基本同 Linux,使用 Clang
- 额外支持 `API_AVAILABLE` 进行版本标记
- Framework 构建时有特殊的符号导出列表

### 静态链接场景
当 `SKIA_DLL` 未定义时:
- `SK_API` 扩展为空
- 所有符号默认可见
- 无需导出/导入声明

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkLoadUserConfig.h | 加载用户配置,可能覆盖宏定义 |
| BUILD.gn / CMakeLists.txt | 构建系统设置 SKIA_IMPLEMENTATION 和 SKIA_DLL 宏 |
| include/core/SkTypes.h | 使用这些宏定义公共类型 |
| 所有公共头文件 | 使用 SK_API 标记导出符号 |

## 使用示例

### 声明公共类
```cpp
class SK_API SkCanvas {
public:
    void drawRect(const SkRect& rect);
    // ...
};
```

### 声明公共函数
```cpp
SK_API void SkGraphics_Init();
```

### 声明私有接口
```cpp
class SK_SPI SkGpuDevice {
    // 内部使用的接口,不保证稳定性
};
```

### 条件可用性标记
```cpp
SK_API_AVAILABLE(macos(10.15), ios(13.0))
void SkMetalDrawable_Present();
```
