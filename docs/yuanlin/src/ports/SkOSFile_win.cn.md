# SkOSFile_win

> 源文件: [src/ports/SkOSFile_win.cpp](../../../../src/ports/SkOSFile_win.cpp)

## 概述

本文件实现了 Skia 文件操作抽象层中 Windows 平台特有的功能，包括文件同步、存在性检查、文件标识与比较、内存映射 (Windows Memory-Mapped Files)、快速读取以及目录迭代功能。它是 `SkOSFile_posix.cpp` 的 Windows 对应实现，使用 Windows API 替代 POSIX 调用。

## 架构位置

本文件与 `SkOSFile_stdio.cpp` 共同构成 Windows 平台上的完整文件操作层。

```
src/core/SkOSFile.h (文件操作声明)
  ├── SkOSFile_stdio.cpp  (跨平台标准 I/O)
  ├── SkOSFile_posix.cpp  (POSIX 平台特有)
  └── SkOSFile_win.cpp    (本文件: Windows 平台特有)
        ├── 文件同步 (_commit)
        ├── 内存映射 (CreateFileMapping/MapViewOfFile)
        ├── 文件标识 (BY_HANDLE_FILE_INFORMATION)
        └── 目录迭代 (FindFirstFileW/FindNextFileW)
```

仅在 `SK_BUILD_FOR_WIN` 宏定义时编译。

## 主要类与结构体

### SkFILEID

```cpp
typedef struct {
    ULONGLONG fVolume;   // 卷序列号
    ULONGLONG fLsbSize;  // 文件索引低位
    ULONGLONG fMsbSize;  // 文件索引高位 (当前固定为 0)
} SkFILEID;
```
使用卷序列号和文件索引的组合唯一标识一个文件。

### SkAutoNullKernelHandle

RAII 风格的 Windows 内核句柄封装，析构时调用 `CloseHandle()`。不可拷贝。
- 别名: `SkAutoWinMMap` — 用于内存映射句柄

### SkOSFileIterData

```cpp
struct SkOSFileIterData {
    HANDLE fHandle;      // FindFirstFile/FindNextFile 句柄
    uint16_t* fPath16;   // UTF-16 编码的搜索路径模式
};
```
目录迭代器的内部数据。

## 公共 API 函数

### 文件同步与存在性

| 函数签名 | 功能说明 |
|---------|---------|
| `void sk_fsync(FILE* f)` | 使用 `_commit()` 将文件缓冲区同步到磁盘 |
| `bool sk_exists(const char* path, SkFILE_Flags flags)` | 使用 `_access()` 检查文件存在性和权限 |

### 文件标识

| 函数签名 | 功能说明 |
|---------|---------|
| `bool sk_fidentical(FILE* a, FILE* b)` | 比较两个文件是否是同一个物理文件 |

### 内存映射

| 函数签名 | 功能说明 |
|---------|---------|
| `void* sk_fmmap(FILE* f, size_t* length)` | 将文件映射到内存 |
| `void* sk_fdmmap(int fileno, size_t* length)` | 通过文件号映射 |
| `void sk_fmunmap(const void* addr, size_t)` | 取消内存映射 |
| `int sk_fileno(FILE* f)` | 获取文件号 (`_fileno`) |

### 快速读取

| 函数签名 | 功能说明 |
|---------|---------|
| `size_t sk_qread(FILE*, void*, size_t count, size_t offset)` | 在指定偏移处读取数据 (使用 OVERLAPPED I/O) |

### 目录迭代

| 函数签名 | 功能说明 |
|---------|---------|
| `SkOSFile::Iter::Iter()` | 默认构造 |
| `SkOSFile::Iter::Iter(path, suffix)` | 带路径和后缀的构造 |
| `SkOSFile::Iter::~Iter()` | 析构，释放句柄和路径内存 |
| `void SkOSFile::Iter::reset(path, suffix)` | 重置迭代器 |
| `bool SkOSFile::Iter::next(name, getDir)` | 获取下一个匹配项 |

## 内部实现细节

### 内存映射 (sk_fdmmap)

1. 通过 `_get_osfhandle()` 将 C 运行时文件号转为 Windows HANDLE
2. 使用 `GetFileSizeEx()` 获取文件大小
3. 检查大小是否在 `size_t` 范围内 (`SkTFitsIn`)
4. 创建文件映射: `CreateFileMapping(file, nullptr, PAGE_READONLY, 0, 0, nullptr)`
5. 映射视图: `MapViewOfFile(mmap, FILE_MAP_READ, 0, 0, 0)`
6. `SkAutoWinMMap` 确保映射句柄在函数退出时关闭（视图仍有效）

取消映射使用 `UnmapViewOfFile(addr)`，忽略 `size` 参数（Windows API 不需要）。

### 快速读取 (sk_qread)

使用 Windows 的 `OVERLAPPED` 结构实现带偏移的读取:
- 将 `offset` 拆分为 `OVERLAPPED.Offset` (低 32 位) 和 `OffsetHigh` (高 32 位)
- 调用 `ReadFile()` 执行带偏移的读取
- 处理 `ERROR_HANDLE_EOF` 返回 0 字节
- 截断 `count` 到 `DWORD` 最大值

### 目录迭代

UTF-16 路径构建 (`concat_to_16`):
- 将 ASCII 路径转为 UTF-16 数组
- 追加 `/*` 和后缀构成搜索模式 (如 `path/*.png`)

迭代逻辑:
- 首次 `next()` 调用 `FindFirstFileW()` 开始搜索
- 后续调用 `FindNextFileW()` 继续
- `is_magic_dir()` 跳过 `.` 和 `..`
- 根据 `getDir` 参数过滤文件或目录
- `get_the_file()` 将 UTF-16 文件名转回 `SkString` (通过 `SkStringFromUTF16`)

### 文件标识 (sk_ino)

使用 `GetFileInformationByHandle()` 获取:
- `dwVolumeSerialNumber` — 卷序列号
- `nFileIndexLow` + `nFileIndexHigh` — 文件唯一索引

注释提到 Vista+ 应使用 `GetFileInformationByHandleEx` 的 `FileIdInfo` 获取更精确的标识。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkTypes.h` | 基础类型与平台宏 |
| `include/private/base/SkMalloc.h` | sk_malloc_throw, sk_free |
| `include/private/base/SkNoncopyable.h` | 不可拷贝基类 |
| `include/private/base/SkTFitsIn.h` | 类型范围检查 |
| `src/base/SkLeanWindows.h` | Windows 头文件精简包含 |
| `src/core/SkOSFile.h` | 函数声明 |
| `src/core/SkStringUtils.h` | SkStringFromUTF16 |
| `<io.h>` | _access, _fileno, _get_osfhandle |

## 设计模式与设计决策

1. **平台适配器**: 使用 Windows API 实现与 POSIX 版本相同的抽象接口
2. **RAII 句柄管理**: `SkAutoNullKernelHandle` 确保内核句柄在异常路径上也能正确关闭
3. **UTF-16 路径**: Windows API 使用宽字符路径 (`FindFirstFileW`)，通过手动转换处理
4. **OVERLAPPED I/O**: `sk_qread` 使用重叠 I/O 实现 `pread` 等效功能（Windows 无原生 `pread`）
5. **Placement New**: 目录迭代器内部数据通过 placement new 存储在固定大小缓冲区中

## 性能考量

- 内存映射避免用户/内核空间数据拷贝，适合大文件只读访问
- `sk_qread` 使用 OVERLAPPED 结构实现原子偏移读取，无需 SetFilePointer+ReadFile 组合
- 目录迭代使用 `FindFirstFileW/FindNextFileW`（W 变体直接支持 Unicode），避免 ANSI 转换
- `concat_to_16` 中使用 `sk_malloc_throw` 在堆上分配 UTF-16 路径，析构时释放

## 相关文件

- `src/core/SkOSFile.h` — 文件操作声明
- `src/ports/SkOSFile_stdio.cpp` — 标准 I/O 操作
- `src/ports/SkOSFile_posix.cpp` — POSIX 对应实现
- `src/base/SkLeanWindows.h` — Windows 头文件精简包含
- `src/core/SkStringUtils.h` — UTF-16 到 SkString 转换
