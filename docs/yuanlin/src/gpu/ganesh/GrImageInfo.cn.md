# GrImageInfo

> 源文件: src/gpu/ganesh/GrImageInfo.h, src/gpu/ganesh/GrImageInfo.cpp

## 概述

`GrImageInfo` 是 Skia Ganesh GPU 后端中用于描述图像元数据的轻量级值类型。它封装了颜色类型 (color type)、透明度类型 (alpha type)、色彩空间 (color space) 以及图像尺寸 (dimensions) 等信息,为 GPU 图像处理提供统一的描述接口。

该类是 `SkImageInfo` 在 GPU 后端的对应物,使用 `GrColorType` 替代 `SkColorType`,并集成了 `GrColorInfo` 用于颜色相关信息的管理。它支持值语义,可以高效地拷贝和传递。

主要用途:
- 描述纹理和渲染目标的格式信息
- 作为图像读写操作的参数
- 在 CPU 和 GPU 之间传递图像元数据
- 创建派生的图像信息(修改颜色类型、尺寸等)

## 架构位置

`GrImageInfo` 位于 Ganesh 的类型系统层,作为图像元数据的容器:

1. **在图像处理流程中的位置**
   ```
   SkImageInfo (Skia 核心)
       └── 转换 ───> GrImageInfo (Ganesh GPU)
                           └── 包含 GrColorInfo
   ```

2. **与其他模块的关系**
   - `GrSurfaceProxy` 使用 `GrImageInfo` 描述 Surface 属性
   - `GrSurfaceContext` 在读写操作中使用 `GrImageInfo`
   - `GrPixmap` 结合 `GrImageInfo` 和数据指针表示像素数据
   - `GrDirectContext` 的纹理创建接口接受 `GrImageInfo`

3. **组成部分**
   - `GrColorInfo`: 颜色类型、透明度类型、色彩空间
   - `SkISize`: 图像宽度和高度

## 主要类与结构体

### 继承关系

```
GrImageInfo (无继承,值类型)
    └── 包含 GrColorInfo
    └── 包含 SkISize
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorInfo` | `GrColorInfo` | 颜色信息(类型、透明度、色彩空间) |
| `fDimensions` | `SkISize` | 图像尺寸(宽度和高度) |

### GrColorInfo 组成

`GrColorInfo` 包含:
- `GrColorType`: Ganesh GPU 颜色类型
- `SkAlphaType`: 透明度类型
- `sk_sp<SkColorSpace>`: 色彩空间智能指针

## 公共 API 函数

### 构造函数

```cpp
// 默认构造函数(无效状态)
GrImageInfo();

// 从 SkImageInfo 构造
GrImageInfo(const SkImageInfo& info);

// 从独立参数构造
GrImageInfo(GrColorType ct, SkAlphaType at, sk_sp<SkColorSpace> cs,
            int w, int h);
GrImageInfo(GrColorType ct, SkAlphaType at, sk_sp<SkColorSpace> cs,
            const SkISize& dimensions);

// 从 GrColorInfo 和尺寸构造
GrImageInfo(const GrColorInfo& info, const SkISize& dimensions);
GrImageInfo(GrColorInfo&& info, const SkISize& dimensions);

// 拷贝和移动构造
GrImageInfo(const GrImageInfo&);
GrImageInfo(GrImageInfo&&);
```

### 赋值运算符

```cpp
GrImageInfo& operator=(const GrImageInfo&);
GrImageInfo& operator=(GrImageInfo&&);
```

### 派生创建方法

```cpp
// 创建修改颜色类型后的副本
GrImageInfo makeColorType(GrColorType ct) const;

// 创建修改透明度类型后的副本
GrImageInfo makeAlphaType(SkAlphaType at) const;

// 创建修改色彩空间后的副本
GrImageInfo makeColorSpace(sk_sp<SkColorSpace> cs) const;

// 创建修改尺寸后的副本
GrImageInfo makeDimensions(SkISize dimensions) const;
GrImageInfo makeWH(int width, int height) const;
```

### 属性访问

```cpp
// 获取颜色信息
const GrColorInfo& colorInfo() const;

// 获取颜色类型
GrColorType colorType() const;

// 获取透明度类型
SkAlphaType alphaType() const;

// 获取色彩空间指针
SkColorSpace* colorSpace() const;

// 获取色彩空间的智能指针
sk_sp<SkColorSpace> refColorSpace() const;

// 获取尺寸
SkISize dimensions() const;
int width() const;
int height() const;

// 获取每像素字节数
size_t bpp() const;

// 获取最小行字节数
size_t minRowBytes() const;

// 检查有效性
bool isValid() const;
```

## 内部实现细节

### 构造函数实现

```cpp
// 默认构造
GrImageInfo::GrImageInfo() = default;

// 从 SkImageInfo 构造
GrImageInfo::GrImageInfo(const SkImageInfo& info)
    : fColorInfo(info.colorInfo())  // 自动转换
    , fDimensions(info.dimensions()) {}

// 从独立参数构造
GrImageInfo::GrImageInfo(GrColorType ct, SkAlphaType at,
                         sk_sp<SkColorSpace> cs, int w, int h)
    : fColorInfo(ct, at, std::move(cs))
    , fDimensions{w, h} {}

// 从 GrColorInfo 构造
GrImageInfo::GrImageInfo(const GrColorInfo& info, const SkISize& dimensions)
    : fColorInfo(info)
    , fDimensions(dimensions) {}

// 移动构造
GrImageInfo::GrImageInfo(GrColorInfo&& info, const SkISize& dimensions)
    : fColorInfo(std::move(info))
    , fDimensions(dimensions) {}
```

### 派生创建实现

```cpp
GrImageInfo GrImageInfo::makeColorType(GrColorType ct) const {
    return {this->colorInfo().makeColorType(ct), this->dimensions()};
}

GrImageInfo GrImageInfo::makeAlphaType(SkAlphaType at) const {
    return {this->colorType(), at, this->refColorSpace(),
            this->width(), this->height()};
}

GrImageInfo GrImageInfo::makeColorSpace(sk_sp<SkColorSpace> cs) const {
    return {this->colorType(), this->alphaType(), std::move(cs),
            this->width(), this->height()};
}

GrImageInfo GrImageInfo::makeDimensions(SkISize dimensions) const {
    return {this->colorType(), this->alphaType(),
            this->refColorSpace(), dimensions};
}

GrImageInfo GrImageInfo::makeWH(int width, int height) const {
    return {this->colorType(), this->alphaType(),
            this->refColorSpace(), width, height};
}
```

### 计算属性实现

```cpp
// 每像素字节数
size_t bpp() const {
    return GrColorTypeBytesPerPixel(this->colorType());
}

// 最小行字节数
size_t minRowBytes() const {
    return this->bpp() * this->width();
}

// 有效性检查
bool isValid() const {
    return fColorInfo.isValid() &&
           this->width() > 0 &&
           this->height() > 0;
}
```

### 代理访问实现

```cpp
// 颜色信息访问
const GrColorInfo& colorInfo() const { return fColorInfo; }
GrColorType colorType() const { return fColorInfo.colorType(); }
SkAlphaType alphaType() const { return fColorInfo.alphaType(); }
SkColorSpace* colorSpace() const { return fColorInfo.colorSpace(); }

// 色彩空间引用计数
sk_sp<SkColorSpace> refColorSpace() const {
    return fColorInfo.refColorSpace();
}

// 尺寸访问
SkISize dimensions() const { return fDimensions; }
int width() const { return fDimensions.width(); }
int height() const { return fDimensions.height(); }
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrColorInfo` | 颜色元数据管理 |
| `SkImageInfo` | CPU 侧图像信息 |
| `SkColorSpace` | 色彩空间表示 |
| `SkISize` | 尺寸类型 |
| `GrTypesPriv.h` | `GrColorType` 定义 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `GrSurfaceProxy` | 使用 `GrImageInfo` 描述 surface |
| `GrSurfaceContext` | 读写操作接受 `GrImageInfo` |
| `GrPixmap` | 结合数据指针表示像素数据 |
| `GrDirectContext` | 纹理创建接口 |
| `GrContextPriv` | 内部图像操作 |
| `GrCopyBaseMipMapToView` | 图像复制操作 |

## 设计模式与设计决策

### 设计模式

1. **值对象模式 (Value Object)**
   - 不可变语义(通过 `make*()` 创建新对象)
   - 支持拷贝和移动
   - 轻量级,适合作为参数传递

2. **建造者模式变体 (Builder Variant)**
   - `make*()` 方法提供流式 API
   - 每次调用返回新的副本
   - 链式调用: `info.makeWH(100, 100).makeColorType(kRGBA)`

3. **组合模式 (Composition)**
   - 组合 `GrColorInfo` 和 `SkISize`
   - 代理访问内部成员
   - 保持接口简洁

4. **适配器模式 (Adapter)**
   - 从 `SkImageInfo` 转换到 GPU 表示
   - 桥接 CPU 和 GPU 的类型系统

### 关键设计决策

1. **为何不直接使用 SkImageInfo?**
   - `SkImageInfo` 使用 `SkColorType`,不完全匹配 GPU 格式
   - `GrColorType` 更精确地表示 GPU 纹理格式
   - 例如: GPU 支持 `kRG_88` 等 CPU 不常用的格式

2. **值语义的选择**
   - 元数据很小(~32 字节),拷贝开销低
   - 避免指针和生命周期管理
   - 不可变性简化并发使用

3. **make*() 而非 set*() 方法**
   - 强制不可变性
   - 避免意外修改共享对象
   - 函数式编程风格

4. **包含 GrColorInfo 而非继承**
   - 组合优于继承
   - `GrColorInfo` 可以独立使用
   - 减少继承层次的复杂性

5. **isValid() 的定义**
   - 颜色信息有效
   - 宽度和高度 > 0
   - 不检查尺寸是否合理(例如是否过大)

6. **bpp() 和 minRowBytes() 的便利性**
   - 常用计算封装为方法
   - 减少重复代码
   - 统一计算逻辑

## 性能考量

### 轻量级值类型

1. **内存占用**
   - `GrColorInfo`: ~16 字节
   - `SkISize`: 8 字节
   - 总计: ~24 字节(加上 padding)

2. **拷贝性能**
   - 色彩空间使用智能指针,引用计数开销低
   - 可以按值传递和返回
   - 编译器可能优化为寄存器传递

3. **缓存友好**
   - 紧凑布局减少缓存行占用
   - 常用字段集中访问

### 默认成员函数

```cpp
GrImageInfo(const GrImageInfo&) = default;
GrImageInfo(GrImageInfo&&) = default;
GrImageInfo& operator=(const GrImageInfo&) = default;
GrImageInfo& operator=(GrImageInfo&&) = default;
```

- 使用编译器生成的默认实现
- 优化为简单的内存拷贝(在可能的情况下)
- 移动语义避免不必要的引用计数操作

### make*() 方法的优化

- RVO (Return Value Optimization) 避免拷贝
- 移动语义减少引用计数操作
- 内联优化消除函数调用开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrColorInfo.h` | 组合 | 颜色元数据 |
| `include/core/SkImageInfo.h` | 转换 | CPU 侧图像信息 |
| `include/core/SkColorSpace.h` | 依赖 | 色彩空间定义 |
| `include/core/SkSize.h` | 依赖 | 尺寸类型 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | `GrColorType` 定义 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 使用 | Surface 代理 |
| `src/gpu/ganesh/GrSurfaceContext.h` | 使用 | Surface 上下文 |
| `src/gpu/ganesh/GrPixmap.h` | 配合 | 像素数据表示 |
| `src/gpu/ganesh/GrDirectContext.h` | 使用 | 上下文接口 |
