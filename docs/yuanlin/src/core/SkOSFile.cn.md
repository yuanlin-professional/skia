# SkOSFile

> 源文件: src/core/SkOSFile.h

## 概述

`SkOSFile` 提供了 Skia 的跨平台文件系统操作抽象层，封装了文件的打开、读取、写入、映射、查询和目录遍历等功能。该模块通过统一的接口屏蔽了不同操作系统（Windows、Linux、macOS、Android 等）在文件操作上的差异，使上层代码能够使用一致的 API 进行文件操作。

该文件主要提供 C 风格的函数接口以及 `SkOSFile::Iter` 类用于目录遍历，是 Skia 文件 I/O 的基础设施。

## 架构位置

`SkOSFile` 位于 Skia 核心层的平台抽象层：

- **所属模块**: `src/core/` - 核心实现
- **层级定位**: 操作系统抽象层（OS Abstraction Layer）
- **实现位置**: `src/ports/SkOSFile_*.cpp`（针对不同平台）
- **使用范围**: 图像解码、资源加载、字体文件访问

## 主要类与结构体

### SkFILE_Flags 枚举

```cpp
enum SkFILE_Flags {
    kRead_SkFILE_Flag   = 0x01,  // 读模式
    kWrite_SkFILE_Flag  = 0x02   // 写模式
};
```

**说明**: 文件打开模式标志，可通过位或组合。

### SkOSFile::Iter 类

**继承关系**: 无继承（独立类）

**用途**: 遍历目录中的文件和子目录。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSelf` | `char[40]` | 不透明的平台特定实现存储 |

**存储策略**: 使用固定大小的字节数组存储平台特定的迭代器状态（如 Windows 的 `WIN32_FIND_DATA` 或 POSIX 的 `DIR*`），避免动态分配。

## 公共 API 函数

### 文件基本操作

| 函数签名 | 说明 |
|---------|------|
| `FILE* sk_fopen(const char path[], SkFILE_Flags)` | 打开文件，返回文件指针 |
| `void sk_fclose(FILE*)` | 关闭文件 |
| `size_t sk_fgetsize(FILE*)` | 获取文件大小（字节） |
| `size_t sk_fwrite(const void* buffer, size_t byteCount, FILE*)` | 写入数据到文件 |
| `void sk_fflush(FILE*)` | 刷新文件缓冲区到磁盘 |
| `void sk_fsync(FILE*)` | 同步文件数据到磁盘（强制写入） |
| `size_t sk_ftell(FILE*)` | 获取当前文件位置指针 |

**注意**: 这些函数是标准 C 文件函数的跨平台封装。

### 内存映射

| 函数签名 | 说明 |
|---------|------|
| `void* sk_fmmap(FILE* f, size_t* length)` | 将文件映射到内存（只读） |
| `void* sk_fdmmap(int fd, size_t* length)` | 通过文件描述符映射文件到内存 |
| `void sk_fmunmap(const void* addr, size_t length)` | 解除文件映射 |

**返回值**: 成功返回内存地址，失败返回 `nullptr`。

**注意事项**:
- 映射是只读的
- 必须使用相同的 `length` 调用 `sk_fmunmap`
- 映射失败可能因为文件过大或系统资源不足

### 文件查询

| 函数签名 | 说明 |
|---------|------|
| `bool sk_fidentical(FILE* a, FILE* b)` | 判断两个文件指针是否指向同一文件 |
| `int sk_fileno(FILE* f)` | 获取文件的底层文件描述符 |
| `bool sk_exists(const char *path, SkFILE_Flags = (SkFILE_Flags)0)` | 检查路径是否存在并具有指定访问权限 |
| `bool sk_isdir(const char *path)` | 检查路径是否为目录 |

**sk_exists 参数说明**:
- 传递 `SkFILE_Flags` 可检查特定权限（如只读、只写）
- 默认参数 `0` 仅检查存在性

### 定位读取

```cpp
size_t sk_qread(FILE* f, void* buffer, size_t count, size_t offset)
```

**功能**: 从指定偏移量读取数据（类似 POSIX `pread`）。

**返回值**:
- 成功: 读取的字节数
- 失败: `SIZE_MAX`

**注意**: 可能影响文件位置指针（不保证原子性）。

### 目录操作

```cpp
bool sk_mkdir(const char* path)
```

**功能**: 创建目录。

**返回值**:
- `true`: 创建成功或目录已存在
- `false`: 创建失败（错误信息输出到 stderr）

**行为**: 仅创建单层目录（不递归创建父目录）。

### 目录遍历 (SkOSFile::Iter)

#### 构造与析构

```cpp
Iter();  // 默认构造（空迭代器）
Iter(const char path[], const char suffix[] = nullptr);  // 初始化到指定目录
~Iter();  // 析构，释放资源
```

**参数说明**:
- `path`: 要遍历的目录路径
- `suffix`: 可选的文件后缀过滤器（如 `".txt"`）

#### 迭代方法

```cpp
void reset(const char path[], const char suffix[] = nullptr);
```

**功能**: 重置迭代器到新目录。

```cpp
bool next(SkString* name, bool getDir = false);
```

**功能**: 获取下一个文件或目录。

**参数**:
- `name`: 输出参数，存储文件/目录名（不含路径）
- `getDir`: `true` 仅返回目录，`false` 返回文件

**返回值**:
- `true`: 成功获取下一项
- `false`: 遍历结束或错误

**注意**: 不要在同一迭代器上混合 `getDir=true` 和 `getDir=false` 的调用（结果未定义）。

#### 实现细节

```cpp
static const size_t kStorageSize = 40;
private:
    alignas(void*) alignas(double) char fSelf[kStorageSize];
```

**设计说明**:
- 使用对齐的字节数组存储平台特定状态
- `alignas(void*)` 确保能存储指针
- `alignas(double)` 确保能存储双精度浮点数
- 40 字节足够存储 Windows `HANDLE` + 路径缓冲区或 POSIX `DIR*` + `dirent`

## 内部实现细节

### 1. 平台特定实现

每个平台有独立的实现文件：

- **Windows**: `src/ports/SkOSFile_win.cpp`
  - 使用 `CreateFile`, `FindFirstFile`, `FindNextFile`
  - 文件映射使用 `CreateFileMapping` 和 `MapViewOfFile`

- **POSIX (Linux/macOS)**: `src/ports/SkOSFile_posix.cpp`
  - 使用 `fopen`, `opendir`, `readdir`
  - 文件映射使用 `mmap`

- **Android**: 可能有特殊处理（资产文件系统）

### 2. 文件打开实现示例（伪代码）

```cpp
// Windows 实现
FILE* sk_fopen(const char path[], SkFILE_Flags flags) {
    const char* mode;
    if (flags == kRead_SkFILE_Flag) mode = "rb";
    else if (flags == kWrite_SkFILE_Flag) mode = "wb";
    else if (flags == (kRead_SkFILE_Flag | kWrite_SkFILE_Flag)) mode = "rb+";
    return fopen(path, mode);
}

// POSIX 实现类似
```

### 3. 内存映射实现策略

```cpp
// POSIX 伪代码
void* sk_fmmap(FILE* f, size_t* length) {
    int fd = fileno(f);
    struct stat sb;
    if (fstat(fd, &sb) == -1) return nullptr;

    *length = sb.st_size;
    void* addr = mmap(nullptr, *length, PROT_READ, MAP_PRIVATE, fd, 0);
    return (addr == MAP_FAILED) ? nullptr : addr;
}

void sk_fmunmap(const void* addr, size_t length) {
    munmap(const_cast<void*>(addr), length);
}
```

### 4. 文件相同性检测

```cpp
// POSIX 伪代码
bool sk_fidentical(FILE* a, FILE* b) {
    struct stat sa, sb;
    if (fstat(fileno(a), &sa) != 0) return false;
    if (fstat(fileno(b), &sb) != 0) return false;
    return (sa.st_dev == sb.st_dev) && (sa.st_ino == sb.st_ino);
}
```

使用 inode 和设备号判断（POSIX），Windows 使用文件索引。

### 5. 目录遍历实现（POSIX 示例）

```cpp
struct IterImpl {
    DIR* dir;
    SkString suffix;
};

Iter::Iter(const char path[], const char suffix[]) {
    static_assert(sizeof(IterImpl) <= kStorageSize);
    IterImpl* impl = reinterpret_cast<IterImpl*>(fSelf);
    impl->dir = opendir(path);
    if (suffix) impl->suffix = suffix;
}

bool Iter::next(SkString* name, bool getDir) {
    IterImpl* impl = reinterpret_cast<IterImpl*>(fSelf);
    while (struct dirent* entry = readdir(impl->dir)) {
        if (getDir && entry->d_type != DT_DIR) continue;
        if (!getDir && entry->d_type == DT_DIR) continue;
        if (!impl->suffix.isEmpty() && !endsWith(entry->d_name, impl->suffix)) continue;
        *name = entry->d_name;
        return true;
    }
    return false;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkString.h` | 字符串存储（`Iter::next` 返回） |
| `include/private/base/SkTemplates.h` | 模板工具 |
| `<stdio.h>` | C 标准 I/O 函数 |
| `<sys/stat.h>` (POSIX) | 文件状态查询 |
| `<sys/mman.h>` (POSIX) | 内存映射 |
| `<windows.h>` (Windows) | Windows API |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `src/codec/SkCodec.cpp` | 图像解码器读取文件 |
| `src/images/SkImageEncoder.cpp` | 图像编码器写入文件 |
| `src/ports/SkFontMgr_*.cpp` | 字体管理器扫描字体目录 |
| `src/utils/SkOSPath.cpp` | 路径操作配合文件操作 |
| `tools/` | 工具程序的文件 I/O |
| `tests/` | 测试代码的文件访问 |

## 设计模式与设计决策

### 1. 外观模式 (Facade Pattern)

封装复杂的平台特定文件操作，提供统一接口：

```cpp
// 用户代码无需关心平台差异
FILE* f = sk_fopen("image.png", kRead_SkFILE_Flag);
size_t size = sk_fgetsize(f);
sk_fclose(f);
```

### 2. RAII (Resource Acquisition Is Initialization)

虽然 C 风格函数不自动管理资源，但 `SkOSFile::Iter` 采用 RAII：

```cpp
{
    SkOSFile::Iter iter("dir");
    // 使用迭代器...
} // 析构函数自动关闭目录句柄
```

### 3. 不透明指针模式 (Opaque Pointer / Pimpl)

`Iter::fSelf` 使用固定大小缓冲区而非传统 pimpl：

**传统 Pimpl**:
```cpp
struct IterImpl;  // 前向声明
IterImpl* pImpl;  // 需要动态分配
```

**Skia 的方式**:
```cpp
alignas(...) char fSelf[40];  // 栈上分配，避免堆开销
```

**优势**:
- 无堆分配开销
- 缓存友好
- 简化生命周期管理

**代价**:
- 必须确保缓冲区足够大（静态断言检查）
- 需要 placement new（如果存储复杂对象）

### 4. 条件编译策略

不同平台使用不同的 `.cpp` 实现文件，通过构建系统选择：

```gn
# BUILD.gn 示例
if (is_win) {
  sources += [ "src/ports/SkOSFile_win.cpp" ]
} else {
  sources += [ "src/ports/SkOSFile_posix.cpp" ]
}
```

### 5. C 风格 API 选择

**设计决策**: 使用全局函数而非类方法。

**理由**:
- 与标准 C 库 `FILE*` API 一致
- 无状态（除了 `Iter`）
- 简单直接，易于理解和使用

### 6. 内存映射只读策略

**设计决策**: `sk_fmmap` 仅支持只读映射。

**理由**:
- Skia 主要读取资源（图像、字体）
- 只读映射更安全（防止意外修改）
- 跨平台实现更简单

### 7. 错误处理策略

- **返回值指示**: 失败返回 `nullptr`, `SIZE_MAX`, `false`
- **错误日志**: `sk_mkdir` 失败时输出到 stderr
- **无异常**: C 风格接口不抛出异常

## 性能考量

### 1. 内存映射优势

```cpp
void* data = sk_fmmap(f, &size);
```

**优势**:
- 零拷贝访问文件数据
- 操作系统自动管理页面缓存
- 支持大文件（超过可用内存）

**适用场景**:
- 只读访问大型图像文件
- 字体文件解析
- 资源打包文件

**限制**:
- 32 位系统地址空间限制（最大约 2-3 GB）
- 内存碎片问题

### 2. Iter 栈上分配

`SkOSFile::Iter` 使用固定大小缓冲区：

**优势**:
- 无堆分配开销（malloc 约 50-200 纳秒）
- 缓存局部性好
- 析构自动清理

**代价**:
- 限制了平台特定数据的大小（40 字节）
- 需要保守估计最大大小

### 3. 文件大小查询

`sk_fgetsize` 可能使用 `fseek`/`ftell` 或 `fstat`：

**fstat 方式** (更快):
```cpp
struct stat sb;
fstat(fileno(f), &sb);
return sb.st_size;
```

**fseek 方式** (较慢):
```cpp
long pos = ftell(f);
fseek(f, 0, SEEK_END);
size_t size = ftell(f);
fseek(f, pos, SEEK_SET);
return size;
```

### 4. sk_qread 性能

- 类似 `pread`，避免改变文件指针
- 但实现可能使用 `fseek` + `fread`，不是真正的原子操作
- 多线程场景需要外部同步

### 5. 目录遍历缓存

`readdir` 的性能取决于文件系统：
- **本地文件系统**: 通常很快（微秒级）
- **网络文件系统**: 可能慢（毫秒级）
- **大目录**: 线性扫描，O(n) 复杂度

**优化策略**:
- 使用后缀过滤减少匹配次数
- 缓存目录列表（如果需要多次访问）

### 6. 跨平台开销

平台抽象层会引入轻微开销（函数调用），但通常可忽略（内联优化）。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/ports/SkOSFile_posix.cpp` | POSIX 平台实现（Linux, macOS, Android） |
| `src/ports/SkOSFile_win.cpp` | Windows 平台实现 |
| `src/utils/SkOSPath.h` | 路径操作辅助函数 |
| `include/core/SkString.h` | 字符串类（`Iter::next` 使用） |
| `src/codec/SkCodec.h` | 图像解码器（使用文件操作） |
| `src/ports/SkFontMgr_fontconfig.cpp` | Linux 字体管理器（使用目录遍历） |
| `src/ports/SkFontMgr_win.cpp` | Windows 字体管理器 |
| `src/ports/SkFontHost_mac.cpp` | macOS 字体管理器 |
| `tools/flags/CommandLineFlags.cpp` | 命令行工具（使用文件检查） |
| `tests/OSPathTest.cpp` | 文件操作测试 |

### 典型使用示例

#### 示例 1: 读取文件到内存

```cpp
FILE* f = sk_fopen("image.png", kRead_SkFILE_Flag);
if (!f) return;

size_t size;
void* data = sk_fmmap(f, &size);
if (data) {
    // 使用 data...
    sk_fmunmap(data, size);
}
sk_fclose(f);
```

#### 示例 2: 遍历目录中的图像文件

```cpp
SkOSFile::Iter iter("images", ".png");
SkString name;
while (iter.next(&name)) {
    SkString path = SkOSPath::Join("images", name.c_str());
    // 处理图像文件...
}
```

#### 示例 3: 检查并创建目录

```cpp
if (!sk_isdir("output")) {
    if (!sk_mkdir("output")) {
        // 创建失败
    }
}
```

## 扩展性考虑

### 当前限制

1. **不支持递归创建目录**: `sk_mkdir` 只创建单层
2. **无文件写入抽象**: 依赖标准 `fwrite`
3. **无异步 I/O**: 所有操作是同步的
4. **内存映射只读**: 不支持可写映射
5. **无符号链接处理**: 行为依赖平台

### 潜在改进方向

1. **异步文件 I/O**: 使用线程池或 OS 异步 API
2. **流式读取**: 支持大文件的分块处理
3. **更丰富的错误信息**: 返回错误码而非布尔值
4. **现代 C++ 封装**: RAII 文件句柄包装类
5. **虚拟文件系统**: 支持内存文件系统、压缩包等

这些改进在当前 Skia 的使用场景中不是必需的，但可能在未来扩展时考虑。
