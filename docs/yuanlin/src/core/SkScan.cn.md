# SkScan

> 源文件: src/core/SkScan.h, src/core/SkScan.cpp

## 概述

`SkScan` 是 Skia 图形库中的扫描转换核心模块,负责将几何图形(路径、矩形、线条等)转换为像素级别的光栅化输出。该模块作为矢量图形到位图渲染的桥梁,提供了填充、描边、抗锯齿等多种扫描转换功能。

`SkScan` 采用静态类设计,提供了完整的光栅化 API,支持从简单的矩形填充到复杂的路径抗锯齿渲染。它与 `SkBlitter` 配合工作,将扫描转换结果输出到目标设备。

## 架构位置

```
Skia 渲染管线
├── SkCanvas (绘制接口层)
├── SkDraw (绘制调度层)
├── SkScan (扫描转换层) ← 当前模块
│   ├── 填充算法
│   ├── 抗锯齿算法
│   └── 路径光栅化
├── SkBlitter (像素输出层)
└── SkDevice (设备抽象层)
```

`SkScan` 位于渲染管线的扫描转换层,接收来自 `SkDraw` 的绘制请求,通过 `SkBlitter` 将像素写入设备。

## 主要类与结构体

### SkScan 类

| 特性 | 说明 |
|------|------|
| 类型 | 静态工具类 |
| 继承关系 | 无继承 |
| 职责 | 提供扫描转换算法 |
| 访问控制 | 公共接口 + 私有内部方法 |

**关键成员变量**

该类为纯静态类,无成员变量。

### SkXRect 类型

| 特性 | 说明 |
|------|------|
| 定义 | `typedef SkIRect SkXRect` |
| 用途 | 定点数矩形表示 |
| 坐标系统 | SkFixed 坐标 (16.16 定点数) |
| 应用场景 | 高精度几何计算 |

### 函数指针类型

| 类型 | 签名 | 用途 |
|------|------|------|
| HairRgnProc | `void (*)(SkSpan<const SkPoint>, const SkRegion*, SkBlitter*)` | 区域裁剪的线条渲染 |
| HairRCProc | `void (*)(SkSpan<const SkPoint>, const SkRasterClip&, SkBlitter*)` | 光栅裁剪的线条渲染 |

## 公共 API 函数

### 路径尺寸检查

```cpp
static bool PathRequiresTiling(const SkIRect& bounds);
```
检查路径是否因尺寸过大需要分块处理。

### 矩形填充

| 函数 | 功能 | 抗锯齿 |
|------|------|--------|
| FillIRect | 填充整数矩形 | 否 |
| FillXRect | 填充定点数矩形 | 否 |
| FillRect | 填充浮点矩形 | 否 |
| AntiFillRect | 填充浮点矩形 | 是 |
| AntiFillXRect | 填充定点数矩形 | 是 |

### 路径填充

```cpp
static void FillPath(const SkPathRaw&, const SkRasterClip&, SkBlitter*);
static void AntiFillPath(const SkPathRaw&, const SkRasterClip&, SkBlitter*);
```
分别提供无抗锯齿和抗锯齿路径填充。

### 几何形状渲染

| 函数 | 形状 | 类型 |
|------|------|------|
| FillTriangle | 三角形 | 填充 |
| FrameRect | 矩形 | 描边 |
| AntiFrameRect | 矩形 | 描边 + 抗锯齿 |

### 线条渲染

| 函数 | 线宽 | 抗锯齿 |
|------|------|--------|
| HairLine | 单像素 | 否 |
| AntiHairLine | 单像素 | 是 |
| HairRect | 矩形描边 | 否 |
| AntiHairRect | 矩形描边 | 是 |

### 路径描边

```cpp
static void HairPath(const SkPathRaw&, const SkRasterClip&, SkBlitter*);
static void AntiHairPath(const SkPathRaw&, const SkRasterClip&, SkBlitter*);
static void HairSquarePath(const SkPathRaw&, const SkRasterClip&, SkBlitter*);  // 方形端点
static void HairRoundPath(const SkPathRaw&, const SkRasterClip&, SkBlitter*);   // 圆形端点
```

## 内部实现细节

### 矩形填充实现

`FillIRect` 实现了高效的矩形填充逻辑:

1. **空矩形检查**: 提前返回,避免无效计算
2. **裁剪优化**:
   - 矩形裁剪: 直接计算交集
   - 复杂裁剪: 使用 `SkRegion::Cliperator` 迭代
3. **Blitter 调用**: 通过 `blitRect` 输出像素

```cpp
void SkScan::FillIRect(const SkIRect& r, const SkRegion* clip, SkBlitter* blitter) {
    if (!r.isEmpty()) {
        if (clip) {
            if (clip->isRect()) {
                // 矩形裁剪快速路径
                const SkIRect& clipBounds = clip->getBounds();
                if (clipBounds.contains(r)) {
                    blitrect(blitter, r);
                } else {
                    SkIRect rr = r;
                    if (rr.intersect(clipBounds)) {
                        blitrect(blitter, rr);
                    }
                }
            } else {
                // 复杂裁剪区域迭代
                SkRegion::Cliperator cliper(*clip, r);
                while (!cliper.done()) {
                    blitrect(blitter, cliper.rect());
                    cliper.next();
                }
            }
        } else {
            blitrect(blitter, r);
        }
    }
}
```

### 定点数转换

提供了完整的定点数与整数/浮点数之间的转换:

- **XRect_set**: 将 `SkIRect` 或 `SkRect` 转换为 `SkXRect`
- **XRect_round**: 四舍五入转换为 `SkIRect`
- **XRect_roundOut**: 向外扩展转换 (floor/ceil)

### RasterClip 处理

针对 `SkRasterClip` 的双路径处理策略:

1. **BW 路径** (`clip.isBW()`): 使用简单的 `SkRegion`
2. **AA 路径**: 使用 `SkAAClipBlitterWrapper` 包装

```cpp
void SkScan::FillIRect(const SkIRect& r, const SkRasterClip& clip, SkBlitter* blitter) {
    if (clip.isEmpty() || r.isEmpty()) {
        return;
    }
    if (clip.isBW()) {
        FillIRect(r, &clip.bwRgn(), blitter);
        return;
    }
    SkAAClipBlitterWrapper wrapper(clip, blitter);
    FillIRect(r, &wrapper.getRgn(), wrapper.getBlitter());
}
```

### 友元访问

`SkAAClip` 和 `SkRegion` 声明为友元类,可访问私有的 `SkRegion*` 版本函数,实现内部优化。

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkBlitter | 像素输出 | src/core/SkBlitter.h |
| SkRasterClip | 裁剪管理 | src/core/SkRasterClip.h |
| SkRegion | 区域裁剪 | include/core/SkRegion.h |
| SkPathRaw | 路径数据 | src/core/SkPathRaw.h |
| SkFixed | 定点数运算 | include/private/base/SkFixed.h |
| SkPoint | 点坐标 | include/core/SkPoint.h |
| SkRect | 矩形几何 | include/core/SkRect.h |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkDraw | 绘制调度层调用扫描转换 |
| SkAAClip | 抗锯齿裁剪使用内部函数 |
| SkRegion | 区域操作使用分块渲染 |
| SkScan_AAAPath | 解析式抗锯齿调用基础函数 |
| SkScan_Path | 传统路径扫描调用基础函数 |

## 设计模式与设计决策

### 1. 静态工具类模式

**设计决策**: 将所有扫描转换函数实现为静态方法

**优点**:
- 无需实例化,降低内存开销
- 明确的无状态语义
- 便于全局访问

**缺点**:
- 扩展性受限
- 无法使用多态

### 2. 策略模式 (通过函数指针)

`HairRgnProc` 和 `HairRCProc` 函数指针类型允许运行时选择不同的线条渲染策略。

### 3. 模板方法模式

提供了三层 API 抽象:

```
FillIRect(SkIRect, SkRasterClip, SkBlitter)  // 用户接口
    ↓
FillIRect(SkIRect, SkRegion*, SkBlitter)     // 内部分发
    ↓
blitrect(SkBlitter, SkIRect)                  // 底层实现
```

### 4. 双路径优化

针对常见场景提供特化实现:

- **矩形裁剪**: 快速交集计算
- **BW 裁剪**: 跳过 AA 包装开销
- **空检查**: 提前退出避免计算

### 5. 友元类设计

允许 `SkAAClip` 和 `SkRegion` 访问私有 API,在保持封装性的同时实现性能优化。

## 性能考量

### 1. 矩形填充优化

- **快速路径**: 完全包含时跳过裁剪计算
- **交集复用**: 预先计算交集避免重复计算
- **批量 Blit**: 尽可能使用大块 `blitRect` 而非逐像素 `blitH`

### 2. 定点数运算

使用 `SkFixed` (16.16 定点数) 而非浮点数:
- 避免浮点运算开销
- 保证位运算可预测性
- 适配低精度设备

### 3. 裁剪迭代器

使用 `SkRegion::Cliperator` 高效遍历复杂裁剪区域,避免逐像素判断。

### 4. 空检查优化

在函数入口处检查空矩形和空裁剪,避免不必要的计算。

### 5. 内联辅助函数

`blitrect` 声明为 `static inline`,编译器可内联优化热点路径。

### 6. 分层 API 设计

提供 `IRect`、`XRect`、`Rect` 三种重载,避免不必要的类型转换开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkScan_AAAPath.cpp | 扩展实现 | 解析式抗锯齿路径扫描 |
| src/core/SkScan_Hairline.cpp | 扩展实现 | 单像素线条渲染 |
| src/core/SkScan_Path.cpp | 扩展实现 | 传统路径扫描算法 |
| src/core/SkScanPriv.h | 内部头文件 | 扫描转换内部工具 |
| src/core/SkBlitter.h | 依赖 | 像素输出接口 |
| src/core/SkRasterClip.h | 依赖 | 光栅裁剪管理 |
| src/core/SkDraw.cpp | 使用者 | 绘制调度层 |
| src/core/SkAAClip.cpp | 友元 | 抗锯齿裁剪 |
| include/core/SkRegion.h | 依赖 | 区域裁剪 |
| include/private/base/SkFixed.h | 依赖 | 定点数类型 |
