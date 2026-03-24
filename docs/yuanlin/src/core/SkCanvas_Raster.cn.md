# SkCanvas_Raster

> 源文件: src/core/SkCanvas_Raster.cpp

## 概述

`SkCanvas_Raster.cpp` 提供了基于光栅位图的 `SkCanvas` 构造函数实现。该文件专注于将 `SkCanvas` 与 `SkBitmap` 关联,创建用于 CPU 光栅化的画布实例。它是 Skia 光栅渲染路径的入口点,为不需要 GPU 加速的场景提供简单高效的软件渲染能力。

该模块通过创建 `SkBitmapDevice` 作为底层设备,将画布的绘制操作路由到 CPU 光栅化器。

## 架构位置

`SkCanvas_Raster.cpp` 在 Skia 架构中的位置:
- 作为 `SkCanvas` 的部分实现,位于 src/core 核心层
- 连接上层画布 API 与底层位图设备
- 为光栅渲染提供初始化路径
- 与 `SkBitmapDevice` 紧密集成
- 支持 Android 框架的特殊颜色行为
- 可选集成 `SkRasterHandleAllocator` 用于自定义内存管理

## 主要类与结构体

该文件不定义新类,仅提供 `SkCanvas` 的构造函数实现。

### SkCanvas 构造函数变体

文件实现了 4 个构造函数:

1. **基本位图构造函数**
```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap)
```

2. **带 Surface Props 的构造函数**
```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap, const SkSurfaceProps& props)
```

3. **自定义分配器构造函数**
```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap,
                   std::unique_ptr<SkRasterHandleAllocator> alloc,
                   SkRasterHandleAllocator::Handle hndl,
                   const SkSurfaceProps* props)
```

4. **Android 颜色行为构造函数**(仅 Android 框架构建)
```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap, ColorBehavior)
```

## 公共 API 函数

### 基础构造函数

```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap)
```

创建与位图关联的画布,使用默认表面属性。

**参数:**
- `bitmap`: 绘制目标位图

**内部实现:**
```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap)
    : SkCanvas(bitmap, nullptr, nullptr, nullptr) {}
```

委托给自定义分配器版本,传递空指针。

### 带表面属性的构造函数

```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap, const SkSurfaceProps& props)
```

创建画布并指定表面属性(像素几何、抗锯齿设置等)。

**参数:**
- `bitmap`: 绘制目标位图
- `props`: 表面属性配置

**内部实现:**
```cpp
: fMCStack(sizeof(MCRec), fMCRecStorage, sizeof(fMCRecStorage))
, fProps(props) {
    this->init(sk_make_sp<SkBitmapDevice>(bitmap, fProps));
}
```

初始化步骤:
1. 初始化矩阵/裁剪栈(`fMCStack`)使用内联存储
2. 保存表面属性(`fProps`)
3. 创建 `SkBitmapDevice` 并关联位图
4. 调用 `init` 完成画布初始化

### 自定义分配器构造函数

```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap,
                   std::unique_ptr<SkRasterHandleAllocator> alloc,
                   SkRasterHandleAllocator::Handle hndl,
                   const SkSurfaceProps* props)
```

创建画布并使用自定义光栅句柄分配器。

**参数:**
- `bitmap`: 绘制目标位图
- `alloc`: 自定义分配器(移动语义)
- `hndl`: 分配器句柄
- `props`: 可选的表面属性指针

**内部实现:**
```cpp
: fMCStack(sizeof(MCRec), fMCRecStorage, sizeof(fMCRecStorage))
, fProps(SkSurfacePropsCopyOrDefault(props))
, fAllocator(std::move(alloc)) {
    this->init(sk_make_sp<SkBitmapDevice>(bitmap, fProps, hndl));
}
```

特点:
- 使用 `SkSurfacePropsCopyOrDefault` 处理可选属性
- 保存分配器所有权(`fAllocator`)
- 将句柄传递给 `SkBitmapDevice`

### Android 特殊构造函数

```cpp
#if defined(SK_BUILD_FOR_ANDROID_FRAMEWORK)
SkCanvas::SkCanvas(const SkBitmap& bitmap, ColorBehavior)
```

创建忽略位图颜色空间的画布,用于 Android 框架兼容。

**内部实现:**
```cpp
: fMCStack(sizeof(MCRec), fMCRecStorage, sizeof(fMCRecStorage)) {
    SkBitmap tmp(bitmap);
    *const_cast<SkImageInfo*>(&tmp.info()) = tmp.info().makeColorSpace(nullptr);
    this->init(sk_make_sp<SkBitmapDevice>(tmp, fProps));
}
```

特殊处理:
1. 拷贝位图
2. 通过 `const_cast` 移除颜色空间信息
3. 使用修改后的位图创建设备

警告:使用 `const_cast` 修改 `SkImageInfo` 是不安全的,仅限 Android 框架内部使用。

## 内部实现细节

### 设备初始化流程

所有构造函数最终调用 `this->init(sk_make_sp<SkBitmapDevice>(...))`:

```cpp
this->init(sk_make_sp<SkBitmapDevice>(bitmap, fProps));
```

`init` 方法(定义在 SkCanvas.cpp 中):
1. 将设备设置为顶层设备
2. 初始化矩阵栈和裁剪栈
3. 设置默认的绘制状态
4. 关联设备与画布生命周期

### SkBitmapDevice 的作用

`SkBitmapDevice` 实现了 `SkDevice` 接口:
- 将绘制命令转换为像素操作
- 管理位图的像素缓冲区
- 处理光栅化、抗锯齿、混合
- 支持裁剪、变换、图层

### 内联存储优化

```cpp
fMCStack(sizeof(MCRec), fMCRecStorage, sizeof(fMCRecStorage))
```

`fMCRecStorage` 是 `SkCanvas` 的成员数组:
- 预分配栈帧存储,避免小深度场景的堆分配
- `MCRec` (Matrix-Clip Record) 是 save/restore 的栈帧
- 超出内联存储时自动切换到堆分配

### SkSurfaceProps 处理

```cpp
fProps(SkSurfacePropsCopyOrDefault(props))
```

`SkSurfacePropsCopyOrDefault` 行为:
- 如果 `props` 非空,拷贝其值
- 如果 `props` 为空,使用默认值
- 默认值通常是 `SkSurfaceProps()` 无参构造

### 自定义分配器集成

`SkRasterHandleAllocator` 用途:
- 允许外部控制光栅化缓冲区的分配
- 支持特殊内存区域(共享内存、GPU 映射内存)
- 用于高级集成场景(如 Chrome 的 Canvas2D)

`Handle` 参数:
- 传递给设备,标识特定的内存区域
- 由分配器管理和解释
- 设备通过句柄访问像素缓冲区

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkCanvas.h | 画布公共接口 |
| include/core/SkRasterHandleAllocator.h | 自定义分配器接口 |
| src/core/SkBitmapDevice.h | 位图设备实现 |
| src/core/SkDevice.h | 设备抽象基类 |
| src/core/SkSurfacePriv.h | Surface 私有工具 |
| src/text/GlyphRun.h | 文本渲染支持(间接) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| 客户端代码 | 创建光栅画布进行绘制 |
| SkSurface | 通过 `MakeRasterDirect` 等工厂方法间接使用 |
| 测试代码 | 测试光栅渲染功能 |
| Android 框架 | 特殊颜色行为支持 |

## 设计模式与设计决策

### 构造函数委托

```cpp
SkCanvas::SkCanvas(const SkBitmap& bitmap)
    : SkCanvas(bitmap, nullptr, nullptr, nullptr) {}
```

使用构造函数委托:
- 减少代码重复
- 统一初始化逻辑
- 简化维护

### 策略模式(设备抽象)

画布通过 `SkDevice` 接口与具体渲染后端解耦:
- `SkBitmapDevice`: 光栅渲染
- GPU 设备(其他文件): GPU 渲染
- 画布不关心具体实现细节

### 依赖注入

```cpp
std::unique_ptr<SkRasterHandleAllocator> alloc
```

通过构造函数注入分配器:
- 灵活性高,支持自定义分配策略
- 不破坏封装,画布不关心分配细节
- 可选依赖,默认情况不需要

### 适配器模式(Android)

```cpp
*const_cast<SkImageInfo*>(&tmp.info()) = tmp.info().makeColorSpace(nullptr);
```

通过修改位图信息适配 Android 的颜色行为:
- 允许渐进式迁移到颜色管理
- 向后兼容旧代码
- 隔离平台特定逻辑

## 性能考量

### 内联存储

```cpp
fMCStack(sizeof(MCRec), fMCRecStorage, sizeof(fMCRecStorage))
```

优势:
- 避免小深度绘制场景的堆分配
- 提高缓存局部性
- 减少内存碎片

### 智能指针开销

```cpp
sk_make_sp<SkBitmapDevice>(bitmap, fProps)
```

使用 `sk_sp`:
- 引用计数管理设备生命周期
- 原子操作开销很小
- 避免手动内存管理错误

### 位图拷贝(Android)

```cpp
SkBitmap tmp(bitmap);  // 浅拷贝
```

`SkBitmap` 的拷贝构造是浅拷贝:
- 只拷贝像素缓冲区指针,不拷贝像素数据
- 引用计数增加
- 开销极低

### SkSurfaceProps 拷贝

```cpp
fProps(SkSurfacePropsCopyOrDefault(props))
```

`SkSurfaceProps` 是小对象(~16 字节):
- 拷贝开销可忽略
- 值语义更安全
- 避免悬空指针

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkCanvas.h | 接口定义 | 画布公共 API |
| src/core/SkCanvas.cpp | 主要实现 | 画布核心逻辑 |
| src/core/SkBitmapDevice.h/cpp | 设备实现 | 位图光栅化 |
| src/core/SkDevice.h | 抽象基类 | 设备接口 |
| include/core/SkSurface.h | 工厂接口 | Surface 创建 |
| include/core/SkRasterHandleAllocator.h | 扩展接口 | 自定义分配器 |
| src/core/SkSurfacePriv.h | 内部工具 | Surface 私有函数 |
