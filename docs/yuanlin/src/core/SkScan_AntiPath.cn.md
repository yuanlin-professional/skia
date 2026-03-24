# SkScan_AntiPath

> 源文件
> - src/core/SkScan_AntiPath.cpp

## 概述

`SkScan_AntiPath.cpp` 实现了反走样路径填充的主入口和调度逻辑。该模块负责检查路径边界、管理裁剪区域、处理反向填充(inverse fill),并将实际的扫描转换工作委派给专门的反走样算法(如 `AAAFillPath`)。它作为 Skia 反走样路径渲染管道的核心调度层,确保正确的预处理和边界条件处理。

## 架构位置

`SkScan_AntiPath` 位于 Skia 扫描转换(scan conversion)子系统的顶层:

- **调度层**: 在 `SkDraw` 和具体反走样算法之间
- **预处理**: 处理裁剪、边界检查、反向填充
- **算法选择**: 根据尺寸和条件选择反走样或非反走样路径

## 主要类与结构体

本文件主要包含两个重载的公共函数,无独立类定义。主要使用的类来自依赖模块:

### 依赖的关键类型

| 类型 | 来源 | 用途 |
|------|------|------|
| `SkPathRaw` | `src/core/SkPathRaw.h` | 底层路径表示 |
| `SkRegion` | `include/core/SkRegion.h` | 裁剪区域 |
| `SkRasterClip` | `src/core/SkRasterClip.h` | 光栅裁剪(BW或AA) |
| `SkBlitter` | `src/core/SkBlitter.h` | 像素填充接口 |
| `SkAAClipBlitter` | `src/core/SkAAClip.h` | AA 裁剪适配器 |

## 公共 API 函数

### SkScan::AntiFillPath (SkRegion 版本)

```cpp
void SkScan::AntiFillPath(const SkPathRaw& path,
                          const SkRegion& origClip,
                          SkBlitter* blitter,
                          bool forceRLE);
```

**功能**: 使用反走样填充路径

**参数**:
- `path`: 底层路径表示
- `origClip`: 裁剪区域(整数像素精度)
- `blitter`: 像素填充器
- `forceRLE`: 是否强制使用 RLE(行程编码)模式

**核心流程**:
1. 检查裁剪区域是否为空
2. 计算路径边界并检查是否需要反向填充
3. 检查是否超出超采样范围(需要回退到非反走样)
4. 限制裁剪区域到 32767 像素(16位索引限制)
5. 处理反向填充的上方区域
6. 调用 `AAAFillPath` 执行实际扫描转换
7. 处理反向填充的下方区域

### SkScan::AntiFillPath (SkRasterClip 版本)

```cpp
void SkScan::AntiFillPath(const SkPathRaw& raw,
                          const SkRasterClip& clip,
                          SkBlitter* blitter);
```

**功能**: 使用光栅裁剪的反走样路径填充

**参数**:
- `raw`: 底层路径表示
- `clip`: 光栅裁剪(可能是 BW 或 AA)
- `blitter`: 像素填充器

**核心流程**:
1. 判断裁剪类型(BW 或 AA)
2. 对于 BW 裁剪: 直接调用 `SkRegion` 版本
3. 对于 AA 裁剪: 使用 `SkAAClipBlitter` 包装后调用

## 内部实现细节

### 安全边界计算

```cpp
static SkIRect safeRoundOut(const SkRect& src) {
    SkIRect dst = src.roundOut();

    // 限制到安全范围,避免尺寸溢出
    const int32_t limit = SK_MaxS32 >> SK_SUPERSAMPLE_SHIFT;
    (void)dst.intersect({ -limit, -limit, limit, limit });

    return dst;
}
```

**原理**:
- 超采样会放大坐标(通常左移3位,8x8超采样)
- 限制范围确保 `(coord << SHIFT)` 不溢出 32 位整数

### 超采样溢出检查

```cpp
static int overflows_short_shift(int value, int shift) {
    const int s = 16 + shift;
    return (SkLeftShift(value, s) >> s) - value;
}

static int rect_overflows_short_shift(SkIRect rect, int shift) {
    return overflows_short_shift(rect.fLeft, shift) |
           overflows_short_shift(rect.fRight, shift) |
           overflows_short_shift(rect.fTop, shift) |
           overflows_short_shift(rect.fBottom, shift);
}
```

**检查目的**:
- 反走样使用 16 位短整数存储超采样坐标
- 如果坐标左移后超出 16 位,回退到非反走样路径

```cpp
if (rect_overflows_short_shift(clippedIR, SK_SUPERSAMPLE_SHIFT)) {
    SkScan::FillPath(path, origClip, blitter);  // 回退到无反走样
    return;
}
```

### 裁剪区域限制

```cpp
static const int32_t kMaxClipCoord = 32767;
const SkIRect& bounds = origClip.getBounds();

if (bounds.fRight > kMaxClipCoord || bounds.fBottom > kMaxClipCoord) {
    SkIRect limit = { 0, 0, kMaxClipCoord, kMaxClipCoord };
    tmpClipStorage.op(origClip, limit, SkRegion::kIntersect_Op);
    clipRgn = &tmpClipStorage;
}
```

**原因**:
- 反走样使用 `int16_t` 存储行索引
- 32767 是 16 位有符号整数的最大值

### 反向填充处理

```cpp
if (isInverse) {
    // 填充裁剪区域中路径边界之外的部分
    sk_blit_above(blitter, ir, *clipRgn);  // 上方
}

SkScan::AAAFillPath(path, blitter, ir, clipRgn->getBounds(), forceRLE);

if (isInverse) {
    sk_blit_below(blitter, ir, *clipRgn);  // 下方
}
```

**反向填充逻辑**:
1. **上方区域**: 从裁剪顶部到路径顶部
2. **路径区域**: 正常填充(但使用反向规则)
3. **下方区域**: 从路径底部到裁剪底部

### SkAAClipBlitter 包装

```cpp
if (!clip.isBW()) {
    SkRegion tmp;
    SkAAClipBlitter aaBlitter;

    tmp.setRect(clip.getBounds());
    aaBlitter.init(blitter, &clip.aaRgn());
    AntiFillPath(raw, tmp, &aaBlitter, true);  // forceRLE=true
}
```

**包装原因**:
- `SkAAClipBlitter` 可以处理 `blitMask`,支持反走样裁剪
- 设置 `forceRLE=true` 因为 `SkAAClipBlitter` 需要 mask 格式

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkScan::AAAFillPath` | 实际的反走样扫描转换算法 |
| `SkScan::FillPath` | 回退的非反走样路径填充 |
| `SkScanClipper` | 裁剪区域管理 |
| `sk_blit_above/below` | 反向填充辅助函数 |
| `SkAAClipBlitter` | AA 裁剪适配器 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkDraw` | 高层绘制调度,调用 `AntiFillPath` |
| `SkCanvas` | 用户 API,通过 `SkDraw` 间接调用 |
| 图像滤镜 | 需要反走样路径渲染的效果 |

## 设计模式与设计决策

### 1. 门面模式(Facade Pattern)

`AntiFillPath` 隐藏复杂的预处理和条件分支:

```cpp
void AntiFillPath(...) {
    // 隐藏的复杂性:
    // - 边界检查
    // - 溢出检测
    // - 裁剪限制
    // - 反向填充处理

    // 简单的接口给调用者
    AAAFillPath(path, blitter, ...);
}
```

### 2. 适配器模式(Adapter Pattern)

`SkAAClipBlitter` 适配 AA 裁剪到标准 `SkBlitter` 接口:

```cpp
// 原始 blitter 不理解 AA 裁剪
// SkAAClipBlitter 将 AA 裁剪转换为 mask 操作
aaBlitter.init(blitter, &clip.aaRgn());
```

### 3. 策略模式(Strategy Pattern)

根据条件选择不同填充策略:
- **反走样**: `AAAFillPath`
- **非反走样**: `FillPath`
- **BW 裁剪**: 直接调用
- **AA 裁剪**: 通过 `SkAAClipBlitter`

### 4. 渐进式降级

遇到限制时降级到更简单的实现:

```cpp
// 尝试反走样
if (rect_overflows_short_shift(...)) {
    // 降级到非反走样
    SkScan::FillPath(...);
    return;
}
// 继续反走样路径...
```

## 性能考量

### 1. 早期退出优化

```cpp
if (origClip.isEmpty()) return;
if (ir.isEmpty()) { /* 处理空路径 */ return; }
```

### 2. 空间限制检查

避免不必要的大内存分配:

```cpp
if (rect_overflows_short_shift(clippedIR, SK_SUPERSAMPLE_SHIFT)) {
    // 回退到非超采样,节省内存
    SkScan::FillPath(path, origClip, blitter);
    return;
}
```

### 3. 裁剪优化

```cpp
if (clipper.getClipRect() == nullptr) {
    // 路径完全在裁剪区域内,跳过逐像素裁剪
    pathContainedInClip = true;
}
```

### 4. 反向填充优化

```cpp
// 只在需要时填充上方/下方
if (isInverse) {
    sk_blit_above(...);  // 条件执行
}
```

### 5. RLE 模式选择

```cpp
// AA 裁剪强制 RLE 模式(更紧凑的内存表示)
AntiFillPath(raw, tmp, &aaBlitter, true);  // forceRLE=true
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkScan_AntiPath.cpp` | 本文件(反走样路径调度) |
| `src/core/SkScan.h` | 扫描转换公共接口 |
| `src/core/SkAAClip.h` | AA 裁剪实现 |
| `src/core/SkRasterClip.h` | 光栅裁剪管理 |
| `src/core/SkBlitter.h` | 像素填充接口 |
| `src/core/SkScanPriv.h` | 扫描转换内部辅助函数 |
| `src/core/SkPathRaw.h` | 路径底层表示 |
| `src/core/SkDraw.cpp` | 调用本模块的主要位置 |
