# SkOSFile_stdio

> 源文件: [src/ports/SkOSFile_stdio.cpp](../../../../src/ports/SkOSFile_stdio.cpp)

## 概述

本文件实现了 Skia 文件操作抽象层中基于标准 C 库 (`stdio.h`) 的跨平台文件 I/O 函数。提供了文件打开、关闭、读写、大小查询、目录判断与创建等基础操作。这些函数是 Skia 内部所有文件访问的底层支撑，包含了对 Windows UTF-8 路径和 iOS Bundle 路径的特殊处理。

## 架构位置

本文件是 Skia 文件系统抽象的核心实现之一，提供与具体平台无关的标准 I/O 操作。它与 `SkOSFile_posix.cpp` 和 `SkOSFile_win.cpp` 配合，共同构成完整的文件操作层。

```
src/core/SkOSFile.h (抽象接口声明)
  ├── src/ports/SkOSFile_stdio.cpp (本文件: 标准 I/O 操作)
  ├── src/ports/SkOSFile_posix.cpp (POSIX 特定: mmap, 文件标识, 目录迭代)
  └── src/ports/SkOSFile_win.cpp   (Windows 特定: mmap, 文件标识, 目录迭代)
```

## 主要类与结构体

本文件不定义公共类，但包含一个 Windows 平台内部辅助函数。

### Windows 内部函数

| 函数 | 说明 |
|------|------|
| `is_ascii(const char* s)` | 检查字符串是否全为 ASCII |
| `fopen_win(const char* utf8path, const char* perm)` | Windows 平台的 UTF-8 路径 fopen 包装 |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `FILE* sk_fopen(const char path[], SkFILE_Flags flags)` | 打开文件，支持读/写标志，含 Windows UTF-8 和 iOS Bundle 回退 |
| `size_t sk_fgetsize(FILE* f)` | 获取文件大小（字节数） |
| `size_t sk_fwrite(const void* buffer, size_t byteCount, FILE* f)` | 写入数据到文件 |
| `void sk_fflush(FILE* f)` | 刷新文件缓冲区 |
| `size_t sk_ftell(FILE* f)` | 获取当前文件位置 |
| `void sk_fclose(FILE* f)` | 关闭文件 |
| `bool sk_isdir(const char* path)` | 判断路径是否为目录 |
| `bool sk_mkdir(const char* path)` | 创建目录 |

## 内部实现细节

### sk_fopen - 文件打开

1. 根据 `SkFILE_Flags` 构建权限字符串 (`"rb"`, `"wb"`, `"rwb"`)
2. **Windows 路径**: 若路径包含非 ASCII 字符，使用 `fopen_win()` 将 UTF-8 转为 UTF-16 后调用 `_wfopen()`
3. **iOS Bundle 回退**: 若文件不存在且为只读模式，尝试在 iOS Bundle 的 `data` 目录中查找
4. 写入失败时输出调试信息（含 `errno` 和错误消息）

权限字符串构建逻辑:
```
kRead_SkFILE_Flag  -> 'r'
kWrite_SkFILE_Flag -> 'w'
始终追加 'b' (二进制模式)
```

### fopen_win - Windows UTF-8 支持

- 对纯 ASCII 路径直接调用标准 `fopen()`（快速路径）
- 对非 ASCII 路径执行 UTF-8 到 UTF-16 的手动转换
- 使用 `SkUTF::NextUTF8()` 和 `SkUTF::ToUTF16()` 进行编码转换
- 分两遍处理：第一遍计算所需 UTF-16 单元数，第二遍执行转换
- 对格式不正确的 UTF-8 序列返回 `nullptr`
- 最终调用 `_wfopen()` 打开文件

### sk_fgetsize - 文件大小获取

```cpp
long curr = ftell(f);     // 记录当前位置
fseek(f, 0, SEEK_END);   // 移到文件末尾
long size = ftell(f);     // 获取位置 = 文件大小
fseek(f, curr, SEEK_SET); // 恢复原始位置
```

- 对负值 `curr` 或 `size` 结果返回 0 作为安全保护
- 此方法不适用于非 seekable 的流，但对常规文件可靠

### sk_fwrite / sk_fflush / sk_ftell / sk_fclose

这些函数是标准 C 库函数的薄封装:
- `sk_fwrite`: 直接调用 `fwrite(buffer, 1, byteCount, f)`
- `sk_fflush`: 调用 `fflush(f)` 并带有 `SkASSERT(f)` 保护
- `sk_ftell`: 调用 `ftell(f)` 并将负值结果转为 0
- `sk_fclose`: 接受 null 指针并安全跳过

### sk_isdir - 目录判断

- 使用 `stat()` 检查路径状态
- 检查 `status.st_mode & S_IFDIR` 位
- iOS 平台上如果默认路径失败，回退到 Bundle 路径检查

### sk_mkdir - 目录创建

- 先检查目录是否已存在 (`sk_isdir`)
- 再检查路径是否存在但不是目录 (`sk_exists`)，输出错误到 stderr
- Windows 使用 `_mkdir()`，POSIX 使用 `mkdir(path, 0777)`
- POSIX 上创建失败时调用 `perror()` 输出错误信息

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkTypes.h` | 基础类型与平台宏 |
| `src/core/SkOSFile.h` | 文件操作函数声明 |
| `<stdio.h>` | 标准 C I/O |
| `<sys/stat.h>` | 文件状态查询 |
| `<errno.h>` | 错误码 |
| `src/base/SkUTF.h` | UTF 编码转换 (Windows) |
| `src/ports/SkOSFile_ios.h` | iOS Bundle 路径解析 |

## 设计模式与设计决策

1. **平台抽象层**: 统一的 `sk_*` 函数族隐藏了不同操作系统间的差异（Windows 宽字符路径、iOS Bundle 机制、POSIX 标准路径）
2. **条件编译**: 使用 `#ifdef _WIN32`、`#ifdef SK_BUILD_FOR_IOS` 等宏隔离平台特定代码
3. **回退策略**: iOS 上优先尝试标准路径，失败后自动回退到 Bundle 资源查找
4. **防御性编程**: `ftell` 返回负值时安全处理，`fclose` 接受 null 指针
5. **二进制模式默认**: 所有文件打开都以二进制模式 (`'b'`) 进行，避免跨平台的换行符转换问题
6. **权限分离**: `sk_fopen` 的 `SkFILE_Flags` 参数清晰区分读和写操作

## 平台特定行为汇总

| 函数 | Windows 特殊处理 | iOS 特殊处理 | POSIX 标准行为 |
|------|:---:|:---:|:---:|
| `sk_fopen` | UTF-8 -> UTF-16 转换 | Bundle 路径回退 | 直接 fopen |
| `sk_isdir` | 无 | Bundle 路径回退 | 直接 stat |
| `sk_mkdir` | `_mkdir()` | 无 | `mkdir(, 0777)` |
| `sk_fgetsize` | 无 | 无 | 通用 fseek/ftell |
| `sk_fwrite` | 无 | 无 | 通用 fwrite |
| `sk_fclose` | 无 | 无 | 通用 fclose + null 守卫 |

## 性能考量

- `sk_fgetsize()` 使用 `fseek/ftell` 组合获取大小，涉及两次文件指针移动；对频繁调用的场景可能需要缓存结果
- Windows 上非 ASCII 路径的 UTF-8 到 UTF-16 转换需要两次遍历（一次计算长度，一次转换），但这是必要的一次性开销
- `sk_fclose()` 中的 null 检查避免了对已关闭或无效文件指针的操作
- `sk_fwrite` 直接委托给 `fwrite`，是一个薄封装，无额外开销
- `fopen_win` 的 ASCII 快速路径确保纯英文路径不会触发 UTF 转换
- `sk_mkdir` 先做两次检查（`sk_isdir` 和 `sk_exists`）再创建，避免不必要的系统调用
- iOS Bundle 回退仅在默认路径失败且为只读模式时触发，不影响写操作的性能

## 相关文件

- `src/core/SkOSFile.h` — 文件操作函数声明，定义了 `SkFILE_Flags` 枚举和所有 `sk_*` 函数的签名
- `src/ports/SkOSFile_posix.cpp` — POSIX 平台特定操作 (mmap, 文件标识, 目录迭代等)
- `src/ports/SkOSFile_win.cpp` — Windows 平台特定操作 (Windows API 实现)
- `src/ports/SkOSFile_ios.h` — iOS Bundle 路径辅助函数 `ios_get_path_in_bundle()`
- `src/base/SkUTF.h` — UTF 编码转换工具，提供 `SkUTF::NextUTF8()` 和 `SkUTF::ToUTF16()`
