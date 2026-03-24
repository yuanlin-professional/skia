# SkPath_serial

> 源文件
> - src/core/SkPath_serial.cpp

## 概述

`SkPath_serial.cpp` 实现了 Skia 路径的序列化和反序列化功能。它提供了将 `SkPath` 对象编码为二进制数据（内存或流）以及从二进制数据重建路径的能力。该模块支持多种优化，包括特殊的圆角矩形（RRect）快速序列化路径、版本兼容性处理、以及严格的数据验证。序列化后的路径可以用于跨进程通信、持久化存储或网络传输。

## 架构位置

`SkPath_serial` 位于 Skia 核心路径系统的序列化层：

- 位于 `src/core` 目录，作为 `SkPath` 的序列化实现
- 与路径数据结构（`SkPathRef`）紧密集成
- 支持 `SkRRect` 的优化序列化路径
- 使用 Skia 的缓冲区工具（`SkBuffer`）进行数据读写
- 为跨进程渲染和数据持久化提供基础能力

## 主要类与结构体

该文件不定义公开的类或结构体，而是为 `SkPath` 提供序列化相关的方法实现。

### 内部枚举

#### SerializationOffsets

定义序列化头部各字段的位偏移：

```cpp
enum SerializationOffsets {
    kType_SerializationShift = 28,       // 4位：序列化类型
    kDirection_SerializationShift = 26,  // 2位：路径方向
    kFillType_SerializationShift = 8,    // 8位：填充类型
    kVersion_SerializationMask = 0xFF,   // 低8位：版本号
};
```

#### SerializationVersions

定义支持的序列化版本：

```cpp
enum SerializationVersions {
    kJustPublicData_Version = 4,            // 2018年2月引入
    kVerbsAreStoredForward_Version = 5,     // 2019年9月引入
    kMin_Version     = kJustPublicData_Version,
    kCurrent_Version = kVerbsAreStoredForward_Version
};
```

#### SerializationType

定义序列化类型：

```cpp
enum SerializationType {
    kGeneral = 0,    // 通用路径
    kRRect = 1       // 圆角矩形优化路径
};
```

## 公共 API 函数

### SkPath::writeToMemory

```cpp
size_t SkPath::writeToMemory(void* storage) const;
```

将路径序列化到内存缓冲区：

- `storage`: 目标内存缓冲区指针（可以为 `nullptr` 以查询所需大小）
- 返回值：写入的字节数
- 如果 `storage` 为 `nullptr`，返回所需的缓冲区大小
- 自动选择最优序列化格式（RRect 或通用）

### SkPath::serialize

```cpp
sk_sp<SkData> SkPath::serialize() const;
```

将路径序列化为 `SkData` 对象：

- 返回包含序列化数据的智能指针
- 自动分配内存
- 便利函数，内部调用 `writeToMemory`

### SkPath::ReadFromMemory (静态)

```cpp
static std::optional<SkPath> SkPath::ReadFromMemory(const void* storage, size_t length, size_t* bytesRead);
```

从内存缓冲区反序列化路径：

- `storage`: 源内存缓冲区指针
- `length`: 缓冲区长度
- `bytesRead`: 可选的输出参数，返回实际读取的字节数
- 返回值：`std::optional<SkPath>`，失败时返回空 optional
- 支持版本兼容性处理

## 内部实现细节

### RRect 优化序列化

`writeToMemoryAsRRect` 函数为圆角矩形提供优化的序列化路径：

**检测条件**

```cpp
if (auto oinfo = this->getOvalInfo()) {
    rrect.setOval(oinfo->fBounds);
    // ...
} else if (auto rinfo = this->getRRectInfo()) {
    rrect = rinfo->fRRect;
    // ...
}
```

检测路径是否为椭圆或圆角矩形。

**序列化格式**

```
[Packed Header: 4 bytes]
[RRect Data: SkRRect::kSizeInMemory bytes]
[Start Index: 4 bytes]
[Padding: 对齐到4字节]
```

**优势**

- 比通用格式更紧凑
- 快速识别和优化渲染
- 保留语义信息（RRect 而非普通路径）

### 通用路径序列化

`writeToMemory` 函数处理通用路径：

**序列化格式**

```
[Packed Header: 4 bytes]
[Point Count: 4 bytes]
[Conic Count: 4 bytes]
[Verb Count: 4 bytes]
[Points: count * sizeof(SkPoint)]
[Conics: count * sizeof(float)]
[Verbs: count * sizeof(uint8_t)]
[Padding: 对齐到4字节]
```

**Packed Header 结构**

```cpp
int32_t packed = (static_cast<int>(fFillType) << kFillType_SerializationShift) |
                 (SerializationType::kGeneral << kType_SerializationShift) |
                 kCurrent_Version;
```

位域包含：

- 填充类型（8位）
- 序列化类型（4位）
- 版本号（8位）

### RRect 反序列化

`read_rrect_path` 函数处理 RRect 序列化格式的反序列化：

**步骤**

1. 读取并解析 packed header
2. 提取方向和填充类型
3. 读取 RRect 数据
4. 读取起始索引并验证范围（0-7）
5. 使用 `SkPath::RRect` 构造路径
6. 设置填充类型并对齐

**方向转换**

```cpp
switch (dir) {
    case (int)SkPathFirstDirection::kCW:
        rrectDir = SkPathDirection::kCW;
        break;
    case (int)SkPathFirstDirection::kCCW:
        rrectDir = SkPathDirection::kCCW;
        break;
    default:
        return {};  // 无效方向
}
```

### 通用路径反序列化

`ReadFromMemory` 函数处理通用序列化格式：

**版本检查**

```cpp
unsigned version = extract_version(packed);
const bool verbsAreForward = (version == kVerbsAreStoredForward_Version);
if (!verbsAreForward && version != kJustPublicData_Version) {
    return {};  // 不支持的版本
}
```

支持版本 4 和 5，版本 5 动词存储方向为正向。

**动词方向处理**

对于版本 4（动词反向存储），需要反转动词数组：

```cpp
SkAutoMalloc reversedStorage;
if (!verbsAreForward) {
    SkPathVerb* tmpVerbs = (SkPathVerb*)reversedStorage.reset(counts.vbs);
    for (unsigned i = 0; i < counts.vbs; ++i) {
        tmpVerbs[i] = verbs[counts.vbs - i - 1];
    }
    verbs = tmpVerbs;
}
```

**空路径处理**

```cpp
if (counts.vbs == 0) {
    if (counts.pts == 0 && counts.cnx == 0) {
        SkPath path(extract_filltype(packed));
        *bytesRead = buffer.pos();
        return path;
    }
    return {};  // 无效：有点但无动词
}
```

### 数据验证

反序列化过程中进行多重验证：

**缓冲区有效性**

```cpp
if (!buffer.isValid()) {
    *bytesRead = 0;
    return {};
}
```

**起始索引范围**

```cpp
if (!buffer.readS32(&start) || start != SkTPin(start, 0, 7)) {
    *bytesRead = 0;
    return {};
}
```

**数据一致性**

- 验证点、圆锥曲线、动词的数量
- 检查缓冲区是否有足够数据
- 确保没有点但有动词的情况不会发生

### 内存安全

使用 `SkSafeMath` 防止整数溢出：

```cpp
SkSafeMath safe;
size_t size = 4 * sizeof(int32_t);
size = safe.add(size, safe.mul(pts, sizeof(SkPoint)));
size = safe.add(size, safe.mul(cnx, sizeof(float)));
size = safe.add(size, safe.mul(vbs, sizeof(uint8_t)));
size = safe.alignUp(size, 4);
if (!safe) {
    return 0;
}
```

如果计算过程中发生溢出，`safe` 变为 false，函数返回错误。

### 对齐处理

所有序列化数据对齐到 4 字节边界：

```cpp
buffer.padToAlign4();
```

确保数据在所有平台上都能正确读取。

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkPath` | 路径类，序列化的目标对象 |
| `SkData` | 序列化数据存储 |
| `SkRRect` | 圆角矩形，优化序列化对象 |
| `SkPathRef` | 路径内部数据表示 |
| `SkBuffer` | 二进制读写工具（`SkWBuffer`、`SkRBuffer`） |
| `SkSafeMath` | 安全数学运算，防止溢出 |
| `SkAutoMalloc` | 自动内存管理 |
| `SkPathPriv` | 路径私有辅助函数 |
| `SkRRectPriv` | RRect 私有辅助函数 |

**被依赖的模块**

| 模块 | 关系 |
|------|------|
| 跨进程渲染 | 序列化路径用于进程间通信 |
| 缓存系统 | 序列化路径用于持久化缓存 |
| 网络传输 | 序列化路径用于数据传输 |
| 文件格式 | 序列化路径用于文件保存 |

## 设计模式与设计决策

### 策略模式

序列化类型选择使用策略模式：

- RRect 优化路径：针对常见形状的特殊处理
- 通用路径：适用于所有路径的标准格式
- 运行时自动选择最优策略

### 版本兼容性

支持多版本反序列化：

- 向前兼容：可以读取旧版本数据
- 版本检查和拒绝不支持的版本
- 动词方向转换处理版本差异

### 可选返回值

使用 `std::optional<SkPath>` 表示可能失败的反序列化：

- 明确表达"可能无结果"的语义
- 避免异常或特殊值
- 类型安全的错误处理

### 查询-然后-写模式

`writeToMemory` 支持查询所需大小：

```cpp
size_t size = path.writeToMemory(nullptr);  // 查询大小
void* buffer = malloc(size);
path.writeToMemory(buffer);                  // 写入数据
```

允许调用者分配正确大小的缓冲区。

### 防御式编程

多层验证和错误检查：

- 缓冲区边界检查
- 数据一致性验证
- 整数溢出保护
- 无效状态检测

### 位域压缩

使用位域压缩 packed header：

- 减少序列化大小
- 快速提取字段
- 保持向前兼容性

## 性能考量

### RRect 优化

RRect 序列化显著减少数据量：

- RRect 数据结构紧凑
- 避免存储大量路径点和动词
- 快速识别和处理

### 单次内存分配

`serialize()` 函数：

```cpp
sk_sp<SkData> SkPath::serialize() const {
    size_t size = this->writeToMemory(nullptr);
    sk_sp<SkData> data = SkData::MakeUninitialized(size);
    this->writeToMemory(data->writable_data());
    return data;
}
```

查询大小后一次性分配，避免多次分配。

### 对齐优化

4 字节对齐确保：

- 在所有平台上高效访问
- 避免未对齐访问的性能损失
- 简化跨平台兼容性

### 零拷贝读取

反序列化直接使用缓冲区中的数据：

```cpp
const SkPoint* points = buffer.skipCount<SkPoint>(counts.pts);
const SkScalar* conics = buffer.skipCount<SkScalar>(counts.cnx);
const SkPathVerb* verbs = buffer.skipCount<SkPathVerb>(counts.vbs);
```

使用 `skipCount` 返回指针，避免拷贝数据。

### 提前返回

多处提前返回避免不必要的计算：

- 无效版本立即返回
- 缓冲区不足立即返回
- 数据一致性检查失败立即返回

### 适用场景

最佳使用场景：

- 跨进程路径传输（如 Chrome GPU 进程）
- 路径缓存持久化
- 网络传输矢量图形
- 路径数据压缩存储

### 性能权衡

- **优势**：紧凑格式，快速序列化/反序列化
- **劣势**：序列化和反序列化有一定开销
- **权衡**：适合需要传输或存储路径的场景

### 内存占用

序列化数据大小：

- **RRect 路径**: 约 40-50 字节
- **通用路径**: 取决于点和动词数量
  - 头部：16 字节
  - 点：每个 8 字节（2D 坐标）
  - 圆锥曲线权重：每个 4 字节
  - 动词：每个 1 字节
  - 对齐填充：最多 3 字节

### 安全性考量

防范恶意或损坏的序列化数据：

- 整数溢出保护（`SkSafeMath`）
- 缓冲区边界检查
- 数据一致性验证
- 范围检查（如起始索引 0-7）

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/core/SkPath.h` | 路径类定义和接口声明 |
| `include/private/SkPathRef.h` | 路径内部数据表示 |
| `include/core/SkRRect.h` | 圆角矩形定义 |
| `src/core/SkRRectPriv.h` | RRect 私有辅助函数 |
| `src/base/SkBuffer.h` | 二进制缓冲区工具 |
| `src/base/SkSafeMath.h` | 安全数学运算 |
| `src/base/SkAutoMalloc.h` | 自动内存管理 |
| `src/core/SkPathPriv.h` | 路径私有辅助函数 |
| `include/core/SkData.h` | 数据容器 |
| `src/core/SkPathEnums.h` | 路径枚举（填充类型、方向等） |
