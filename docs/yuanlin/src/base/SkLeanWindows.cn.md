# SkLeanWindows - 精简的 Windows 头文件包含
> 源文件: `src/base/SkLeanWindows.h`

## 概述
SkLeanWindows 是一个专门用于包含 Windows 头文件的薄封装头文件。它通过定义特定的宏（WIN32_LEAN_AND_MEAN 和 NOMINMAX），在包含 windows.h 前后进行预处理设置，以减少 Windows API 的污染范围，避免宏冲突，并加快编译速度。这是 Skia 在 Windows 平台上的关键兼容性工具。

## 架构位置
SkLeanWindows 位于 Skia 基础平台抽象层（src/base）中，是最底层的平台特定头文件之一。它为所有需要调用 Windows API 的 Skia 模块提供统一的包含方式，确保在整个代码库中 Windows 头文件的包含方式一致且无副作用。

## 主要功能

### 条件编译保护
```cpp
#ifdef SK_BUILD_FOR_WIN
    // Windows 相关定义
#endif
```
仅在 Windows 平台编译时生效，其他平台此头文件为空。

### 宏定义管理

#### WIN32_LEAN_AND_MEAN
- **目的**: 排除 Windows API 中很少使用的部分
- **效果**:
  - 不包含 cryptography、DDE、RPC、Shell API
  - 减少编译时间（约 10-20%）
  - 减少命名空间污染
  - 降低宏冲突风险
- **来源**: 微软官方推荐（Old New Thing 博客）

#### NOMINMAX
- **目的**: 阻止 windows.h 定义 min/max 宏
- **问题背景**: Windows SDK 默认定义：
  ```cpp
  #define min(a,b) (((a) < (b)) ? (a) : (b))
  #define max(a,b) (((a) > (b)) ? (a) : (b))
  ```
- **冲突**: 与 C++ 标准库的 `std::min`/`std::max` 以及 Skia 自己的模板函数冲突
- **解决**: 定义 NOMINMAX 阻止这些宏

### 清理机制
```cpp
#ifdef WIN32_IS_MEAN_WAS_LOCALLY_DEFINED
    #undef WIN32_IS_MEAN_WAS_LOCALLY_DEFINED
    #undef WIN32_LEAN_AND_MEAN
#endif
```

**设计意图**:
- 如果宏是由本文件定义的（通过标记宏识别），则在包含 windows.h 后清理
- 避免影响后续包含 windows.h 的代码
- 保持良好的头文件卫生（header hygiene）

## 内部实现细节

### 三段式包含模式

#### 第一阶段：记录和定义
```cpp
#ifndef WIN32_LEAN_AND_MEAN
    #define WIN32_LEAN_AND_MEAN
    #define WIN32_IS_MEAN_WAS_LOCALLY_DEFINED  // 标记宏
#endif
```
- 检查是否已定义 WIN32_LEAN_AND_MEAN
- 若未定义，则定义它并打上标记

#### 第二阶段：包含头文件
```cpp
#include <windows.h>
```
- 在设置好的环境下包含 Windows 头文件

#### 第三阶段：清理
```cpp
#ifdef WIN32_IS_MEAN_WAS_LOCALLY_DEFINED
    #undef WIN32_IS_MEAN_WAS_LOCALLY_DEFINED
    #undef WIN32_LEAN_AND_MEAN
#endif
```
- 根据标记宏判断是否需要清理
- 恢复原始环境

### 为何需要清理
假设场景：
1. 用户代码在包含 Skia 前已定义 WIN32_LEAN_AND_MEAN（故意要精简）
2. Skia 通过此头文件包含 windows.h
3. 如果 Skia 不清理，WIN32_LEAN_AND_MEAN 会保持定义
4. 用户后续包含 windows.h 时会意外继承这个定义

清理机制确保"在此处定义的，在此处清理"。

### IWYU pragma
```cpp
#include "include/private/base/SkFeatures.h" // IWYU pragma: keep
```
- IWYU (Include What You Use) 工具可能认为 SkFeatures.h 未使用
- `pragma: keep` 指示保留此包含
- SkFeatures.h 定义 SK_BUILD_FOR_WIN 宏

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkFeatures.h | 定义 SK_BUILD_FOR_WIN 平台检测宏 |
| <windows.h> | Windows API 头文件（仅 Windows 平台） |

### 被依赖的模块
所有需要调用 Windows API 的 Skia 模块：
- src/ports/SkOSFile_win.cpp（文件操作）
- src/ports/SkThread_win.cpp（线程）
- src/ports/SkFontHost_win.cpp（字体）
- src/ports/SkOSLibrary_win.cpp（动态库加载）
- src/gpu/ganesh/gl/win/*.cpp（OpenGL 上下文）
- src/utils/win/*.cpp（窗口相关工具）

## 设计模式与设计决策

### RAII 风格的宏管理
虽然不是真正的 RAII（因为是宏而非对象），但采用了类似的"获取-使用-释放"模式：
- 获取：定义宏并标记
- 使用：包含 windows.h
- 释放：根据标记清理宏

### 防御性编程
- 检查宏是否已定义，避免重复定义
- 使用标记宏区分"本地定义"和"外部定义"
- 条件清理，不影响外部环境

### 最小侵入原则
- 仅在 Windows 平台生效
- 仅定义必要的宏
- 包含后恢复环境

### 编译时优化
通过 WIN32_LEAN_AND_MEAN 减少编译单元大小：
- 更少的符号需要解析
- 更少的模板实例化
- 更快的链接速度

## 性能考量

### 编译速度提升
WIN32_LEAN_AND_MEAN 带来的编译速度提升：
- **典型场景**: 10-20% 的编译时间减少
- **大型项目**: 数分钟的节省
- **增量编译**: 减少头文件依赖变化的影响

### 无运行时开销
这些宏仅影响编译过程，对生成代码无影响：
- 不增加二进制大小
- 不影响运行时性能
- 纯粹的预处理器操作

### 命名空间污染的代价
不使用 NOMINMAX 的后果：
```cpp
std::vector<int> v;
int result = std::max(v[0], v[1]);  // 编译错误！max 被宏替换
```
修复此类错误需要：
- 添加括号：`(std::max)(v[0], v[1])`
- 或使用 #undef max

使用 NOMINMAX 从根本上避免这个问题。

### 微软官方推荐
```cpp
// https://devblogs.microsoft.com/oldnewthing/20091130-00/?p=15863
```
引用的博客文章详细解释了 WIN32_LEAN_AND_MEAN 的历史和用途，体现了 Skia 遵循平台最佳实践。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkFeatures.h | 定义 SK_BUILD_FOR_WIN |
| src/ports/SkOSFile_win.cpp | 使用 Windows 文件 API |
| src/ports/SkFontHost_win.cpp | 使用 Windows 字体 API |
| src/ports/SkThread_win.cpp | 使用 Windows 线程 API |
| src/gpu/ganesh/gl/win/GrGLMakeNativeInterface_win.cpp | OpenGL 上下文创建 |
| src/utils/win/SkDWrite.cpp | DirectWrite 字体渲染 |
| include/ports/SkTypeface_win.h | Windows 字体接口 |

## 最佳实践

### 使用建议
在 Skia 代码库中需要包含 Windows API 时：
```cpp
// 推荐
#include "src/base/SkLeanWindows.h"

// 不推荐
#include <windows.h>
```

### 扩展此模式
其他项目可以借鉴这个模式：
1. 创建包装头文件
2. 在包含问题头文件前设置宏
3. 使用标记宏追踪定义来源
4. 包含后清理本地定义的宏

### 避免的陷阱
```cpp
// 错误：在此之前包含 windows.h
#include <windows.h>
#include "src/base/SkLeanWindows.h"  // 太晚了，windows.h 已包含
```

正确的顺序：
```cpp
// 正确：先包含 SkLeanWindows.h
#include "src/base/SkLeanWindows.h"
// 后续包含的任何 Windows 相关头文件都会使用精简版本
```
