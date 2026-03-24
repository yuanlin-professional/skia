# SkMaskFilter

> 源文件: include/core/SkMaskFilter.h, src/core/SkMaskFilter.cpp

## 概述

`SkMaskFilter` 是 Skia 中用于对遮罩进行变换处理的公共基类。它在绘制之前对图形的遮罩应用各种效果,如模糊 (blur)、浮雕 (emboss) 等。该类是 `SkFlattenable` 的子类,支持序列化。最常用的子类是 blur mask filter,用于实现阴影和发光效果。

## 架构位置

`SkMaskFilter` 位于 Skia 绘制管线的效果层:
- 作为公共 API 暴露给用户
- 内部实现由 `SkMaskFilterBase` 提供
- 在光栅化和像素混合之前应用效果
- 支持序列化到 `SkPicture` 等格式

## 主要类与结构体

### 类层次结构

| 类名 | 父类 | 说明 |
|------|------|------|
| SkMaskFilter | SkFlattenable | 公共接口基类 |

### 关键枚举

**SkBlurStyle** (定义在其他头文件):
```cpp
enum SkBlurStyle {
    kNormal_SkBlurStyle,  // 内外都模糊
    kSolid_SkBlurStyle,   // 内部实心,外部模糊
    kOuter_SkBlurStyle,   // 仅外部模糊
    kInner_SkBlurStyle,   // 仅内部模糊
};
```

## 公共 API 函数

### 工厂方法

```cpp
// 创建模糊遮罩滤镜
static sk_sp<SkMaskFilter> MakeBlur(SkBlurStyle style,
                                    SkScalar sigma,
                                    bool respectCTM = true);
```

**参数**:
- `style`: 模糊样式 (normal/solid/outer/inner)
- `sigma`: 高斯模糊的标准差,必须 > 0
- `respectCTM`: 若为 true,模糊 sigma 受当前变换矩阵 (CTM) 影响

**返回值**:
- 成功: `sk_sp<SkMaskFilter>` 指向新的模糊滤镜
- 失败: `nullptr` (通常因 sigma <= 0)

### 序列化

```cpp
// 反序列化遮罩滤镜
static sk_sp<SkMaskFilter> Deserialize(const void* data,
                                       size_t size,
                                       const SkDeserialProcs* procs = nullptr);
```

**参数**:
- `data`: 序列化数据指针
- `size`: 数据大小
- `procs`: 可选的反序列化回调

**返回值**:
- 成功: 重建的 `SkMaskFilter` 对象
- 失败: `nullptr`

### 内部管理

```cpp
// 注册所有内置 flattenable (内部调用)
static void RegisterFlattenables();
```

由 Skia 初始化时自动调用,注册 blur 等滤镜的创建函数。

## 内部实现细节

### 注册机制

```cpp
void SkMaskFilter::RegisterFlattenables() {
    sk_register_blur_maskfilter_createproc();
}
```

调用外部定义的注册函数,将具体滤镜类型注册到 flattenable 工厂。

### 反序列化实现

```cpp
sk_sp<SkMaskFilter> SkMaskFilter::Deserialize(const void* data, size_t size,
                                              const SkDeserialProcs* procs) {
    return sk_sp<SkMaskFilter>(static_cast<SkMaskFilter*>(
               SkFlattenable::Deserialize(
                   kSkMaskFilter_Type, data, size, procs).release()));
}
```

利用 `SkFlattenable::Deserialize()` 通用反序列化机制,然后转换为 `SkMaskFilter` 类型。

### 内部基类关系

公共 API 通过 `SkMaskFilterBase` 访问内部实现:
```cpp
// 定义在 SkMaskFilterBase.h
inline SkMaskFilterBase* as_MFB(SkMaskFilter* mf) {
    return static_cast<SkMaskFilterBase*>(mf);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkFlattenable | 序列化基类 |
| SkRefCnt | 引用计数管理 |
| SkScalar | 浮点数类型 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkPaint | 包含 SkMaskFilter 作为绘制属性 |
| SkMaskFilterBase | 内部实现基类 |
| SkBlurMaskFilter | 具体的模糊滤镜实现 |
| SkCanvas | 应用滤镜效果 |

## 设计模式与设计决策

### 1. 抽象工厂模式
```cpp
static sk_sp<SkMaskFilter> MakeBlur(...);
```
通过静态工厂方法创建具体子类,隐藏实现细节。

### 2. Pimpl (编译防火墙)
公共 API (`SkMaskFilter`) 和内部实现 (`SkMaskFilterBase`) 分离:
- 头文件依赖减少
- 二进制兼容性更好
- 内部实现可自由修改

### 3. Flattenable 序列化
继承 `SkFlattenable` 支持:
- 序列化到 `SkPicture`
- 跨进程传输
- 持久化存储

### 4. 类型安全转换
```cpp
static SkFlattenable::Type GetFlattenableType() {
    return kSkMaskFilter_Type;
}
```
确保反序列化类型正确。

### 5. 智能指针管理
所有 API 使用 `sk_sp<SkMaskFilter>`:
```cpp
sk_sp<SkMaskFilter> filter = SkMaskFilter::MakeBlur(...);
paint.setMaskFilter(filter);  // 自动引用计数
```

## 性能考量

### 1. respectCTM 优化
```cpp
MakeBlur(style, sigma, respectCTM = true)
```
- `respectCTM = true`: 模糊随缩放变化 (质量优先)
- `respectCTM = false`: 模糊固定 (性能优先,可缓存)

### 2. 延迟计算
滤镜效果在实际绘制时才应用,不在创建时计算:
```cpp
auto filter = SkMaskFilter::MakeBlur(...);  // 轻量级
// ... 绘制时才执行模糊
```

### 3. 缓存机制
内部实现 (`SkMaskFilterBase`) 支持 nine-patch 缓存:
```cpp
// 大面积阴影可复用小块模糊结果
```

### 4. 序列化开销
反序列化需要:
- 类型查找
- 内存分配
- 参数重建

适合预处理,不适合热路径。

### 5. 虚函数调用
`SkMaskFilter` 是抽象类,方法调用涉及虚函数开销:
```cpp
virtual bool filterMask(...) const = 0;  // 动态分发
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkMaskFilterBase.h | 内部实现 | 实际功能基类 |
| include/effects/SkBlurMaskFilter.h | 已废弃 | 旧版公共接口 |
| include/core/SkPaint.h | 使用者 | 绘制属性 |
| include/core/SkFlattenable.h | 基类 | 序列化支持 |
| src/core/SkBlurMaskFilterImpl.h | 具体实现 | 模糊算法 |
| include/core/SkCanvas.h | 使用者 | 绘制接口 |

## 使用示例

### 创建模糊效果

```cpp
#include "include/core/SkMaskFilter.h"
#include "include/core/SkPaint.h"
#include "include/core/SkCanvas.h"

void drawBlurredRect(SkCanvas* canvas) {
    SkPaint paint;
    paint.setAntiAlias(true);
    paint.setColor(SK_ColorBLUE);

    // 创建模糊滤镜: sigma=10, 正常模糊样式
    auto blur = SkMaskFilter::MakeBlur(kNormal_SkBlurStyle, 10.0f);
    paint.setMaskFilter(blur);

    canvas->drawRect(SkRect::MakeWH(100, 100), paint);
}
```

### 固定大小模糊 (不受变换影响)

```cpp
auto blur = SkMaskFilter::MakeBlur(kNormal_SkBlurStyle,
                                   5.0f,
                                   false);  // respectCTM = false
paint.setMaskFilter(blur);

canvas->scale(2.0f, 2.0f);
canvas->drawCircle(50, 50, 30, paint);  // 模糊大小不变
```

### 序列化与反序列化

```cpp
// 序列化
sk_sp<SkMaskFilter> original = SkMaskFilter::MakeBlur(...);
sk_sp<SkData> data = original->serialize();

// 反序列化
sk_sp<SkMaskFilter> restored =
    SkMaskFilter::Deserialize(data->data(), data->size());
```
