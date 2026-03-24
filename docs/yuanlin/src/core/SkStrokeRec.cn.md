# SkStrokeRec

> 源文件: include/core/SkStrokeRec.h, src/core/SkStrokeRec.cpp

## 概述

`SkStrokeRec` 是 Skia 图形库中用于记录和管理路径描边参数的核心类。它封装了描边的所有属性,包括描边宽度、端点帽样式、连接点样式、斜接限制以及描边样式(hairline、fill、stroke、stroke+fill)。该类不仅存储这些参数,还提供了将描边应用到路径的功能,以及计算描边对几何边界影响的方法。它在 Skia 的渲染管线中扮演着描边参数传递和转换的关键角色。

## 架构位置

`SkStrokeRec` 位于 Skia 核心 API 层,作为 `SkPaint` 描边属性和底层描边算法之间的桥梁。它将高层的绘制意图转换为具体的几何操作指令。

```
Skia 描边处理流程:
  SkPaint (用户设置的绘制属性)
    ↓ 提取描边参数
  SkStrokeRec (参数封装和传递)
    ↓ 应用到路径
  SkStroke (底层描边算法)
    ↓ 调用几何生成
  SkStrokerPriv (Cap/Join 实现)
    ↓ 输出
  SkPathBuilder (生成描边后的路径)
```

## 主要类与结构体

### SkStrokeRec

**继承关系:**
- 无继承关系(独立的数据类)
- 使用 `SK_BEGIN_REQUIRE_DENSE` 宏标记,要求紧凑内存布局

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fResScale` | `SkScalar` | 分辨率缩放因子,影响曲线细分精度 |
| `fWidth` | `SkScalar` | 描边宽度(负值表示 fill,0 表示 hairline) |
| `fMiterLimit` | `SkScalar` | 斜接限制,防止尖角过长 |
| `fCap` | `uint32_t : 16` | 端点帽样式 (SkPaint::Cap) |
| `fJoin` | `uint32_t : 15` | 连接点样式 (SkPaint::Join) |
| `fStrokeAndFill` | `uint32_t : 1` | 是否同时描边和填充 |

**注意**: 后三个成员被打包到同一个 32 位整数中,避免内存填充,确保二进制相等性用于哈希计算。

## 公共 API 函数

### 构造函数

| 函数签名 | 功能说明 |
|---------|---------|
| `SkStrokeRec(InitStyle style)` | 使用初始化样式构造(kHairline_InitStyle 或 kFill_InitStyle) |
| `SkStrokeRec(const SkPaint&, SkScalar resScale = 1)` | 从 SkPaint 提取描边参数 |
| `SkStrokeRec(const SkPaint&, SkPaint::Style, SkScalar resScale = 1)` | 从 SkPaint 提取,但覆盖样式 |

### 样式枚举

```cpp
enum Style {
    kHairline_Style,        // 1 像素宽度
    kFill_Style,            // 仅填充
    kStroke_Style,          // 仅描边
    kStrokeAndFill_Style    // 描边并填充
};
```

### 属性访问

| 函数签名 | 功能说明 |
|---------|---------|
| `Style getStyle() const` | 获取当前样式 |
| `SkScalar getWidth() const` | 获取描边宽度 |
| `SkScalar getMiter() const` | 获取斜接限制 |
| `SkPaint::Cap getCap() const` | 获取端点帽样式 |
| `SkPaint::Join getJoin() const` | 获取连接点样式 |
| `SkScalar getResScale() const` | 获取分辨率缩放因子 |
| `bool isHairlineStyle() const` | 是否为 hairline 样式 |
| `bool isFillStyle() const` | 是否为 fill 样式 |
| `bool needToApply() const` | 是否需要应用描边 |

### 属性修改

| 函数签名 | 功能说明 |
|---------|---------|
| `void setFillStyle()` | 设置为填充样式 |
| `void setHairlineStyle()` | 设置为 hairline 样式 |
| `void setStrokeStyle(SkScalar width, bool strokeAndFill = false)` | 设置描边样式和宽度 |
| `void setStrokeParams(SkPaint::Cap, SkPaint::Join, SkScalar miterLimit)` | 设置描边参数 |
| `void setResScale(SkScalar rs)` | 设置分辨率缩放因子 |

### 核心功能

| 函数签名 | 功能说明 |
|---------|---------|
| `bool applyToPath(SkPathBuilder* dst, const SkPath& src) const` | 将描边应用到路径,返回是否修改 |
| `void applyToPaint(SkPaint* paint) const` | 将描边参数应用到 SkPaint |
| `SkScalar getInflationRadius() const` | 获取描边对几何边界的扩展半径 |
| `bool hasEqualEffect(const SkStrokeRec& other) const` | 比较两个 SkStrokeRec 是否有相同效果 |

### 静态工具方法

| 函数签名 | 功能说明 |
|---------|---------|
| `static SkScalar GetInflationRadius(const SkPaint&, SkPaint::Style)` | 从 SkPaint 计算扩展半径 |
| `static SkScalar GetInflationRadius(SkPaint::Join, SkScalar miterLimit, SkPaint::Cap, SkScalar strokeWidth)` | 根据参数计算扩展半径 |

## 内部实现细节

### 样式编码机制

使用 `fWidth` 的特殊值编码样式:
```cpp
#define kStrokeRec_FillStyleWidth (-SK_Scalar1)  // -1.0 表示 fill

Style getStyle() const {
    if (fWidth < 0) return kFill_Style;
    if (fWidth == 0) return kHairline_Style;
    return fStrokeAndFill ? kStrokeAndFill_Style : kStroke_Style;
}
```

这种编码方式避免了额外的样式字段,节省内存。

### 初始化逻辑

从 `SkPaint` 初始化时的特殊处理:
```cpp
void init(const SkPaint& paint, SkPaint::Style style, SkScalar resScale) {
    switch (style) {
        case SkPaint::kStrokeAndFill_Style:
            if (0 == paint.getStrokeWidth()) {
                // hairline + fill == fill (特殊规则)
                fWidth = kStrokeRec_FillStyleWidth;
                fStrokeAndFill = false;
            } else {
                fWidth = paint.getStrokeWidth();
                fStrokeAndFill = true;
            }
            break;
        // ...
    }
}
```

关键设计:hairline 描边与填充的组合被简化为纯填充。

### 描边应用

```cpp
bool applyToPath(SkPathBuilder* dst, const SkPath& src) const {
    if (fWidth <= 0) return false;  // hairline 或 fill 不需要应用

    SkStroke stroker;
    stroker.setCap((SkPaint::Cap)fCap);
    stroker.setJoin((SkPaint::Join)fJoin);
    stroker.setMiterLimit(fMiterLimit);
    stroker.setWidth(fWidth);
    stroker.setDoFill(fStrokeAndFill);
    stroker.setResScale(fResScale);
    stroker.strokePath(src, dst);
    return true;
}
```

### 扩展半径计算

描边会扩展几何边界,计算公式:
```cpp
SkScalar GetInflationRadius(SkPaint::Join join, SkScalar miterLimit,
                           SkPaint::Cap cap, SkScalar strokeWidth) {
    if (strokeWidth < 0) return 0;  // fill
    if (strokeWidth == 0) return SK_Scalar1;  // hairline 特殊处理

    SkScalar multiplier = SK_Scalar1;
    if (join == SkPaint::kMiter_Join) {
        multiplier = max(multiplier, miterLimit);
    }
    if (cap == SkPaint::kSquare_Cap) {
        multiplier = max(multiplier, SK_ScalarSqrt2);
    }
    return strokeWidth / 2 * multiplier;
}
```

关键点:
- **斜接连接**: 最坏情况由斜接限制决定
- **方形帽**: 对角线长度为 `√2` 倍半径
- **Hairline**: 特殊返回 1.0(实际在设备空间确定)

### 位域打包

```cpp
uint32_t fCap : 16;             // SkPaint::Cap (实际只需 2 位)
uint32_t fJoin : 15;            // SkPaint::Join (实际只需 2 位)
uint32_t fStrokeAndFill : 1;    // bool
```

设计原因:
- 避免填充字节,确保结构体大小确定
- 保证二进制相等性,用于哈希和比较
- Cap 和 Join 使用超大位数避免初始化填充位

### 等效性比较

```cpp
bool hasEqualEffect(const SkStrokeRec& other) const {
    if (!this->needToApply()) {
        return this->getStyle() == other.getStyle();
    }
    return fWidth == other.fWidth &&
           (fJoin != SkPaint::kMiter_Join || fMiterLimit == other.fMiterLimit) &&
           fCap == other.fCap &&
           fJoin == other.fJoin &&
           fStrokeAndFill == other.fStrokeAndFill;
}
```

优化:当 Join 不是 Miter 时,不比较 `fMiterLimit`(因为不相关)。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPaint` | 提供描边属性的源头 |
| `SkStroke` | 执行实际的描边操作 |
| `SkPath` | 源路径 |
| `SkPathBuilder` | 构建描边后的路径 |
| `SkPaintDefaults` | 提供默认参数值 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| GPU 后端 | 计算描边路径的边界 |
| 路径效果 | 传递描边参数 |
| 图像滤镜 | 计算边界扩展 |
| 裁剪优化 | 判断是否需要描边 |

## 设计模式与设计决策

### 设计模式

1. **值对象模式**: 不可变性为主的设计,修改生成新状态
2. **桥接模式**: 连接高层 SkPaint 和底层 SkStroke
3. **紧凑数据结构**: 使用位域优化内存布局

### 设计决策

**1. 为何使用特殊值编码样式?**
- 节省内存(避免额外的枚举字段)
- 简化判断逻辑(直接比较 fWidth)
- 向后兼容性好

**2. 为何将 ResScale 分离出来?**
- 分辨率缩放不影响逻辑等效性
- 同样的描边参数在不同分辨率下应视为等效
- `hasEqualEffect` 不比较 ResScale

**3. 为何使用位域打包?**
- 减少结构体大小(从 24 字节降到 16 字节,假设 64 位系统)
- 保证哈希计算的正确性(避免未初始化的填充字节)
- 提高缓存友好性

**4. hairline + fill = fill 的规则?**
- hairline 是 1 像素宽,填充已经覆盖了路径内部
- 再填充一次没有视觉意义
- 简化处理逻辑

**5. 为何需要 GetInflationRadius?**
- 裁剪优化:预先计算描边后的边界
- 避免不必要的几何生成
- GPU 渲染需要提前知道几何范围

## 性能考量

### 性能优化

1. **紧凑内存布局**
   - 使用 `SK_BEGIN_REQUIRE_DENSE` 强制紧凑
   - 位域打包减少内存占用
   - 提高缓存命中率

2. **快速路径判断**
   - `needToApply()` 快速判断是否需要描边
   - `hasEqualEffect()` 避免不必要的重新计算

3. **避免虚函数**
   - 纯数据类,无虚函数表开销
   - 可以按值传递和复制

### 调试支持

```cpp
#ifdef SK_DEBUG
bool gDebugStrokerErrorSet = false;
SkScalar gDebugStrokerError;
#endif
```

在调试模式下,可以通过全局变量覆盖 `fResScale`,用于 Viewer 工具实时调整描边精度。

### Hairline 的性能注意事项

计算 hairline 的扩展半径时返回固定值 1.0:
```cpp
if (0 == strokeWidth) {
    // FIXME: 需要 "matrixScale" 参数才能正确处理 hairline
    // hairline 宽度在设备空间确定,与其他描边不同
    return SK_Scalar1;
}
```

这是已知的不精确处理,因为 hairline 的实际宽度取决于变换矩阵。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkPaint.h` | 定义描边属性和枚举 |
| `src/core/SkStroke.h` | 描边算法主类 |
| `src/core/SkStroke.cpp` | 描边算法实现 |
| `src/core/SkStrokerPriv.h` | Cap 和 Join 的底层实现 |
| `src/core/SkPaintDefaults.h` | 默认参数值 |
| `include/core/SkPathBuilder.h` | 路径构建器 |
| `tests/StrokeTest.cpp` | 描边单元测试 |
| `tools/viewer/Viewer.cpp` | 可视化调试工具 |
