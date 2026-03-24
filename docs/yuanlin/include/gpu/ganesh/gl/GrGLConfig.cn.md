# GrGLConfig

> 源文件: `include/gpu/ganesh/gl/GrGLConfig.h`

## 概述
GrGLConfig 是 Ganesh OpenGL 后端的配置头文件,定义了 OpenGL 函数调用约定、日志记录和错误检查的编译时配置宏。该文件为跨平台 OpenGL 开发提供统一的配置接口,允许开发者通过编译器定义或配置文件控制 OpenGL 调试和性能分析功能。

## 架构位置
该文件位于 `include/gpu/ganesh/gl` OpenGL 后端配置层,属于 Ganesh OpenGL 子系统的基础设施。它在编译时决定 OpenGL 函数调用的平台特定行为和调试功能的启用状态,被所有 OpenGL 相关代码间接依赖。

## 核心配置宏

### 函数调用约定

#### GR_GL_FUNCTION_TYPE
```cpp
#if !defined(GR_GL_FUNCTION_TYPE)
    #if defined(SK_BUILD_FOR_WIN)
        #define GR_GL_FUNCTION_TYPE __stdcall
    #else
        #define GR_GL_FUNCTION_TYPE
    #endif
#endif
```

**功能**: 定义 OpenGL 函数指针的调用约定

**平台行为**:
| 平台 | 调用约定 | 说明 |
|------|----------|------|
| Windows | `__stdcall` | 标准 Win32 API 调用约定 |
| 其他平台 | 空(默认 C 调用约定) | Unix/Linux/macOS/Android/iOS |

**应用**: 所有 OpenGL 函数指针类型使用此宏:
```cpp
typedef void GR_GL_FUNCTION_TYPE (*GrGLActiveTextureProc)(GrGLenum texture);
```

**自定义**: 可在编译器命令行或 GrUserConfig.h 中覆盖

### 日志记录配置

#### GR_GL_LOG_CALLS
```cpp
#if !defined(GR_GL_LOG_CALLS)
    #ifdef SK_DEBUG
        #define GR_GL_LOG_CALLS 1
    #else
        #define GR_GL_LOG_CALLS 0
    #endif
#endif
```

**功能**: 启用/禁用 OpenGL 调用日志记录

**默认行为**:
- Debug 构建: 启用 (1)
- Release 构建: 禁用 (0)

**运行时控制**:
- 通过全局变量 `gLogCallsGL` 在调试器中动态开关
- 初始值由 `GR_GL_LOG_CALLS_START` 控制

**日志输出**: 使用 SkDebugf 打印每个 GL 调用

**典型日志**:
```
glActiveTexture(GL_TEXTURE0)
glBindTexture(GL_TEXTURE_2D, 42)
glDrawArrays(GL_TRIANGLES, 0, 3)
```

#### GR_GL_LOG_CALLS_START
```cpp
#if !defined(GR_GL_LOG_CALLS_START)
    #define GR_GL_LOG_CALLS_START 0
#endif
```

**功能**: 控制 gLogCallsGL 的初始值

**默认**: 0 (即使启用日志功能,默认也不打印)

**使用场景**: 在调试器中设置 `gLogCallsGL = 1` 动态启用日志

### 错误检查配置

#### GR_GL_CHECK_ERROR
```cpp
#if !defined(GR_GL_CHECK_ERROR)
    #ifdef SK_DEBUG
        #define GR_GL_CHECK_ERROR 1
    #else
        #define GR_GL_CHECK_ERROR 0
    #endif
#endif
```

**功能**: 启用/禁用 GL 调用后的错误检查

**默认行为**:
- Debug 构建: 启用 (1)
- Release 构建: 禁用 (0)

**实现**: 每个 GL 调用后插入 `glGetError()`

**性能影响**:
- 每次调用产生 GPU 同步点
- Debug 构建可接受,Release 构建严重影响性能

**运行时控制**:
- 通过全局变量 `gCheckErrorGL` 在调试器中动态开关
- 初始值由 `GR_GL_CHECK_ERROR_START` 控制

#### GR_GL_CHECK_ERROR_START
```cpp
#if !defined(GR_GL_CHECK_ERROR_START)
    #define GR_GL_CHECK_ERROR_START 1
#endif
```

**功能**: 控制 gCheckErrorGL 的初始值

**默认**: 1 (Debug 构建时默认启用错误检查)

**调试工作流**:
1. Debug 构建默认检查所有错误
2. 发现问题区域后,在调试器中设置 `gCheckErrorGL = 0` 跳过无关代码
3. 在可疑区域前重新设置为 1

## 配置方式

### 方式 1: 编译器命令行
```bash
# 强制启用 Release 构建的错误检查
clang++ -DGR_GL_CHECK_ERROR=1 ...

# 禁用 Debug 构建的日志
clang++ -DGR_GL_LOG_CALLS=0 ...
```

### 方式 2: IDE 项目设置
在 Xcode/Visual Studio/CMake 中定义预处理器宏

### 方式 3: GrUserConfig.h
创建用户配置文件:
```cpp
// GrUserConfig.h
#define GR_GL_LOG_CALLS 1
#define GR_GL_CHECK_ERROR 1
```

### 方式 4: GL 自定义文件
如果使用 `GR_GL_CUSTOM_SETUP_HEADER`:
```cpp
// 自定义头文件
#define GR_GL_CUSTOM_SETUP_HEADER "MyGLSetup.h"

// MyGLSetup.h
#define GR_GL_FUNCTION_TYPE __fastcall  // 自定义调用约定
```

## 运行时调试变量

### gLogCallsGL
```cpp
extern bool gLogCallsGL;  // 实际在实现文件中定义
```

**用途**: 运行时控制 GL 调用日志

**调试器使用**:
```
(lldb) expr gLogCallsGL = 1  // 启用日志
(lldb) continue
(lldb) expr gLogCallsGL = 0  // 禁用日志
```

### gCheckErrorGL
```cpp
extern bool gCheckErrorGL;  // 实际在实现文件中定义
```

**用途**: 运行时控制 GL 错误检查

**性能优化**: 在性能敏感区域临时禁用

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkLoadUserConfig.h | 加载用户自定义配置 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| GrGLFunctions.h | 使用 GR_GL_FUNCTION_TYPE 定义函数指针 |
| GrGLInterface.cpp | 实现调用日志和错误检查 |
| 所有 OpenGL 后端代码 | 间接依赖配置宏 |

## 设计模式与设计决策

### 条件编译模式
使用 `#if !defined(MACRO)` 模式:
- 允许外部覆盖默认值
- 避免重定义警告
- 支持多级配置优先级

### Debug/Release 分离
自动根据 SK_DEBUG 选择默认配置:
- Debug: 最大诊断信息,性能次要
- Release: 最小开销,性能优先
- 灵活性: 可手动覆盖

### 运行时可控
编译时宏 + 运行时变量双层控制:
- 编译时决定是否包含检查代码
- 运行时决定是否执行检查
- 平衡代码大小和灵活性

## 性能考量

### 日志记录开销
- GR_GL_LOG_CALLS=1: 每个调用增加字符串格式化和 I/O 开销
- 建议仅在诊断特定问题时启用
- Release 构建应禁用

### 错误检查开销
- GR_GL_CHECK_ERROR=1: 每个调用后 GPU 同步
- 严重影响渲染性能(可降低 10x-100x)
- 仅在 Debug 构建或定位 GL 错误时使用
- 现代替代: 使用 KHR_debug 扩展的异步错误报告

### 函数调用约定
- `__stdcall` vs 默认调用约定性能差异可忽略
- 主要用于二进制兼容性(Windows DLL)

## 平台相关说明

### Windows 特定
- 使用 `__stdcall` 匹配 OpenGL32.dll 导出约定
- 确保函数指针与系统 GL 库兼容

### Unix/Linux/macOS
- 默认 C 调用约定
- 无需特殊调用约定修饰

### 移动平台 (Android/iOS)
- OpenGL ES 使用默认调用约定
- 错误检查开销对移动设备更显著

### WebGL (Emscripten)
- JavaScript 绑定层已处理调用约定
- 日志可能被浏览器控制台捕获

## 典型配置场景

### 开发调试
```cpp
#define GR_GL_LOG_CALLS 1
#define GR_GL_LOG_CALLS_START 1
#define GR_GL_CHECK_ERROR 1
#define GR_GL_CHECK_ERROR_START 1
```

### 性能分析
```cpp
#define GR_GL_LOG_CALLS 0
#define GR_GL_CHECK_ERROR 0
```

### 持续集成测试
```cpp
#define GR_GL_CHECK_ERROR 1  // 捕获所有 GL 错误
#define GR_GL_LOG_CALLS 0    // 避免日志污染
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/gl/GrGLFunctions.h | 使用函数调用约定宏 |
| src/gpu/ganesh/gl/GrGLInterface.cpp | 实现日志和错误检查 |
| src/gpu/ganesh/gl/GrGLGpu.cpp | OpenGL 后端主实现 |
| include/private/base/SkLoadUserConfig.h | 用户配置加载 |
