# SkOSFile_posix

> 源文件: [src/ports/SkOSFile_posix.cpp](../../../../src/ports/SkOSFile_posix.cpp)

## 概述

本文件实现了 Skia 文件操作抽象层中 POSIX 平台特有的功能，包括文件同步 (`fsync`)、文件存在性检查、文件标识与比较、内存映射 (mmap)、快速读取 (`pread`) 以及目录迭代功能。这些是 `SkOSFile_stdio.cpp` 中标准 I/O 操作的补充，提供了 POSIX 系统独有的高性能文件操作能力。

## 架构位置

本文件与 `SkOSFile_stdio.cpp` 共同构成 POSIX 平台上完整的文件操作实现。`SkOSFile_win.cpp` 提供了对应的 Windows 实现。

```
src/core/SkOSFile.h (文件操作声明)
  ├── SkOSFile_stdio.cpp  (跨平台标准 I/O)
  ├── SkOSFile_posix.cpp  (本文件: POSIX 特有操作)
  │     ├── 文件同步/存在性检查
  │     ├── 内存映射 (mmap/munmap)
  │     ├── 文件标识 (inode)
  │     └── 目录迭代 (opendir/readdir)
  └── SkOSFile_win.cpp    (Windows 特有操作)
```

## 主要类与结构体

### SkFILEID

```cpp
typedef struct {
    dev_t dev;  // 设备号
    ino_t ino;  // inode 号
} SkFILEID;
```

用于唯一标识一个文件，通过设备号和 inode 号的组合区分不同文件。

### SkOSFileIterData

```cpp
struct SkOSFileIterData {
    DIR* fDIR;         // 目录句柄
    SkString fPath;    // 目录路径
    SkString fSuffix;  // 文件后缀过滤
};
```

目录迭代器的内部数据，使用就地构造 (placement new) 存储在 `SkOSFile::Iter` 的固定大小缓冲区 `fSelf` 中。

## 公共 API 函数

### 文件同步与存在性

| 函数签名 | 功能说明 |
|---------|---------|
| `void sk_fsync(FILE* f)` | 将文件缓冲区同步到磁盘（Android 和部分 libc 变体除外） |
| `bool sk_exists(const char* path, SkFILE_Flags flags)` | 检查文件是否存在及具有指定的读写权限 |

### 文件标识

| 函数签名 | 功能说明 |
|---------|---------|
| `bool sk_fidentical(FILE* a, FILE* b)` | 判断两个 FILE 指针是否指向同一文件 |

### 内存映射

| 函数签名 | 功能说明 |
|---------|---------|
| `void* sk_fmmap(FILE* f, size_t* size)` | 将文件内存映射为只读区域 |
| `void* sk_fdmmap(int fd, size_t* size)` | 通过文件描述符进行内存映射 |
| `void sk_fmunmap(const void* addr, size_t length)` | 取消内存映射 |
| `int sk_fileno(FILE* f)` | 获取文件描述符 |

### 快速读取

| 函数签名 | 功能说明 |
|---------|---------|
| `size_t sk_qread(FILE* file, void* buffer, size_t count, size_t offset)` | 在指定偏移处读取数据（基于 `pread`，不改变文件位置） |

### 目录迭代

| 函数签名 | 功能说明 |
|---------|---------|
| `SkOSFile::Iter::Iter()` | 默认构造函数 |
| `SkOSFile::Iter::Iter(const char path[], const char suffix[])` | 指定路径和后缀的构造函数 |
| `SkOSFile::Iter::~Iter()` | 析构函数，关闭目录句柄 |
| `void SkOSFile::Iter::reset(const char path[], const char suffix[])` | 重置迭代器到新路径 |
| `bool SkOSFile::Iter::next(SkString* name, bool getDir)` | 获取下一个匹配的文件或目录 |

## 内部实现细节

### sk_exists - 文件存在性检查

- 使用 POSIX `access()` 系统调用检查文件存在性和权限
- iOS 平台: 默认路径检查失败后，回退到 Bundle 内查找（仅只读模式）
- 将 `SkFILE_Flags` 映射为 `access()` 的 `R_OK` / `W_OK` 标志

### sk_fdmmap - 内存映射实现

1. 通过 `fstat()` 获取文件大小和类型
2. 验证是否为常规文件 (`S_ISREG`)
3. 验证文件大小不超过 `size_t` 范围 (`SkTFitsIn`)
4. 调用 `mmap()` 以 `PROT_READ | MAP_PRIVATE` 映射
5. 映射失败返回 `nullptr`

### 目录迭代器

- 使用 `opendir()`/`readdir()`/`closedir()` POSIX API
- 通过 `stat()` 判断条目是文件还是目录
- `issuffixfor()` 辅助函数实现后缀过滤（空后缀匹配所有文件）
- iOS 平台: 目录打开失败后尝试 Bundle 内路径
- 使用 placement new 在固定大小缓冲区中构造 `SkOSFileIterData`

### sk_fsync - 条件编译

在 Android、uClibc 和 Newlib 环境下被禁用，因为这些环境中 `fsync` 可能不可用或行为不一致。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkString.h` | Skia 字符串类 |
| `include/core/SkTypes.h` | 基础类型 |
| `include/private/base/SkTFitsIn.h` | 安全类型范围检查 |
| `include/private/base/SkTemplates.h` | 模板工具 |
| `src/core/SkOSFile.h` | 函数声明 |
| `<dirent.h>` | 目录操作 |
| `<sys/mman.h>` | 内存映射 |
| `<sys/stat.h>` | 文件状态 |
| `<unistd.h>` | POSIX 基础 API |
| `src/ports/SkOSFile_ios.h` | iOS Bundle 路径 (条件编译) |

## 设计模式与设计决策

1. **平台抽象**: `sk_*` 前缀函数统一包装 POSIX API，上层代码无需直接使用系统调用
2. **Placement New**: 目录迭代器的内部数据通过 placement new 构造在预分配的固定大小缓冲区中，避免额外堆分配
3. **两级文件标识**: 使用 `dev_t + ino_t` 组合唯一标识文件，正确处理硬链接场景
4. **iOS 回退机制**: 文件存在性检查和目录迭代都包含 Bundle 路径回退逻辑
5. **防御性编程**: `sk_fdmmap` 中多层验证（文件类型、大小范围、映射结果）

## 性能考量

- **mmap**: 内存映射避免了 `read()` 的内核-用户空间数据拷贝，适合大文件的只读访问
- **pread (sk_qread)**: 支持带偏移的原子读取，不修改文件位置，线程安全且避免了 `lseek + read` 的竞态
- **stat 调用**: 目录迭代中每个条目都调用 `stat()` 判断类型，对大目录可能有性能影响
- **编译时禁用 fsync**: 在不支持或不需要的平台上跳过 fsync，避免不必要的系统调用

## 相关文件

- `src/core/SkOSFile.h` — 文件操作声明
- `src/ports/SkOSFile_stdio.cpp` — 标准 I/O 操作
- `src/ports/SkOSFile_win.cpp` — Windows 平台对应实现
- `src/ports/SkOSFile_ios.h` — iOS Bundle 路径辅助
