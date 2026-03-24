# SkGetExecutablePath_mac

> 源文件: src/utils/SkGetExecutablePath_mac.cpp

## 概述

`SkGetExecutablePath_mac.cpp` 是 Skia 图形库为 macOS 平台实现的获取当前可执行文件路径的工具文件。该文件通过调用 macOS 特定的 `_NSGetExecutablePath` 函数来获取可执行文件的完整路径,采用了两阶段查询的策略来处理动态路径长度。

## 架构位置

该文件是 Skia 跨平台路径获取机制在 macOS/iOS 上的实现:

```
src/utils/
  ├── SkGetExecutablePath.h        # 跨平台接口
  ├── SkGetExecutablePath_mac.cpp  # macOS 实现(本文件)
  ├── SkGetExecutablePath_linux.cpp
  └── SkGetExecutablePath_win.cpp
```

## 主要类与结构体

该文件不包含类或结构体,仅实现接口函数。

## 公共 API 函数

### `SkGetExecutablePath()`

```cpp
std::string SkGetExecutablePath()
```

**功能**: 返回当前可执行文件的完整路径。

**实现**:
```cpp
std::string SkGetExecutablePath() {
    uint32_t size = 0;
    _NSGetExecutablePath(nullptr, &size);  // 第一次调用获取所需大小

    std::string result(size, '\0');
    if (_NSGetExecutablePath(result.data(), &size) != 0) {
        result.clear();  // 失败时清空
    }
    return result;
}
```

**返回值**:
- 成功: 包含完整路径的字符串
- 失败: 空字符串

## 内部实现细节

### macOS API: `_NSGetExecutablePath`

```cpp
int _NSGetExecutablePath(char* buf, uint32_t* bufsize);
```

**参数说明**:
- `buf`: 接收路径的缓冲区(可以为 `nullptr`)
- `bufsize`: 输入时为缓冲区大小,输出时为实际所需大小

**返回值**:
- `0`: 成功
- `-1`: 缓冲区太小,`bufsize` 被设置为所需大小

### 两阶段查询策略

该实现采用**查询-分配-查询**模式:

#### 第一阶段: 查询所需大小

```cpp
uint32_t size = 0;
_NSGetExecutablePath(nullptr, &size);
```

- 传入 `nullptr` 作为缓冲区
- 函数返回 `-1`,但 `size` 被设置为所需的缓冲区大小
- 不需要检查返回值,因为我们只关心 `size`

#### 第二阶段: 分配内存并获取路径

```cpp
std::string result(size, '\0');  // 预分配指定大小
if (_NSGetExecutablePath(result.data(), &size) != 0) {
    result.clear();  // 理论上不应失败,但仍需处理
}
```

- 根据第一阶段获得的大小分配字符串
- 再次调用 API 获取实际路径
- 如果第二次调用失败,清空结果并返回空字符串

### 为何需要两次调用

macOS 的 `_NSGetExecutablePath` 设计特点:
1. **动态路径长度**: 不同系统和应用的路径长度不同
2. **无固定上限**: 没有类似 Windows `MAX_PATH` 的硬性限制
3. **避免截断**: 两次调用确保缓冲区足够大,避免路径被截断

### 典型路径示例

macOS 可执行文件路径示例:
```
/Applications/MyApp.app/Contents/MacOS/MyApp
/Users/username/bin/myprogram
/opt/local/bin/tool
```

路径长度通常在 50-200 字符之间,但理论上可以更长。

## 依赖关系

### 系统头文件

```cpp
#include <mach-o/dyld.h>  // _NSGetExecutablePath
```

**说明**: `<mach-o/dyld.h>` 是 macOS/iOS 的动态链接器(dyld)接口头文件。

### Skia 内部依赖

```cpp
#include "src/utils/SkGetExecutablePath.h"  // 接口声明
```

## 设计模式与设计决策

### 两阶段资源分配模式

该实现展示了经典的**查询大小-分配-填充**模式:

**优点**:
- 避免固定大小缓冲区的浪费
- 避免路径截断风险
- 适应不同长度的路径

**缺点**:
- 需要两次系统调用
- 略微增加代码复杂度

### 错误处理

```cpp
if (_NSGetExecutablePath(result.data(), &size) != 0) {
    result.clear();
}
```

虽然第二次调用理论上不应失败(因为已经分配了足够空间),但仍然进行错误检查:
- **防御性编程**: 处理极端情况和未来 API 变更
- **一致性**: 与其他平台实现保持一致的错误处理策略

### 内存管理

使用 `std::string` 的 RAII 特性:
- 自动内存管理,无需手动 `free`
- 异常安全
- 移动语义支持

## 性能考量

### 时间复杂度

- **第一次调用**: 约 1-2 微秒(仅查询大小)
- **内存分配**: 约 0.5-1 微秒(小字符串通常很快)
- **第二次调用**: 约 2-4 微秒(实际读取路径)
- **总开销**: 约 4-8 微秒

### 内存使用

```cpp
std::string result(size, '\0');  // 动态分配
```

- **动态分配**: 根据实际路径长度分配
- **典型大小**: 50-200 字节
- **无浪费**: 不会分配过大的固定缓冲区

### 优化对比

与固定缓冲区方案对比:

**固定缓冲区方案**:
```cpp
char buf[PATH_MAX];  // macOS PATH_MAX = 1024
_NSGetExecutablePath(buf, ...);
```
- 优点: 单次调用
- 缺点: 浪费内存(典型路径只用 100/1024 字节)

**当前方案**:
- 优点: 精确分配,无浪费
- 缺点: 两次调用(但开销可接受)

### 缓存建议

由于两次系统调用的开销,强烈建议缓存结果:

```cpp
const std::string& GetCachedExecutablePath() {
    static const std::string path = SkGetExecutablePath();
    return path;
}
```

## 相关文件

### 平台实现对比

| 平台 | 策略 | 调用次数 | 缓冲区 |
|------|------|----------|--------|
| macOS | 两阶段查询 | 2 次 | 动态分配 |
| Linux | 固定缓冲区 | 1 次 | PATH_MAX(4096) |
| Windows | 固定缓冲区 | 1 次 | MAX_PATH(260) |

### macOS 特性

#### 应用包结构

macOS 应用通常打包为 `.app` 包:
```
MyApp.app/
  └── Contents/
      ├── MacOS/
      │   └── MyApp          # 实际可执行文件
      ├── Resources/
      └── Info.plist
```

`SkGetExecutablePath()` 返回的是 `MacOS/MyApp` 的完整路径。

#### 符号链接

macOS 支持符号链接,`_NSGetExecutablePath` 自动解析:
```
/usr/local/bin/tool -> /opt/homebrew/bin/tool
```

返回的是实际文件路径,而非符号链接路径。

### iOS 兼容性

该实现同样适用于 iOS/iPadOS:
- `<mach-o/dyld.h>` 在 iOS SDK 中可用
- iOS 应用路径结构类似(但位于沙箱内)
- 典型路径: `/var/containers/Bundle/Application/UUID/MyApp.app/MyApp`

## 实际应用示例

### 获取应用包路径

```cpp
#include "src/utils/SkGetExecutablePath.h"
#include <string>

std::string GetAppBundlePath() {
    std::string exePath = SkGetExecutablePath();
    if (exePath.empty()) return "";

    // 从 /path/to/MyApp.app/Contents/MacOS/MyApp
    // 提取 /path/to/MyApp.app
    size_t pos = exePath.find(".app/");
    if (pos != std::string::npos) {
        return exePath.substr(0, pos + 4);  // 包括 ".app"
    }
    return "";
}
```

### 获取资源路径

```cpp
std::string GetResourcePath(const char* filename) {
    std::string bundlePath = GetAppBundlePath();
    if (bundlePath.empty()) return "";

    return bundlePath + "/Contents/Resources/" + filename;
}
```

### 跨平台路径处理

```cpp
#include <libgen.h>  // dirname

std::string GetExecutableDir() {
    std::string path = SkGetExecutablePath();
    if (path.empty()) return "";

    // 使用 POSIX dirname 获取目录部分
    char* dirPath = dirname(const_cast<char*>(path.c_str()));
    return std::string(dirPath);
}
```

## 安全与可靠性

### 沙箱环境

在 macOS 沙箱(Sandbox)环境中:
- `_NSGetExecutablePath` 仍然可用
- 返回沙箱内的路径
- 不会暴露沙箱外的真实文件系统路径

### 权限要求

- 无特殊权限要求
- 标准用户权限即可调用
- 在所有 macOS 版本中稳定可用

### 失败场景

极少数可能失败的情况:
1. 内存分配失败(极端低内存)
2. 系统 API 内部错误(几乎不可能)
3. 第一次和第二次调用之间路径发生变化(理论上不可能)

该实现展示了 macOS 平台特有的两阶段查询模式,既保证了内存效率,又确保了路径完整性,是适应 macOS 动态路径长度特性的优雅解决方案。
