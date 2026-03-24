# SkReadBuffer

> 源文件: src/core/SkReadBuffer.h, src/core/SkReadBuffer.cpp

## 概述

`SkReadBuffer` 是 Skia 图形库中用于反序列化（解扁平化）数据的核心工具类。它提供了一套完整的接口来从二进制缓冲区中读取各种类型的数据，包括基本类型、几何对象、图像、字体以及可扁平化对象（`SkFlattenable`）。该类是 Skia 序列化框架的关键组成部分，主要用于 `SkPicture` 的反序列化、Paint 对象的重建以及跨平台数据交换。

## 架构位置

`SkReadBuffer` 位于 Skia 核心层（`src/core`），与 `SkWriteBuffer` 配对使用，共同构成 Skia 的序列化/反序列化基础设施。它在架构中的位置：

- **上层依赖**: 被 `SkPicturePriv`、`SkFlattenable`、`SkPaint`、`SkShader`、`SkColorFilter` 等高级对象使用
- **同层协作**: 与 `SkWriteBuffer` 配对，依赖 `SkSamplingPriv`、`SkPaintPriv` 等私有接口
- **下层支持**: 使用 `SkAlign`、`SkSafeMath`、`SkMatrixPriv` 等底层工具

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 用途 |
|------|---------|------|
| `SkReadBuffer` | 无继承 | 主要的反序列化读取器类 |
| `EmptyImageGenerator` | 继承自 `SkImageGenerator` | 用于处理损坏/空图像流的占位符生成器 |

### SkReadBuffer 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCurr` | `const char*` | 当前读取位置指针 |
| `fStop` | `const char*` | 缓冲区结束位置 |
| `fBase` | `const char*` | 缓冲区起始位置 |
| `fVersion` | `int` | 数据版本号（用于版本兼容） |
| `fTFArray` | `sk_sp<SkTypeface>*` | 字体数组指针 |
| `fTFCount` | `int` | 字体数组大小 |
| `fFactoryArray` | `SkFlattenable::Factory*` | 工厂函数数组 |
| `fFactoryCount` | `int` | 工厂函数数量 |
| `fFlattenableDict` | `THashMap<uint32_t, Factory>` | 可扁平化对象工厂字典 |
| `fProcs` | `SkDeserialProcs` | 自定义反序列化回调 |
| `fAllowSkSL` | `bool` | 是否允许 SkSL 着色器 |
| `fError` | `bool` | 错误状态标志 |

## 公共 API 函数

### 初始化与配置

```cpp
// 构造与内存设置
SkReadBuffer(const void* data, size_t size);
void setMemory(const void* data, size_t size);

// 版本管理
void setVersion(int version);
uint32_t getVersion() const;
bool isVersionLT(SkPicturePriv::Version targetVersion) const;

// 配置回调
void setTypefaceArray(sk_sp<SkTypeface> array[], int count);
void setFactoryPlayback(SkFlattenable::Factory array[], int count);
void setDeserialProcs(const SkDeserialProcs& procs);
void setAllowSkSL(bool allow);
```

### 基本类型读取

```cpp
bool readBool();                     // 读取布尔值
int32_t readInt();                   // 读取 32 位整数
uint32_t readUInt();                 // 读取无符号 32 位整数
SkScalar readScalar();               // 读取标量（float）
SkColor readColor();                 // 读取颜色值
uint8_t peekByte();                  // 窥视下一个字节（不移动指针）
void readString(SkString* string);   // 读取字符串
```

### 几何对象读取

```cpp
void readPoint(SkPoint* point);              // 读取 2D 点
void readPoint3(SkPoint3* point);            // 读取 3D 点
void read(SkM44* matrix);                    // 读取 4x4 矩阵
void readMatrix(SkMatrix* matrix);           // 读取 3x3 变换矩阵
void readIRect(SkIRect* rect);               // 读取整数矩形
void readRect(SkRect* rect);                 // 读取浮点矩形
void readRRect(SkRRect* rrect);              // 读取圆角矩形
void readRegion(SkRegion* region);           // 读取区域
std::optional<SkPath> readPath();            // 读取路径
void readColor4f(SkColor4f* color);          // 读取浮点颜色
SkSamplingOptions readSampling();            // 读取采样选项
```

### 高级对象读取

```cpp
// 读取可扁平化对象
SkFlattenable* readRawFlattenable();
SkFlattenable* readFlattenable(SkFlattenable::Type);
template <typename T> sk_sp<T> readFlattenable();

// 特定类型的快捷方法
sk_sp<SkColorFilter> readColorFilter();
sk_sp<SkImageFilter> readImageFilter();
sk_sp<SkBlender> readBlender();
sk_sp<SkMaskFilter> readMaskFilter();
sk_sp<SkPathEffect> readPathEffect();
sk_sp<SkShader> readShader();
SkPaint readPaint();

// 图像与字体
sk_sp<SkImage> readImage();
sk_sp<SkTypeface> readTypeface();
```

### 数组读取

```cpp
bool readByteArray(void* value, size_t size);
bool readColorArray(SkSpan<SkColor>);
bool readColor4fArray(SkSpan<SkColor4f>);
bool readIntArray(SkSpan<int32_t>);
bool readPointArray(SkSpan<SkPoint>);
bool readScalarArray(SkSpan<SkScalar>);
const void* skipByteArray(size_t* size);
sk_sp<SkData> readByteArrayAsData();
uint32_t getArrayCount();  // 获取即将读取的数组元素数量
```

### 缓冲区管理与验证

```cpp
size_t size() const;                 // 缓冲区总大小
size_t offset() const;               // 当前偏移量
size_t available() const;            // 剩余可读字节数
bool eof();                          // 是否到达末尾
const void* skip(size_t size);       // 跳过指定字节数
bool isValid() const;                // 是否处于有效状态
bool validate(bool isValid);         // 验证条件，失败则标记错误
int32_t checkInt(int min, int max);  // 读取并范围检查整数
```

## 内部实现细节

### 内存对齐机制

所有数据都以 4 字节对齐方式存储和读取：

```cpp
// 跳过操作自动进行 4 字节对齐
const void* SkReadBuffer::skip(size_t size) {
    size_t inc = SkAlign4(size);  // 向上对齐到 4 字节边界
    this->validate(inc >= size);
    // ... 读取逻辑
}
```

### 错误处理策略

采用"标记失败并停止读取"模式：

```cpp
void SkReadBuffer::setInvalid() {
    if (!fError) {
        fCurr = fStop;  // 将读取指针移到末尾，停止所有后续读取
        fError = true;
    }
}
```

一旦发生错误，后续所有读取操作都会立即返回默认值，避免传播损坏数据。

### 可扁平化对象的反序列化

支持两种工厂查找模式：

1. **预加载工厂数组**（用于 `SkPicture`）：
```cpp
// 使用索引直接查找
int32_t index = this->read32();
factory = fFactoryArray[index - 1];
```

2. **字典模式**：
```cpp
// 首次读取工厂名称并缓存
const char* name = this->readString(&ignored_length);
factory = SkFlattenable::NameToFactory(name);
fFlattenableDict.set(count + 1, factory);

// 后续使用索引查找
uint32_t index = this->readUInt() >> 8;
factory = *fFlattenableDict.find(index);
```

### 图像反序列化特殊处理

图像反序列化包含多层容错逻辑：

1. **损坏数据处理**：返回 `nullptr` 表示数据损坏
2. **解码失败处理**：返回 1x1 空图像（`EmptyImageGenerator`）
3. **Mipmap 支持**：可选的多级渐远纹理数据
4. **子集矩形**（旧版兼容）：支持读取图像子集

```cpp
sk_sp<SkImage> SkReadBuffer::readImage() {
    // 读取标志位和数据
    uint32_t flags = this->read32();
    sk_sp<SkData> data = this->readByteArrayAsData();

    // 使用自定义回调或默认解码
    image = deserialize_image(data, fProcs, alphaType);

    // 失败则返回占位图像，而非 null
    return image ? image : MakeEmptyImage(1, 1);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkAlign` | 4 字节对齐计算 |
| `SkSafeMath` | 安全的乘法运算（防溢出） |
| `SkMatrixPriv` | 矩阵的内存读取 |
| `SkPaintPriv` | Paint 对象的反扁平化 |
| `SkSamplingPriv` | 采样选项的序列化支持 |
| `SkWriteBuffer` | 图像 Mipmap 反序列化时使用 |
| `SkDeserialProcs` | 自定义反序列化回调 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkPicture` | 读取录制的绘图命令 |
| `SkFlattenable` 子类 | 所有 `Shader`、`ColorFilter`、`ImageFilter` 等的反序列化 |
| `SkPaint` | 从缓冲区重建 Paint 对象 |
| `SkPath` | 读取路径数据 |
| 各种 Effect 类 | `Blender`、`MaskFilter`、`PathEffect` 等 |

## 设计模式与设计决策

### 1. 流式读取模式

使用三指针（`fBase`、`fCurr`、`fStop`）管理读取状态，支持顺序读取和跳过操作。

### 2. 工厂模式

使用 `SkFlattenable::Factory` 函数指针实现多态对象的反序列化：
- 支持预加载工厂数组（高性能场景）
- 支持动态工厂字典（灵活性场景）

### 3. 版本兼容策略

通过 `fVersion` 字段支持向后兼容：

```cpp
bool isVersionLT(SkPicturePriv::Version targetVersion) const {
    return fVersion > 0 && fVersion < targetVersion;
}

// 使用示例
if (!this->isVersionLT(SkPicturePriv::kAnisotropicFilter)) {
    // 新版本逻辑
} else {
    // 旧版本兼容逻辑
}
```

### 4. 错误传播机制

采用"粘性错误"模式：一旦标记错误，所有后续操作都自动失败并返回安全的默认值。

### 5. 内存安全设计

- 所有读取前都检查 `available()` 是否足够
- 使用 `SkSafeMath` 防止整数溢出
- 指针对齐检查防止未对齐访问

## 性能考量

### 1. 零拷贝优化

`skip()` 系列方法直接返回缓冲区内部指针，避免不必要的内存拷贝：

```cpp
const void* ptr = buffer.skip(dataSize);
// 直接使用 ptr 指向的原始缓冲区数据
```

### 2. 内联模板方法

高频调用的类型化跳过方法使用内联模板：

```cpp
template <typename T> const T* skipT() {
    return static_cast<const T*>(this->skip(sizeof(T)));
}
```

### 3. 工厂字典缓存

动态模式下，工厂函数按索引缓存，避免重复的字符串查找。

### 4. 内存对齐

4 字节对齐确保在所有平台上的快速内存访问。

### 5. 分支预测友好

常见路径（有效数据）放在 `if` 的主分支，错误路径放在 `else` 中。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkWriteBuffer.h/cpp` | 配对类 | 序列化写入器 |
| `include/core/SkFlattenable.h` | 核心接口 | 可扁平化对象基类 |
| `src/core/SkPaintPriv.h` | 使用者 | Paint 反扁平化实现 |
| `src/core/SkPicturePriv.h` | 使用者 | Picture 版本管理 |
| `include/core/SkSerialProcs.h` | 配置接口 | 自定义反序列化回调 |
| `src/core/SkMatrixPriv.h` | 依赖 | 矩阵内存操作 |
| `src/core/SkSamplingPriv.h` | 依赖 | 采样选项序列化 |
| `include/core/SkImage.h` | 使用者 | 图像反序列化 |
| `include/core/SkTypeface.h` | 使用者 | 字体反序列化 |
| `src/base/SkSafeMath.h` | 依赖 | 安全数学运算 |

## 典型使用场景

### 场景 1: 反序列化 SkPicture

```cpp
SkReadBuffer buffer(pictureData, dataSize);
buffer.setVersion(pictureVersion);
buffer.setFactoryPlayback(factories, factoryCount);
buffer.setTypefaceArray(typefaces, typefaceCount);

// 读取绘图命令
while (!buffer.eof()) {
    auto flattenable = buffer.readFlattenable<SkDrawCommand>();
    // 处理命令...
}
```

### 场景 2: 反序列化 Paint 对象

```cpp
SkReadBuffer buffer(paintData, dataSize);
SkPaint paint = buffer.readPaint();  // 内部调用 SkPaintPriv::Unflatten
```

### 场景 3: 自定义对象反序列化

```cpp
class MyEffect : public SkFlattenable {
    sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer) {
        float value = buffer.readScalar();
        auto shader = buffer.readShader();
        if (!buffer.isValid()) return nullptr;
        return sk_make_sp<MyEffect>(value, shader);
    }
};
```
