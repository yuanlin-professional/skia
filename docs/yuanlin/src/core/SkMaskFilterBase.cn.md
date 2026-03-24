# SkMaskFilterBase

> 源文件: src/core/SkMaskFilterBase.h, src/core/SkMaskFilterBase.cpp

## 概述

`SkMaskFilterBase` 是 Skia 图形库中 mask filter (遮罩滤镜) 的内部基类,它扩展了公共 API 类 `SkMaskFilter`,提供了滤镜实现所需的核心接口和工具方法。该类支持对 alpha 遮罩进行各种变换操作,如模糊、浮雕等效果,并通过 nine-patch 优化技术提升性能。

## 架构位置

`SkMaskFilterBase` 位于 Skia 渲染管线的遮罩处理层:
- 作为 `SkMaskFilter` 的内部实现基类,对外隐藏具体实现细节
- 与 `SkBlitter` 配合完成遮罩的光栅化渲染
- 为 blur、emboss、SDF、shader、table 等具体滤镜类型提供统一接口
- 通过 `SkResourceCache` 实现 nine-patch 缓存优化

## 主要类与结构体

### 继承关系

| 类名 | 父类 | 说明 |
|------|------|------|
| SkMaskFilterBase | SkMaskFilter | 内部实现基类 |
| NinePatch | SkNoncopyable | Nine-patch 优化数据结构 |

### 关键成员变量

**SkMaskFilterBase::NinePatch**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fMask | SkMask | 遮罩数据 (bounds 必须从 [0,0] 开始) |
| fOuterRect | SkIRect | 外围矩形 (宽高必须 >= fMask.fBounds) |
| fCenter | SkIPoint | 拉伸中心点位置 |
| fCache | SkCachedData* | 缓存数据指针 (可选) |

## 公共 API 函数

### 核心虚函数

```cpp
// 返回滤镜生成的遮罩格式
virtual SkMask::Format getFormat() const = 0;

// 对源遮罩应用滤镜效果
virtual bool filterMask(SkMaskBuilder* dst, const SkMask& src,
                       const SkMatrix& matrix, SkIPoint* margin) const = 0;

// 返回滤镜类型
virtual Type type() const = 0;
```

### 边界计算

```cpp
// 计算滤镜后的快速边界
virtual void computeFastBounds(const SkRect& src, SkRect* dest) const;
```

### 转换函数

```cpp
// 尝试转换为模糊参数
virtual bool asABlur(BlurRec*) const;

// 转换为 ImageFilter 表示
virtual std::pair<sk_sp<SkImageFilter>, bool> asImageFilter(
    const SkMatrix& ctm, const SkPaint& paint) const;
```

### Nine-Patch 优化

```cpp
// 矩形到 nine-patch 转换
virtual FilterReturn filterRectsToNine(SkSpan<const SkRect>, const SkMatrix&,
                                      const SkIRect& clipBounds,
                                      std::optional<NinePatch>*,
                                      SkResourceCache*) const;

// 圆角矩形到 nine-patch 转换
virtual std::optional<NinePatch> filterRRectToNine(const SkRRect&,
                                                  const SkMatrix&,
                                                  const SkIRect& clipBounds,
                                                  SkResourceCache*) const;
```

## 内部实现细节

### Nine-Patch 绘制机制

系统通过 `draw_nine()` 和 `draw_nine_clipped()` 实现 nine-patch 拉伸绘制:
1. **角落绘制**: 四个角落保持原始大小不变
2. **边缘拉伸**: 上下左右四条边使用中心扫描线重复填充
3. **中心填充**: 可选的中心区域填充

代码示例:
```cpp
// 提取遮罩子集
SkMask m = extract_mask_subset(mask, bounds, outerR.left(), outerR.top());
blit_clipped_mask(blitter, m, m.fBounds, clipR);
```

### 路径过滤流程

`filterPath()` 方法处理路径遮罩:
1. 检测是否为嵌套矩形,尝试 nine-patch 优化
2. 将路径光栅化为 A8 格式遮罩
3. 调用 `filterMask()` 应用滤镜效果
4. 使用 `SkBlitter` 渲染最终遮罩

### 圆角矩形优化

`filterRRect()` 专门优化圆角矩形:
```cpp
std::optional<NinePatch> patch =
    this->filterRRectToNine(devRRect, matrix, clip.getBounds(), cache);
if (patch.has_value()) {
    draw_nine(patch->fMask, patch->fOuterRect, patch->fCenter, true, clip, blitter);
    return true;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkMask | 遮罩数据结构 |
| SkBlitter | 像素绘制 |
| SkRasterClip | 裁剪区域管理 |
| SkResourceCache | Nine-patch 缓存 |
| SkCachedData | 缓存数据封装 |
| SkPathPriv | 路径内部工具 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkBlurMaskFilterImpl | 具体的模糊滤镜实现 |
| SkEmbossMaskFilter | 浮雕滤镜实现 |
| skcpu::Draw | CPU 绘制系统 |

## 设计模式与设计决策

### 1. 模板方法模式
基类定义滤镜处理框架,子类实现具体算法:
- `filterMask()`: 核心滤镜算法
- `type()`: 类型识别
- `getFormat()`: 输出格式

### 2. Nine-Patch 优化策略
通过缓存和重用可拉伸的小遮罩减少计算:
- 对于大面积的模糊效果,只计算边缘小块
- 中心区域通过复制扫描线快速填充
- 使用 `SkResourceCache` 缓存计算结果

### 3. FilterReturn 三态返回
```cpp
enum class FilterReturn {
    kFalse,          // 失败
    kTrue,           // 成功
    kUnimplemented,  // 未实现,回退到默认方法
};
```
允许子类选择性实现优化路径。

### 4. 内部实现隐藏
使用辅助函数 `as_MFB()` 进行类型转换:
```cpp
inline SkMaskFilterBase* as_MFB(SkMaskFilter* mf) {
    return static_cast<SkMaskFilterBase*>(mf);
}
```

## 性能考量

### 1. Nine-Patch 缓存
- 减少大区域模糊的重复计算
- 特别适合 UI 元素的阴影效果

### 2. 快速边界计算
`computeFastBounds()` 允许提前裁剪优化:
```cpp
void computeFastBounds(const SkRect& src, SkRect* dst) const {
    SkMask srcM(nullptr, src.roundOut(), 0, SkMask::kA8_Format);
    SkMaskBuilder dstM;
    if (this->filterMask(&dstM, srcM, SkMatrix::I(), &margin)) {
        dst->set(dstM.fBounds);
    }
}
```

### 3. 形状检测优化
通过 `countNestedRects()` 检测嵌套矩形,使用专门的优化路径:
```cpp
int rectCount = countNestedRects(devRaw, rects);
if (rectCount > 0) {
    switch (this->filterRects(...)) {
        case FilterReturn::kTrue: return true;
        // ...
    }
}
```

### 4. Fuzzer 保护
```cpp
#if defined(SK_BUILD_FOR_FUZZER)
if (devRaw.verbs().size() > 1000 || devRaw.points().size() > 1000) {
    return false;
}
#endif
```
防止模糊测试时的资源耗尽。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkMaskFilter.h | 公共接口 | 公共 API 定义 |
| src/core/SkMask.h | 数据结构 | 遮罩数据类型 |
| src/core/SkBlitter.h | 渲染后端 | 像素级绘制 |
| src/core/SkMaskCache.h | 缓存系统 | Nine-patch 缓存 |
| src/core/SkMaskBlurFilter.h | 具体实现 | 模糊算法实现 |
| src/core/SkDraw.h | 绘制系统 | CPU 绘制接口 |
| src/core/SkResourceCache.h | 资源管理 | 通用缓存机制 |
