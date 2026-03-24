# SkGetExecutablePath

> 源文件: src/utils/SkGetExecutablePath.h

## 概述

`SkGetExecutablePath.h` 是 Skia 图形库中定义获取当前可执行文件路径接口的头文件。该文件提供了一个简洁的跨平台 API,用于返回正在运行的可执行文件的完整路径。这是一个接口定义文件,具体实现根据不同操作系统平台有不同的实现版本。

## 架构位置

该头文件位于 Skia 项目的实用工具模块中:

```
src/
  └── utils/
      ├── SkGetExecutablePath.h          # 接口定义(本文件)
      ├── SkGetExecutablePath_linux.cpp  # Linux 实现
      ├── SkGetExecutablePath_win.cpp    # Windows 实现
      └── SkGetExecutablePath_mac.cpp    # macOS 实现
```

该模块为上层应用提供统一的 API,屏蔽了不同操作系统获取可执行文件路径的差异。

## 主要类与结构体

该头文件不包含类或结构体,仅声明一个全局函数。

## 公共 API 函数

### `SkGetExecutablePath()`

```cpp
std::string SkGetExecutablePath();
```

**功能**: 返回当前正在运行的可执行文件的完整限定路径。

**返回值**:
- 成功时返回包含完整绝对路径的 `std::string`
- 失败时返回空字符串

**平台实现**:
- **Linux**: 通过读取 `/proc/self/exe` 符号链接实现
- **Windows**: 使用 `GetModuleFileNameA()` Win32 API
- **macOS**: 使用 `_NSGetExecutablePath()` Mach-O API

**使用示例**:

```cpp
#include "src/utils/SkGetExecutablePath.h"
#include <iostream>

int main() {
    std::string exePath = SkGetExecutablePath();
    if (!exePath.empty()) {
        std::cout << "Executable path: " << exePath << std::endl;
    } else {
        std::cerr << "Failed to get executable path" << std::endl;
    }
    return 0;
}
```

## 内部实现细节

### 跨平台实现策略

该头文件采用**编译时多态**的设计模式:
1. 头文件只包含函数声明
2. 不同平台的实现文件提供具体实现
3. 构建系统根据目标平台选择编译对应的实现文件

### 实现文件选择

在 Skia 的构建配置中:
- 编译 Linux 目标时链接 `SkGetExecutablePath_linux.cpp`
- 编译 Windows 目标时链接 `SkGetExecutablePath_win.cpp`
- 编译 macOS 目标时链接 `SkGetExecutablePath_mac.cpp`

这种设计避免了运行时的条件判断开销,实现了零成本抽象。

## 依赖关系

### 依赖的标准库

```cpp
#include <string>
```

该头文件只依赖 C++ 标准库的 `std::string` 类型。

### 被依赖的模块

该接口可能被以下 Skia 模块使用:
- 资源加载模块(相对路径解析)
- 调试和日志模块(错误报告)
- 测试框架(测试数据定位)
- 插件系统(动态库加载路径)

## 设计模式与设计决策

### 1. 接口分离原则(ISP)

头文件只声明必要的接口,不包含任何实现细节:
- 保持头文件简洁,减少编译依赖
- 实现细节隐藏在平台特定的 `.cpp` 文件中
- 降低头文件变更对依赖代码的影响

### 2. 依赖倒置原则(DIP)

上层模块依赖于抽象接口,而不是具体实现:
- 调用者只需包含头文件,不关心平台差异
- 平台实现可以独立变更而不影响接口
- 便于单元测试和模拟实现

### 3. 开闭原则(OCP)

接口对扩展开放,对修改封闭:
- 新增平台支持只需添加新的实现文件
- 不需要修改接口定义或现有实现
- 符合 Skia 的跨平台扩展策略

### 4. 错误处理策略

采用**返回值方式**表示错误,而不是异常:
- 符合 Skia 的 no-exception 策略
- 性能开销更小,适合图形处理场景
- 调用者需要检查返回的字符串是否为空

## 性能考量

### 1. 内联优化

由于函数实现在独立的 `.cpp` 文件中,编译器无法在调用点内联:
- 存在函数调用开销(约 1-5 纳秒)
- 建议在初始化阶段调用,不要在热路径中使用

### 2. 缓存建议

可执行文件路径在程序运行期间不会改变,建议:
```cpp
// 推荐做法:在初始化时缓存
static const std::string kExecutablePath = SkGetExecutablePath();

// 避免:在循环中重复调用
for (int i = 0; i < n; ++i) {
    std::string path = SkGetExecutablePath();  // 不推荐
    // ...
}
```

### 3. 字符串拷贝开销

函数返回 `std::string` 值类型:
- 现代编译器会使用移动语义(C++11)或 RVO(返回值优化)
- 避免不必要的字符串拷贝
- 在大多数情况下性能开销可忽略

## 相关文件

### 平台特定实现

| 平台 | 实现文件 | 使用的系统 API |
|------|----------|----------------|
| Linux | `SkGetExecutablePath_linux.cpp` | `readlink("/proc/self/exe")` |
| Windows | `SkGetExecutablePath_win.cpp` | `GetModuleFileNameA()` |
| macOS | `SkGetExecutablePath_mac.cpp` | `_NSGetExecutablePath()` |

### 典型使用场景

1. **资源文件定位**:
   ```cpp
   std::string exePath = SkGetExecutablePath();
   std::string resourceDir = GetDirectoryPath(exePath) + "/resources/";
   ```

2. **日志记录**:
   ```cpp
   void LogError(const char* message) {
       std::cerr << "[" << SkGetExecutablePath() << "] " << message << std::endl;
   }
   ```

3. **配置文件加载**:
   ```cpp
   std::string configPath = GetDirectoryPath(SkGetExecutablePath()) + "/config.json";
   ```

### 构建系统集成示例

在 GN 构建文件中的配置:
```gn
skia_utils_sources = [
  "src/utils/SkGetExecutablePath.h",
]

if (is_linux) {
  skia_utils_sources += [ "src/utils/SkGetExecutablePath_linux.cpp" ]
} else if (is_win) {
  skia_utils_sources += [ "src/utils/SkGetExecutablePath_win.cpp" ]
} else if (is_mac) {
  skia_utils_sources += [ "src/utils/SkGetExecutablePath_mac.cpp" ]
}
```

## 可移植性注意事项

### 路径格式差异

不同平台返回的路径格式不同:
- **Linux/macOS**: `/usr/local/bin/app`
- **Windows**: `C:\Program Files\App\app.exe`

调用者需要使用跨平台的路径处理函数来解析返回的路径。

### 符号链接处理

- **Linux**: 自动解析符号链接,返回实际可执行文件路径
- **macOS**: 返回实际路径,不是符号链接
- **Windows**: 不涉及符号链接概念

### 安全考虑

在某些环境中(如沙箱、容器),可能无法获取可执行文件路径:
- 建议检查返回值是否为空
- 提供降级方案或默认路径
- 避免假设路径总是可用

该接口的简洁设计使其成为 Skia 中跨平台功能实现的典范,为上层代码提供了统一、高效、易用的可执行文件路径查询能力。
