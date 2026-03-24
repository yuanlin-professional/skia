# SkGetExecutablePath_win

> 源文件: src/utils/SkGetExecutablePath_win.cpp

## 概述

`SkGetExecutablePath_win.cpp` 是 Skia 图形库为 Windows 平台实现的获取当前可执行文件路径的工具文件。该文件通过调用 Windows API 中的 `GetModuleFileNameA` 函数来获取正在运行的可执行文件的完整路径,是 Skia 跨平台路径获取机制在 Windows 上的具体实现。

## 架构位置

该文件位于 Skia 的工具模块中,与其他平台的实现文件并列:

```
src/utils/
  ├── SkGetExecutablePath.h        # 跨平台接口
  ├── SkGetExecutablePath_win.cpp  # Windows 实现(本文件)
  ├── SkGetExecutablePath_linux.cpp
  └── SkGetExecutablePath_mac.cpp
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
    char executableFileBuf[MAX_PATH];
    DWORD executablePathLen = GetModuleFileNameA(nullptr, executableFileBuf, MAX_PATH);
    return (executablePathLen > 0) ? std::string(executableFileBuf) : std::string();
}
```

**返回值**:
- 成功: 包含完整路径的字符串(如 `C:\Program Files\App\app.exe`)
- 失败: 空字符串

## 内部实现细节

### Windows API 使用

#### `GetModuleFileNameA()`

```cpp
DWORD GetModuleFileNameA(
    HMODULE hModule,    // 模块句柄,nullptr 表示当前进程
    LPSTR   lpFilename, // 接收路径的缓冲区
    DWORD   nSize       // 缓冲区大小
);
```

**参数说明**:
- `hModule = nullptr`: 获取当前进程的可执行文件路径
- `executableFileBuf`: 固定大小缓冲区(`MAX_PATH` = 260 字节)
- `MAX_PATH`: Windows 定义的最大路径长度

**返回值**:
- 成功: 实际写入的字符数
- 失败: 0

### 路径长度限制

Windows 传统路径限制:
- **MAX_PATH**: 260 字符(包括 null 终止符)
- **长路径支持**: Windows 10 1607+ 支持超过 260 字符的路径(需启用)
- **当前实现**: 仅支持传统的 260 字符限制

### 错误处理

```cpp
return (executablePathLen > 0) ? std::string(executableFileBuf) : std::string();
```

- 返回值大于 0: 成功,构造字符串
- 返回值等于 0: 失败(可能原因包括缓冲区太小、访问权限不足等),返回空字符串

## 依赖关系

### 系统头文件

```cpp
#include <windows.h>  // GetModuleFileNameA, MAX_PATH, DWORD
```

### Skia 内部依赖

```cpp
#include "src/utils/SkGetExecutablePath.h"  // 接口声明
```

## 设计模式与设计决策

### 简洁实现

Windows 实现是三个平台实现中最简洁的:
- **Linux**: 需要处理符号链接读取和错误检查(20+ 行)
- **macOS**: 需要两次调用获取大小(15+ 行)
- **Windows**: 单次 API 调用即可完成(3 行核心代码)

### 字符集选择

使用 `GetModuleFileNameA`(ANSI 版本)而非 `GetModuleFileNameW`(Unicode 版本):
- **优点**: 直接返回 `char*`,无需转换为 UTF-8
- **缺点**: 对非 ASCII 路径支持有限
- **权衡**: Skia 主要用于 ASCII 路径场景,简化实现

### 错误处理策略

采用简单的成功/失败二分法:
- 不检查具体错误代码(`GetLastError()`)
- 不尝试重试或降级处理
- 符合 Skia 的轻量级工具设计理念

## 性能考量

### 时间复杂度

- **API 调用**: `GetModuleFileNameA` 大约 1-3 微秒
- **字符串构造**: 约 0.5-1 微秒
- **总开销**: 约 2-5 微秒

### 内存使用

```cpp
char executableFileBuf[MAX_PATH];  // 栈上分配 260 字节
```

- **栈分配**: 避免堆内存分配开销
- **固定大小**: 不会动态扩展
- **内存安全**: 自动回收,无泄漏风险

### 优化建议

对于频繁调用场景,建议缓存结果:

```cpp
// 推荐模式
static const std::string& GetCachedExecutablePath() {
    static const std::string path = SkGetExecutablePath();
    return path;
}
```

## 相关文件

### 平台对比

| 平台 | API | 特点 |
|------|-----|------|
| Windows | `GetModuleFileNameA()` | 简单直接,单次调用 |
| Linux | `readlink("/proc/self/exe")` | 需处理符号链接 |
| macOS | `_NSGetExecutablePath()` | 需两次调用获取大小 |

### 长路径支持

对于需要支持超过 260 字符路径的场景,可以使用:
```cpp
// 可能的扩展实现
GetModuleFileNameW(...);  // Unicode 版本
// 配合 "\\?\" 前缀支持长路径
```

### 使用场景

常见使用场景:
1. **插件加载**: 确定 DLL 加载路径
2. **资源定位**: 查找可执行文件同目录下的资源
3. **日志记录**: 记录程序路径用于诊断
4. **配置文件**: 在可执行文件目录下查找配置文件

### Windows 特定注意事项

1. **路径格式**: Windows 使用反斜杠 `\` 作为路径分隔符
2. **盘符**: 路径包含盘符(如 `C:`)
3. **UNC 路径**: 支持网络路径(如 `\\server\share\file.exe`)
4. **大小写**: Windows 文件系统不区分大小写

### 安全考虑

在某些场景下可能失败:
- **权限限制**: 在受限用户权限下可能无法访问
- **路径过长**: 超过 `MAX_PATH` 的路径会被截断
- **特殊环境**: 在某些沙箱或容器环境中可能返回错误

## 实际应用示例

```cpp
// 获取可执行文件所在目录
std::string GetExecutableDir() {
    std::string exePath = SkGetExecutablePath();
    if (exePath.empty()) return "";

    size_t pos = exePath.find_last_of("\\/");
    return (pos != std::string::npos) ? exePath.substr(0, pos) : "";
}

// 构造资源文件路径
std::string GetResourcePath(const char* filename) {
    return GetExecutableDir() + "\\" + filename;
}
```

该实现展示了 Windows 平台 API 的简洁性,通过单一的 Win32 API 调用即可完成可执行文件路径获取,是 Skia 跨平台设计的典型范例。
