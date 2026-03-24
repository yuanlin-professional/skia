# TextBlob - GPU 文本 Blob

> 源文件: `src/text/gpu/TextBlob.h`, `src/text/gpu/TextBlob.cpp`

## 概述

TextBlob 是 Skia GPU 文本渲染系统中的核心缓存对象。它将 SkTextBlob 完全处理为可直接用于 GPU 绘制的格式，包含多个 SubRun（子运行），每个 SubRun 跟踪自己的字形和位置数据。TextBlob 支持缓存重用：当绘制参数（画笔、矩阵等）匹配时，可复用已有的 TextBlob 避免重复处理。

与 Slug 不同，TextBlob 主要用于进程内的缓存重用，不支持跨进程序列化。

## 架构位置

```
sktext::gpu 命名空间
  └── TextBlob (final, SkRefCnt)
        ├── SubRunAllocator
        ├── SubRunContainer
        └── Key (缓存键)
```

- **创建者**: sktext::gpu::TextBlob::Make
- **管理者**: SkTextBlobCache（LRU 缓存，通过内部链表）
- **消费者**: SkDevice::drawTextBlob

## 主要类与结构体

### TextBlob
**成员变量**:
- `fAlloc` (SubRunAllocator): 必须首先声明（最后销毁）
- `fSubRuns` (SubRunContainerOwner): SubRun 容器
- `fSize` (int): 总内存大小
- `fInitialLuminance` (SkColor): 创建时的画笔亮度
- `fKey` (Key): 缓存键

### TextBlob::Key
缓存查找键，用于列表搜索（非哈希表）。

**关键字段**:
- `fUniqueID` — TextBlob 的唯一 ID
- `fCanonicalColor` — 规范化颜色（用于 gamma 校正匹配）
- `fPixelGeometry` — 像素几何（LCD 渲染需要）
- `fBlurRec` — 模糊参数
- `fScalerContextFlags` — ScalerContext 标志
- `fPositionMatrix` — 位置矩阵
- `fHasSomeDirectSubRuns` — 是否有直接 SubRun
- `fStyle / fJoin / fFrameWidth / fMiterLimit` — 画笔风格参数

## 公共 API 函数

```cpp
static sk_sp<TextBlob> Make(const GlyphRunList&, const SkPaint&,
                            const SkMatrix&, SkStrikeDeviceInfo,
                            StrikeForGPUCacheInterface*);
```

```cpp
void draw(SkCanvas*, SkPoint drawOrigin, const SkPaint&, const AtlasDrawDelegate&);
bool canReuse(const SkPaint&, const SkMatrix&) const;
void addKey(const Key& key);
```

## 内部实现细节

### Key 生成（Key::Make）
1. 检查可缓存性（无 PathEffect，MaskFilter 必须是 Blur）
2. 计算规范颜色（LCD 文本使用透明占位，A8 文本按亮度分桶）
3. 判断是否有 Direct SubRun（根据 approximateDeviceTextSize）
4. 有 Direct SubRun 时记录矩阵的小数部分（整数平移差异可兼容）
5. 无 Direct SubRun 时使用单位矩阵（Path 和 SDFT 不依赖矩阵）

### Key 比较
核心逻辑：若有 Direct SubRun，需要检查矩阵的 2x2 部分相同且平移差为整数（通过 `can_use_direct` 判断）。

### canReuse 检查
1. 空 SubRun 且矩阵不匹配时不可复用
2. LCD 文本的亮度变化时不可复用
3. 委托 SubRunContainer::canReuse 做最终判断

### 规范颜色计算
- LCD 文本: 固定返回 SK_ColorTRANSPARENT（因为 LCD 对颜色敏感）
- A8 文本: 计算亮度 -> CanonicalColor 分桶

## 依赖关系

- `SubRunAllocator` — 内存分配（联合分配模式）
- `SubRunContainer` — SubRun 管理
- `GlyphRunList` — 输入数据
- `SkPaintPriv` — 亮度计算
- `SkMaskFilterBase` — Blur 检测
- `SkFontPriv` — 文字大小近似
- `SkTInternalLList` — LRU 链表支持

## 设计模式与设计决策

1. **联合分配**: 与 SlugImpl 相同的 placement new 模式
2. **缓存键设计**: Key 覆盖所有影响渲染结果的参数
3. **Direct SubRun 特判**: 直接 SubRun 对矩阵敏感（整数平移兼容），而 Path/SDFT 不敏感
4. **规范颜色分桶**: 减少因微小颜色差异导致的缓存未命中
5. **亮度追踪**: fInitialLuminance 用于检测 LCD 文本的颜色变化

## 性能考量

- 缓存命中时避免了完整的 SubRunContainer 重建
- Key 比较是线性的（在缓存列表中搜索），但 TextBlob 缓存通常较小
- canReuse 快速失败路径避免了不必要的深度检查
- 联合分配减少堆分配次数

## 相关文件

- `src/text/gpu/SubRunContainer.h` — SubRun 容器
- `src/text/gpu/SlugImpl.h` — Slug（跨进程版本）
- `src/text/gpu/SubRunAllocator.h` — 内存分配器
- `src/text/GlyphRun.h` — 输入数据
- `src/text/gpu/SubRunControl.h` — SubRun 类型决策
