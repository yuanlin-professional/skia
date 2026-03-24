# BufferWriter

> 源文件: src/gpu/BufferWriter.h

## 概述

`BufferWriter` 是 Skia GPU 模块中用于高效写入缓冲区的核心工具类族。它提供了类型安全、零拷贝的缓冲区写入接口,专为顶点数据、索引数据和纹理上传等场景设计。该模块包含三个主要类:`BufferWriter`(基类)、`VertexWriter`(顶点数据)、`IndexWriter`(索引数据)和 `TextureUploadWriter`(纹理数据),每个类针对特定场景优化。

核心设计思想是:通过预分配的缓冲区和流式写入接口,避免临时内存分配和数据拷贝,同时提供编译时类型检查,确保写入的数据类型与顶点格式匹配。该模块大量使用模板和操作符重载,提供了优雅的 C++ 风格 API。

## 架构位置

在 Skia 架构中,`BufferWriter` 位于以下位置:

- **基础设施层**: 为 GPU 渲染管线提供缓冲区写入工具
- **上游使用**: 被几何生成器、网格构建器、纹理上传路径使用
- **性能关键路径**: 处于渲染热路径,写入频率极高
- **跨后端**: Ganesh 和 Graphite 都使用该工具

该模块是平台无关的头文件,所有函数都是内联的,以实现零抽象开销。

## 主要类与结构体

### BufferWriter (基类)

通用缓冲区写入器基类。

**继承关系**: 无继承,但作为 `VertexWriter`、`IndexWriter` 等的基类。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fPtr` | `void*` | 当前写入位置指针 |
| `fEnd` | `Mark` (调试) | 缓冲区结束标记 |

**嵌套类型 - Mark**:
```cpp
struct Mark {
    uintptr_t fMark;  // 缓冲区位置的整数表示
};
```
**用途**: 标记缓冲区中的位置,支持比较和偏移计算。

### VertexWriter

专为顶点数据写入设计的流式写入器。

**继承关系**: 继承自 `BufferWriter`。

**设计特点**:
- 支持 `<<` 操作符流式写入
- 支持条件写入 (`If`)
- 支持数组和重复写入 (`Array`, `Repeat`)
- 支持四边形顶点批量写入 (`writeQuad`)

**特殊常量**:
```cpp
static constexpr uint32_t kIEEE_32_infinity = 0x7f800000;
```
**用途**: 用于表示无效或特殊顶点(如退化三角形)。

### IndexWriter

专为索引数据写入设计的写入器。

**继承关系**: 继承自 `BufferWriter`。

**特点**:
- 只支持 `uint16_t` 索引(Skia 的标准)
- 提供数组批量写入 (`writeArray`)
- 支持 `<<` 操作符

### TextureUploadWriter

专为纹理数据上传设计的写入器。

**继承关系**: 继承自 `BufferWriter`。

**特点**:
- 支持带行字节数的矩形区域写入
- 支持像素格式转换
- 支持 RGB888x 到 RGB888 的紧凑转换

### VertexColor

辅助类,用于写入颜色数据到顶点缓冲区。

**成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fColor` | `uint32_t[4]` | 颜色数据(4字节或16字节) |
| `fWideColor` | `bool` | 是否为宽颜色(float32) |

**用途**: 根据着色器需求,自动选择字节或浮点颜色格式。

## 公共 API 函数

### BufferWriter 核心函数

#### 构造函数
```cpp
BufferWriter(void* ptr, size_t size)
BufferWriter(void* ptr, Mark end)
```
**功能**: 创建缓冲区写入器。
**参数**:
- `ptr`: 缓冲区起始指针
- `size`: 缓冲区大小(字节)
- `end`: 缓冲区结束标记

#### mark
```cpp
Mark mark(size_t offset=0) const
```
**功能**: 在当前位置(可带偏移)创建标记。
**返回**: `Mark` 对象,可用于后续验证或计算。

#### write
```cpp
void write(const void* src, size_t bytes)
template <typename T> void write(SkSpan<const T> data)
template <typename T> void write(T data)
```
**功能**: 写入原始数据到缓冲区。
**约束**: `T` 必须是 POD 类型(`std::is_trivially_copyable`)。

#### zeroBytes
```cpp
void zeroBytes(size_t bytes)
```
**功能**: 写入零字节(用于填充或初始化)。

### VertexWriter 特有函数

#### 流式写入操作符
```cpp
template <typename T>
VertexWriter& operator<<(VertexWriter& w, const T& val)
```
**功能**: 流式写入任意 POD 类型。
**示例**:
```cpp
VertexWriter vertices{ptr, size};
vertices << SkPoint{x, y} << color << texCoord;
```

#### 条件写入
```cpp
template <typename T>
static Conditional<T> If(bool condition, const T& value)
```
**功能**: 仅在条件为真时写入值。
**示例**:
```cpp
vertices << VertexWriter::If(hasColor, color);
```

#### 数组写入
```cpp
template <typename T>
static ArrayDesc<T> Array(const T* array, int count)
```
**功能**: 批量写入数组。
**示例**:
```cpp
vertices << VertexWriter::Array(positions, vertexCount);
```

#### 重复写入
```cpp
template <int kCount, typename T>
static RepeatDesc<kCount, T> Repeat(const T& val)
```
**功能**: 重复写入同一值。
**示例**:
```cpp
vertices << VertexWriter::Repeat<4>(color);  // 写入4次
```

#### 四边形写入
```cpp
template <typename... Args>
void writeQuad(const Args&... remainder)
```
**功能**: 写入四边形的四个顶点,支持混合重复和变化的数据。
**用法**: 通过 `is_quad<T>` 特化标记哪些类型在四个顶点间变化。

#### TriStrip / TriFan 辅助
```cpp
static TriStrip<float> TriStripFromRect(const SkRect& r)
static TriFan<float> TriFanFromRect(const SkRect& r)
```
**功能**: 从矩形生成三角形带/扇的顶点位置。

### IndexWriter 函数

#### writeArray
```cpp
void writeArray(SkSpan<const uint16_t> indices)
```
**功能**: 批量写入索引数组。

#### 流式写入
```cpp
IndexWriter& operator<<(IndexWriter& w, uint16_t val)
IndexWriter& operator<<(IndexWriter& w, int val)
```
**功能**: 流式写入索引。

### TextureUploadWriter 函数

#### write (矩形区域)
```cpp
void write(size_t offset, const void* src, size_t srcRowBytes,
           size_t dstRowBytes, size_t trimRowBytes, int rowCount)
```
**功能**: 写入矩形图像块,支持行字节数不同的情况。

#### convertAndWrite
```cpp
void convertAndWrite(size_t offset,
                     const SkImageInfo& srcInfo, const void* src, size_t srcRowBytes,
                     const SkImageInfo& dstInfo, size_t dstRowBytes)
```
**功能**: 转换像素格式并写入。

#### writeRGBFromRGBx
```cpp
void writeRGBFromRGBx(size_t offset, const void* src, size_t srcRowBytes,
                      size_t dstRowBytes, int rowPixels, int rowCount)
```
**功能**: 将 RGB888x 转换为紧凑的 RGB888 格式。

## 内部实现细节

### 零拷贝设计
所有写入操作直接写入预分配的缓冲区,避免中间缓冲:
```cpp
SkSpan<uint8_t> slice(size_t bytes) {
    void* ptr = fPtr;
    fPtr = SkTAddOffset<void>(fPtr, bytes);
    return SkSpan<uint8_t>{static_cast<uint8_t*>(ptr), bytes};
}
```

### 边界验证
在调试模式下,所有写入操作验证不超过 `fEnd`:
```cpp
void validate(size_t bytesToWrite) const {
    SkASSERT(fPtr || bytesToWrite == 0);
    SkASSERT(!fEnd || Mark(fPtr, bytesToWrite) <= fEnd);
}
```

### makeOffset 分割机制
`makeOffset` 将当前写入器分割为两部分:
```cpp
template<typename W>
W makeOffset(size_t offsetInBytes) const {
    validate(offsetInBytes);
    void* p = SkTAddOffset<void>(fPtr, offsetInBytes);
    Mark end = fEnd;
    fEnd = Mark(p);  // 限制当前写入器的结束位置
    return W{p, end};  // 新写入器从 p 开始
}
```
**用途**: 安全地将缓冲区区域分配给子任务。

### is_quad 特化机制
通过模板特化标记哪些类型在四边形顶点间变化:
```cpp
template <> struct VertexWriter::is_quad<TriStrip<float>> : std::true_type {};
```
编译时分发到不同的 `writeQuadVertex` 实现。

### VertexColor 格式适配
自动适配字节和浮点颜色:
```cpp
VertexWriter& operator<<(VertexWriter& w, const VertexColor& color) {
    w << color.fColor[0];
    if (color.fWideColor) {
        w << color.fColor[1] << color.fColor[2] << color.fColor[3];
    }
    return w;
}
```

### 宏辅助的代码生成
`BUFFER_WRITER_OVERLOADS` 宏生成重复的构造和赋值操作符,减少代码重复。

## 依赖关系

### 依赖的模块

| 模块 | 依赖内容 | 用途 |
|------|----------|------|
| `include/core/SkRect.h` | `SkRect` | 矩形定义 |
| `include/core/SkImageInfo.h` | `SkImageInfo` | 图像信息 |
| `src/base/SkRectMemcpy.h` | `SkRectMemcpy` | 矩形区域拷贝 |
| `src/core/SkConvertPixels.h` | `SkConvertPixels` | 像素格式转换 |
| `src/core/SkColorData.h` | `SkPMColor4f` | 预乘颜色 |

### 被依赖的模块

| 模块 | 使用内容 | 用途 |
|------|----------|------|
| Ganesh 几何生成 | `VertexWriter` | 顶点数据写入 |
| Graphite 绘制器 | `VertexWriter`, `IndexWriter` | 网格构建 |
| 纹理上传路径 | `TextureUploadWriter` | 纹理数据传输 |
| 路径渲染器 | `writeQuad` | 四边形批处理 |
| 文本渲染 | `VertexColor` | 字形颜色 |

## 设计模式与设计决策

### 1. CRTP (Curiously Recurring Template Pattern)
虽然未显式使用 CRTP,但通过继承和宏实现了类似的效果,避免虚函数开销。

### 2. 流式接口 (Fluent Interface)
`operator<<` 返回引用,支持链式调用:
```cpp
vertices << pos << color << uv;
```

### 3. 类型安全的变长参数
`writeQuad` 使用变长模板参数,编译时展开,无运行时开销:
```cpp
template <typename... Args>
void writeQuad(const Args&... remainder);
```

### 4. 零成本抽象
所有函数都是内联的,编译后与手写的指针操作无异,但提供更好的类型安全。

### 5. RAII 资源分割
`makeOffset` 实现了类似 RAII 的资源管理,确保缓冲区区域不会重复写入。

### 6. 编译时分发
`is_quad` 特化利用 SFINAE 在编译时选择正确的函数,无运行时分支。

## 性能考量

### 1. 零抽象开销
- 所有函数内联,编译后无函数调用
- 无虚函数表查找
- 无异常处理开销

### 2. 缓存友好
- 顺序写入,优秀的空间局部性
- 预分配的缓冲区,无碎片
- 直接写入最终位置,无中间拷贝

### 3. 编译时优化
- 模板实例化在编译时完成
- `constexpr` 常量直接嵌入代码
- 编译器可进行跨函数优化

### 4. 类型安全无开销
POD 类型约束(`std::is_trivially_copyable`)确保:
- 无隐藏的构造函数调用
- `memcpy` 可用(编译器优化为寄存器操作)
- 无对齐问题

### 5. 批量操作优化
`writeArray` 和 `Repeat` 利用循环展开和向量化优化。

### 6. 调试开销
边界检查仅在 `SK_DEBUG` 下启用,发布版本零开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/BufferWriter.h` | 定义 | 缓冲区写入器 |
| `src/gpu/ganesh/GrVertexWriter.h` | 使用者 | Ganesh 顶点写入 |
| `src/gpu/graphite/DrawWriter.h` | 使用者 | Graphite 绘制写入器 |
| `src/gpu/ganesh/geometry/GrQuad.cpp` | 使用者 | 四边形几何 |
| `src/gpu/graphite/PathAtlas.cpp` | 使用者 | 路径图集构建 |
| `src/gpu/ganesh/GrResourceProvider.cpp` | 提供者 | 缓冲区分配 |
| `src/base/SkRectMemcpy.h` | 依赖 | 矩形拷贝 |

**备注**: 该模块是 Skia GPU 性能关键路径的核心工具,通过零拷贝、内联和类型安全设计,在保证性能的同时提供了优雅的 C++ API。设计充分利用了现代 C++ 特性(模板、SFINAE、变长参数等),是高性能系统编程的优秀范例。
