# SkFontDescriptor

> 源文件：src/core/SkFontDescriptor.h, src/core/SkFontDescriptor.cpp

## 概述

SkFontDescriptor 是 Skia 字体系统中的核心序列化类,用于描述和传输字体的完整信息。它封装了字体的所有属性(名称、样式、变体坐标、调色板等)以及可选的字体数据流,支持跨进程、跨平台的字体传输和持久化存储。该类同时定义了 SkFontData 辅助类用于管理字体数据。

## 架构位置

```
Skia 字体系统
└── src/core
    ├── SkFontDescriptor (字体描述符)
    ├── SkFontData (字体数据容器)
    ├── SkTypeface (字体面)
    ├── SkFontMgr (字体管理器)
    └── 序列化框架
        ├── SkWriteBuffer
        └── SkReadBuffer
```

该类是字体序列化和字体匹配的桥梁,在字体创建流程中起关键作用。

## 主要类与结构体

### SkFontData

字体数据容器,管理字体流和相关参数。

**继承关系**
- 无继承,值类型

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fStream | std::unique_ptr<SkStreamAsset> | 字体数据流 |
| fIndex | int | TTC 集合索引 |
| fPaletteIndex | int | 调色板索引(彩色字体) |
| fAxisCount | int | 变体轴数量 |
| fPaletteOverrideCount | int | 调色板覆盖数量 |
| fAxis | AutoSTMalloc<4, SkFixed> | 变体轴坐标数组 |
| fPaletteOverrides | AutoSTMalloc<4, Palette::Override> | 调色板覆盖数组 |

### SkFontDescriptor

字体描述符,包含字体属性和可选数据流。

**继承关系**
- 继承自 SkNoncopyable (不可拷贝)

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fFamilyName | SkString | 字体族名 |
| fFullName | SkString | 完整名称 |
| fPostscriptName | SkString | PostScript 名称 |
| fStyle | SkFontStyle | 字体样式(weight/width/slant) |
| fStream | std::unique_ptr<SkStreamAsset> | 可选字体数据 |
| fCollectionIndex | int | TTC 索引,默认 0 |
| fPaletteIndex | int | 调色板索引,默认 0 |
| fCoordinateCount | int | 变体坐标数量 |
| fVariation | Coordinates | 变体坐标数组 |
| fPaletteEntryOverrideCount | int | 调色板条目覆盖数量 |
| fPaletteEntryOverrides | AutoTMalloc<Override> | 调色板覆盖 |
| fSyntheticBold | bool | 是否合成粗体 |
| fSyntheticOblique | bool | 是否合成斜体 |
| fFactoryId | SkTypeface::FactoryId | 工厂 ID |

## 公共 API 函数

### SkFontData 核心方法

#### 构造函数

```cpp
SkFontData(std::unique_ptr<SkStreamAsset> stream,
           int index, int paletteIndex,
           const SkFixed* axis, int axisCount,
           const Palette::Override* overrides, int overrideCount)
```

创建字体数据对象,拷贝轴和调色板覆盖数据。

#### 访问器方法

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| hasStream() | bool | 是否包含数据流 |
| detachStream() | unique_ptr | 转移流所有权 |
| getStream() | SkStreamAsset* | 获取流指针 |
| getIndex() | int | 获取 TTC 索引 |
| getAxisCount() | int | 获取轴数量 |
| getAxis() | const SkFixed* | 获取轴数据 |
| getPaletteIndex() | int | 获取调色板索引 |
| getPaletteOverrides() | const Override* | 获取覆盖数据 |

### SkFontDescriptor 核心方法

#### 序列化方法

```cpp
static bool Deserialize(SkStream* stream, SkFontDescriptor* result)
```

从流反序列化字体描述符。

**返回值**
- true: 成功
- false: 失败(数据损坏或格式错误)

**特性**
- 完整错误检查
- 向后兼容旧格式
- 自动处理版本差异

```cpp
bool serialize(SkWStream* stream) const
```

序列化到输出流。

**格式**
- 紧凑二进制格式
- 可选字段按需编码
- 包含版本信息

#### 属性访问器

```cpp
SkFontStyle getStyle() const
const char* getFamilyName() const
const char* getFullName() const
const char* getPostscriptName() const
```

获取字体基本属性。

#### 属性设置器

```cpp
void setStyle(SkFontStyle style)
void setFamilyName(const char* name)
void setFullName(const char* name)
void setPostscriptName(const char* name)
```

设置字体基本属性。

#### 高级属性

```cpp
int getCollectionIndex() const
int getPaletteIndex() const
int getVariationCoordinateCount() const
const VariationPosition::Coordinate* getVariation() const
bool getSyntheticBold() const
bool getSyntheticOblique() const
```

获取高级字体参数。

#### 数据流管理

```cpp
bool hasStream() const
std::unique_ptr<SkStreamAsset> dupStream() const
std::unique_ptr<SkStreamAsset> detachStream()
void setStream(std::unique_ptr<SkStreamAsset> stream)
```

管理嵌入的字体数据流。

#### 构建 FontArguments

```cpp
SkFontArguments getFontArguments() const
```

转换为 SkFontArguments 对象,用于字体创建。

#### 静态工具方法

```cpp
static SkFontStyle::Width SkFontStyleWidthForWidthAxisValue(SkScalar width)
static SkScalar SkFontWidthAxisValueForStyleWidth(int width)
```

在 CSS 宽度值和变体轴值之间转换。

## 内部实现细节

### 序列化格式

#### 字段标识符

```cpp
enum {
    kFontFamilyName = 0x01,
    kFullName = 0x04,
    kPostscriptName = 0x06,
    kWeight = 0x10,
    kWidth = 0x11,
    kSlant = 0x12,
    kItalic = 0x13,
    kSyntheticBold = 0xF6,
    kSyntheticOblique = 0xF7,
    kPaletteIndex = 0xF8,
    kPaletteEntryOverrides = 0xF9,
    kFontVariation = 0xFA,
    kFactoryId = 0xFC,
    kFontIndex = 0xFD,
    kSentinel = 0xFF
};
```

#### 编码结构

```
[styleBits:4字节] [字段序列] [kSentinel] [流长度] [流数据]

styleBits 格式:
  weight:16 | width:8 | slant:4 | 未使用:4
```

#### 可选字段编码

仅当值非默认时才写入:
```cpp
if (fCollectionIndex > 0) {
    write_uint(stream, fCollectionIndex, kFontIndex);
}
```

### 宽度映射

CSS 宽度值到轴值的映射表:

```cpp
static constexpr SkScalar width_for_usWidth[0x10] = {
    50,   // 0: 不使用
    50,   // 1: ultra-condensed
    62.5, // 2: extra-condensed
    75,   // 3: condensed
    87.5, // 4: semi-condensed
    100,  // 5: normal
    112.5,// 6: semi-expanded
    125,  // 7: expanded
    150,  // 8: extra-expanded
    200,  // 9: ultra-expanded
    200, 200, 200, 200, 200, 200  // 10-15: 保留
};
```

### 反序列化流程

```cpp
1. 读取 styleBits 解析基础样式
2. 循环读取字段直到 kSentinel
   - 根据 ID 分发到不同处理逻辑
   - 验证数据完整性
   - 动态分配数组(变体坐标/调色板覆盖)
3. 读取可选字体流
   - 读取长度
   - 读取数据到 SkData
   - 包装为 SkMemoryStream
```

### 错误处理

```cpp
// 所有读取都检查有效性
if (!stream->readPackedUInt(&length)) { return false; }

// 防止超长数据消耗内存
if (SkStreamPriv::RemainingLengthIsBelow(stream, length)) {
    return false;
}

// 类型安全转换
if (!SkTFitsIn<CoordinateCountType>(coordinateCount)) {
    return false;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkFontStyle | 字体样式定义 |
| SkFontArguments | 字体参数传递 |
| SkStream | 流接口 |
| SkData | 数据容器 |
| SkString | 字符串管理 |
| SkFixed | 定点数类型 |
| SkTFitsIn | 类型安全转换 |
| SkFloatUtils | 浮点工具 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkTypeface | 序列化字体面 |
| SkFontMgr | 字体匹配和创建 |
| SkRemoteTypeface | 远程字体传输 |
| Chromium IPC | 跨进程字体共享 |

## 设计模式与设计决策

### 设计模式

1. **值对象模式**: SkFontData 作为不可变数据容器
2. **建造者模式**: SkFontDescriptor 通过 setter 链式构建
3. **序列化模式**: 自定义二进制格式,紧凑高效

### 设计决策

1. **为何分离 SkFontData 和 SkFontDescriptor**
   - SkFontData: 纯数据,用于传递
   - SkFontDescriptor: 包含序列化逻辑,更重量级

2. **可选字段的编码策略**
   - 节省空间:仅编码非默认值
   - 版本兼容:新字段不影响旧版本
   - 扩展性:易于添加新属性

3. **嵌入流 vs 引用流**
   - 嵌入流:自包含,适合跨进程
   - 引用流:节省内存,适合本地使用
   - 设计支持两种模式

4. **宽度映射表的原因**
   - CSS 标准定义离散宽度值
   - OpenType 'wdth' 轴使用百分比
   - 映射表实现双向转换

5. **使用 AutoSTMalloc 的好处**
   - 小数组用栈(避免堆分配)
   - 大数组自动切换到堆
   - RAII 自动释放

## 性能考量

### 内存占用

```cpp
sizeof(SkFontDescriptor) ≈
    3 * sizeof(SkString)       // ~96 字节
    + sizeof(SkFontStyle)      // 12 字节
    + sizeof(unique_ptr)       // 8 字节
    + 4 * sizeof(int)          // 16 字节
    + Coordinates 开销         // ~32 字节(小数组)
    + AutoTMalloc 开销         // ~32 字节
    ≈ 196 字节 (无大数组时)
```

### 序列化大小

典型字体描述符:
```
基础: 20-50 字节 (样式 + 名称)
变体: +12 * 轴数量
调色板: +8 * 覆盖数量
字体流: +实际字体大小 (可选)
```

### 性能优化

1. **延迟流复制**
```cpp
std::unique_ptr<SkStreamAsset> dupStream() const {
    return fStream->duplicate();  // 仅在需要时复制
}
```

2. **智能内存分配**
```cpp
AutoSTMalloc<4, SkFixed> fAxis;  // 4 轴以内不分配堆
```

3. **紧凑编码**
```cpp
stream->writePackedUInt(value);  // 变长编码节省空间
```

### 性能特征

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 序列化 | O(n) | n = 字段数量 |
| 反序列化 | O(n) | 线性读取 |
| 拷贝构造 | O(n) | 复制数组 |
| 流复制 | O(m) | m = 字体数据大小 |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkFontStyle.h | 字体样式定义 |
| include/core/SkFontArguments.h | 字体参数 |
| include/core/SkTypeface.h | 字体面接口 |
| src/core/SkFontMgr.cpp | 字体管理器实现 |
| src/core/SkTypeface.cpp | 字体面序列化 |
| src/core/SkRemoteTypeface.cpp | 远程字体传输 |
| tests/FontDescriptorTest.cpp | 单元测试 |
