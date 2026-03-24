# SkCustomTypeface

> 源文件: include/utils/SkCustomTypeface.h, src/utils/SkCustomTypeface.cpp

## 概述

SkCustomTypeface 提供了一套工具,允许用户创建自定义字体,其中每个字形可以定义为路径或 Drawable 对象。这是一个强大的功能,支持动态生成字体、特殊效果字体或图标字体。与传统字体文件不同,自定义字体可以在运行时完全通过代码构建,每个字形都可以是任意复杂的图形。

主要功能:
- 通过构建器模式创建自定义字体
- 支持基于路径的字形(矢量字形)
- 支持基于 Drawable 的字形(可执行绘图代码)
- 可序列化和反序列化字体
- 完全集成到 Skia 的 SkTypeface 系统
- 支持字体度量和样式设置

## 架构位置

SkCustomTypeface 位于 Skia 的 utils 模块中,扩展了字体系统:

```
Skia Graphics Library
├── Core
│   ├── SkTypeface (字体抽象基类)
│   ├── SkScalerContext (字形光栅化)
│   ├── SkGlyph (单个字形数据)
│   └── SkFontMetrics (字体度量)
├── Utils
│   ├── SkCustomTypefaceBuilder (构建器) ← 当前模块
│   └── SkUserTypeface (内部实现)
└── Private
    └── SkUserScalerContext (光栅化上下文)
```

该模块通过继承 SkTypeface 实现完整的字体接口,使自定义字体与系统字体无缝集成。

## 主要类与结构体

### SkCustomTypefaceBuilder

**类型**: 构建器类

**继承关系**:
- 无继承,独立的构建器类

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| std::vector<GlyphRec> | fGlyphRecs | 字形记录数组 |
| SkFontMetrics | fMetrics | 字体度量信息 |
| SkFontStyle | fStyle | 字体样式 |

### GlyphRec 结构体

**关键成员变量**:

| 成员类型 | 名称 | 默认值 | 说明 |
|---------|------|-------|------|
| SkPath | fPath | 空路径 | 路径字形数据 |
| sk_sp<SkDrawable> | fDrawable | nullptr | Drawable 字形数据 |
| SkRect | fBounds | {0,0,0,0} | 边界框(仅 Drawable 使用) |
| float | fAdvance | 0 | 字形前进宽度 |

**成员方法**:
- `bool isDrawable() const`: 判断是路径字形还是 Drawable 字形

**设计决策**: fPath 和 fDrawable 是逻辑上的 union,二选一使用。

### SkUserTypeface

**类型**: 内部实现类(final)

**继承关系**:
```
SkRefCnt
  └── SkTypeface
        └── SkUserTypeface (final)
```

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| std::vector<GlyphRec> | fGlyphRecs | 字形数据(移动语义) |
| SkFontMetrics | fMetrics | 字体度量 |

**特性**:
- 标记为 final,不可再继承
- 友元类: SkCustomTypefaceBuilder, SkUserScalerContext
- 私有构造函数,仅通过 Builder 创建

### SkUserScalerContext

**类型**: 光栅化上下文类

**继承关系**:
```
SkScalerContext
  └── SkUserScalerContext
```

**关键成员变量**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| SkMatrix | fMatrix | 变换矩阵(从 SkScalerContextRec 提取) |

**特性**:
- 负责将字形路径/Drawable 转换为位图
- 处理字形度量计算
- 支持子像素定位

## 公共 API 函数

### SkCustomTypefaceBuilder 构造函数

```cpp
SkCustomTypefaceBuilder();
```

**功能**: 创建空的字体构建器。

**初始状态**:
- fMetrics 清零
- fGlyphRecs 为空
- fStyle 使用默认样式

### setGlyph (路径版本)

```cpp
void setGlyph(SkGlyphID index, float advance, const SkPath& path);
```

**功能**: 设置路径字形。

**参数**:
- `index`: 字形 ID
- `advance`: 前进宽度
- `path`: 字形路径

**特性**:
- 自动扩展内部数组以容纳索引
- 清空该字形的 Drawable(确保逻辑互斥)

### setGlyph (Drawable 版本)

```cpp
void setGlyph(SkGlyphID index, float advance,
              sk_sp<SkDrawable> drawable, const SkRect& bounds);
```

**功能**: 设置 Drawable 字形。

**参数**:
- `index`: 字形 ID
- `advance`: 前进宽度
- `drawable`: 绘图对象
- `bounds`: 字形边界框

**特性**:
- Drawable 可以执行任意绘图代码
- 必须提供显式边界框(Drawable 可能无法自动计算)
- 清空该字形的路径

### setMetrics

```cpp
void setMetrics(const SkFontMetrics& fm, float scale = 1);
```

**功能**: 设置字体度量。

**参数**:
- `fm`: 字体度量结构
- `scale`: 可选的缩放因子

**内部处理**:
- 使用 scale_fontmetrics() 对度量进行缩放
- 缩放 x 和 y 方向的所有度量值

### setFontStyle

```cpp
void setFontStyle(SkFontStyle style);
```

**功能**: 设置字体样式(粗细、宽度、倾斜)。

### detach

```cpp
sk_sp<SkTypeface> detach();
```

**功能**: 完成构建,返回 SkTypeface 实例。

**处理流程**:
1. 检查字形记录非空(否则返回 nullptr)
2. 计算所有字形的联合边界框
3. 更新 fMetrics 的边界字段
4. 创建 SkUserTypeface 实例(移动字形数据)
5. 返回 sk_sp<SkTypeface>

**边界计算**:
- 初始化为反转的边界框(最大值)
- 遍历所有字形,联合边界框
- Drawable 字形使用 fBounds
- 路径字形使用 fPath.getBounds()

### MakeFromStream

```cpp
static sk_sp<SkTypeface> MakeFromStream(
    std::unique_ptr<SkStreamAsset> stream,
    const SkFontArguments& args
);
```

**功能**: 从流中反序列化字体。

**返回值**:
- 成功返回 SkTypeface 智能指针
- 失败返回 nullptr

**特性**:
- 内部调用 Deserialize() 静态方法
- SkFontArguments 参数当前未使用

### FactoryId 常量

```cpp
static constexpr SkTypeface::FactoryId FactoryId =
    SkSetFourByteTag('u','s','e','r');
```

**功能**: 字体工厂标识符,'user' 四字节标签。

**用途**: 字体序列化时的类型标识。

## 内部实现细节

### 字形记录管理

#### ensureStorage 方法

```cpp
GlyphRec& ensureStorage(SkGlyphID index) {
    if (index >= fGlyphRecs.size()) {
        fGlyphRecs.resize(SkToSizeT(index) + 1);
    }
    return fGlyphRecs[index];
}
```

**特性**:
- 稀疏数组实现,按需扩展
- 未设置的字形为默认值(空路径,无 Drawable)
- 使用 vector 自动管理内存

### 字体度量缩放

scale_fontmetrics 辅助函数:

```cpp
static SkFontMetrics scale_fontmetrics(const SkFontMetrics& src,
                                       float sx, float sy) {
    // X 方向度量: fAvgCharWidth, fMaxCharWidth, fXMin, fXMax
    // Y 方向度量: fTop, fAscent, fDescent, fBottom, fLeading,
    //            fXHeight, fCapHeight, fUnderlineThickness,
    //            fUnderlinePosition, fStrikeoutThickness,
    //            fStrikeoutPosition
}
```

**应用场景**:
- setMetrics 时应用用户指定的缩放
- generateFontMetrics 时应用变换矩阵的缩放

### SkUserTypeface 实现

#### onFilterRec

```cpp
void onFilterRec(SkScalerContextRec* rec) const override {
    rec->useStrokeForFakeBold();
    rec->setHinting(SkFontHinting::kNone);
}
```

**设计决策**:
- 使用描边模拟粗体(因为没有多个粗细变体)
- 禁用 hinting(自定义字形不需要对齐网格)

#### onCharsToGlyphs

```cpp
void onCharsToGlyphs(SkSpan<const SkUnichar> chars,
                     SkSpan<SkGlyphID> glyphs) const override {
    // 简单映射: Unicode 值 < glyphCount 时直接作为 GlyphID
    // 否则映射到 0 (缺失字形)
}
```

**限制**: 不支持复杂的字符到字形映射。

#### onGetUPEM

```cpp
int onGetUPEM() const override {
    return 2048;
}
```

**说明**: 返回固定值 2048 作为每 em 单位数。

#### 空操作方法

许多字体表查询方法返回空或 0:
- `onGetTableTags`: 返回 0 个表
- `onGetTableData`: 返回 0 字节
- `onGetVariationDesignParameters`: 不支持变体
- `onGetAdvancedMetrics`: 返回 nullptr

### SkUserScalerContext 实现

#### generateMetrics

```cpp
GlyphMetrics generateMetrics(const SkGlyph& glyph, SkArenaAlloc*) override {
    // 1. 检查字形 ID 是否有效
    // 2. 应用变换矩阵计算前进宽度
    // 3. 对于 Drawable 字形:
    //    - 设置 maskFormat 为 ARGB32
    //    - 变换边界框
    //    - 应用子像素偏移
    //    - 设置 neverRequestPath = true
    // 4. 对于路径字形:
    //    - 设置 computeFromPath = true
}
```

**子像素定位**:
- 使用 `getSubXFixed()` 和 `getSubYFixed()` 获取亚像素偏移
- 通过 SkFixedToScalar 转换为浮点
- 偏移边界框以实现子像素精度

#### generateImage

```cpp
void generateImage(const SkGlyph& glyph, void* imageBuffer) override {
    // 路径字形: 调用 generateImageFromPath (基类方法)
    // Drawable 字形:
    //   1. 创建直接光栅 Canvas (MakeRasterDirectN32)
    //   2. 清空为透明 (或调试模式下显示红色)
    //   3. 平移到字形位置
    //   4. 应用子像素偏移
    //   5. 绘制 Drawable
}
```

**调试支持**:
- kSkShowTextBlitCoverage 常量控制调试可视化
- 启用时背景为红色,用于识别光栅化区域

#### generatePath

```cpp
std::optional<SkScalerContext::GeneratedPath> generatePath(
    const SkGlyph& glyph) override {
    // 1. 断言是路径字形(不是 Drawable)
    // 2. 应用变换矩阵 (fPath.makeTransform(fMatrix))
    // 3. 返回 {transformedPath, false}
}
```

**返回值**: {路径, 是否为反锯齿位置敏感}

#### generateDrawable

```cpp
sk_sp<SkDrawable> generateDrawable(const SkGlyph& glyph) override {
    // 如果是 Drawable 字形:
    //   返回 DrawableMatrixWrapper (包装原始 Drawable + 变换矩阵)
    // 否则:
    //   返回 nullptr (路径字形不使用 Drawable)
}
```

**DrawableMatrixWrapper**:
- 嵌套类,包装原始 Drawable
- 应用变换矩阵
- 实现边界框变换
- 可选的调试可视化(绿色覆盖)

#### generateFontMetrics

```cpp
void generateFontMetrics(SkFontMetrics* metrics) override {
    auto [sx, sy] = fMatrix.mapPoint({1, 1});
    *metrics = scale_fontmetrics(this->userTF()->fMetrics, sx, sy);
}
```

**特性**: 从变换矩阵提取缩放因子,应用到字体度量。

### 序列化格式

#### 文件头

```cpp
static const char gHeaderString[] = "SkUserTypeface01";  // 16 字节
```

#### 数据结构

```
[16 字节] 头字符串
[sizeof(SkFontMetrics)] 度量数据
[sizeof(SkFontStyle)] 样式数据
[4 字节] 字形数量 (int32_t)
对于每个字形:
  [4 字节] 字形类型 (GlyphType: kPath=0, kDrawable=1)
  [4 字节] 前进宽度 (float)
  [16 字节] 边界框 (SkRect)
  [size_t] 数据大小
  [变长] 路径/Drawable 序列化数据 (4 字节对齐)
```

#### onOpenStream

序列化到流的实现:

```cpp
std::unique_ptr<SkStreamAsset> onOpenStream(int* ttcIndex) const override {
    // 1. 创建动态内存流
    // 2. 写入头字符串
    // 3. 写入 fMetrics
    // 4. 写入 fontStyle
    // 5. 写入字形数量
    // 6. 遍历字形:
    //    - 写入类型标志
    //    - 写入前进宽度和边界
    //    - 序列化路径或 Drawable
    //    - 写入数据大小和内容
    // 7. 设置 *ttcIndex = 0
    // 8. 返回流
}
```

#### Deserialize

反序列化实现:

```cpp
sk_sp<SkTypeface> Deserialize(SkStream* stream) {
    AutoRestorePosition arp(stream);  // RAII 恢复流位置

    // 1. 读取并验证头字符串
    // 2. 读取 SkFontMetrics
    // 3. 读取 SkFontStyle
    // 4. 读取字形数量 (验证 0 <= count <= kMaxGlyphCount)
    // 5. 创建 SkCustomTypefaceBuilder
    // 6. 遍历字形:
    //    - 读取类型标志 (验证合法性)
    //    - 读取前进宽度和边界 (验证有限性)
    //    - 读取数据大小 (验证与流剩余大小一致)
    //    - 根据类型反序列化:
    //      * kDrawable: 使用 SkDrawable::Deserialize (禁用 SkSL)
    //      * kPath: 使用 SkPath::ReadFromMemory
    //    - 添加到构建器
    // 7. 成功时标记 RAII 完成,失败时恢复流位置
    // 8. 返回 builder.detach()
}
```

**安全性**:
- 验证所有读取的数据范围
- 检查流剩余长度是否足够
- 使用 AutoRestorePosition 确保失败时恢复流位置
- 限制最大字形数量(kMaxGlyphCount = 65536)
- Drawable 反序列化禁用 SkSL(安全考虑)

### 内存管理

**构建器阶段**:
- 使用 std::vector 管理字形记录
- SkPath 和 sk_sp<SkDrawable> 自动管理内存

**detach 后**:
- 通过 std::move 转移 fGlyphRecs 到 SkUserTypeface
- 原构建器失去所有权,可以安全销毁

**字体生命周期**:
- SkUserTypeface 通过 sk_sp<SkTypeface> 引用计数
- 字形数据与字体实例共存亡

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 说明 |
|-----|------|------|
| SkTypeface | 核心接口 | 字体抽象基类 |
| SkScalerContext | 核心光栅化 | 字形光栅化上下文 |
| SkGlyph | 核心数据 | 字形数据结构 |
| SkPath | 核心几何 | 路径字形表示 |
| SkDrawable | 核心绘图 | Drawable 字形表示 |
| SkCanvas | 核心接口 | Drawable 字形光栅化 |
| SkFontMetrics | 核心类型 | 字体度量 |
| SkFontStyle | 核心类型 | 字体样式 |
| SkMatrix | 核心几何 | 变换矩阵 |
| SkStream | 核心 I/O | 序列化/反序列化 |
| SkFontDescriptor | 内部类型 | 字体描述符 |

### 被依赖的模块

| 模块 | 使用场景 | 说明 |
|-----|---------|------|
| 图标字体生成器 | 运行时图标 | 从 SVG/路径创建图标字体 |
| 动画文字效果 | 特效字体 | 字形使用 Drawable 实现动画 |
| 游戏引擎 | 自定义字体 | 艺术字体或特殊符号 |
| 测试框架 | 字体测试 | 创建可控的测试字体 |
| 字体编辑器 | 字体工具 | 可视化字体编辑 |

## 设计模式与设计决策

### 构建器模式 (Builder Pattern)

SkCustomTypefaceBuilder 实现标准构建器:
- **流式接口**: setGlyph, setMetrics, setFontStyle 可以链式调用
- **延迟验证**: detach 时才进行最终验证和边界计算
- **一次性构建**: detach 后构建器失效(移动语义)

**优势**:
- 构建过程清晰,易于理解
- 支持逐步添加字形
- 自动计算字体边界

### 策略模式 (Strategy Pattern)

字形表示策略:
- **路径策略**: 使用 SkPath 表示矢量字形
- **Drawable 策略**: 使用 SkDrawable 表示程序化字形

**优势**:
- 灵活支持两种字形类型
- 统一的接口(GlyphRec)
- 运行时多态(通过 isDrawable() 判断)

### 模板方法模式 (Template Method)

SkScalerContext 继承体系:
- **基类**: 定义光栅化流程框架
- **子类**: 重写 generateMetrics, generateImage, generatePath, generateDrawable

**优势**:
- 复用光栅化基础设施
- 仅需实现特定于自定义字体的逻辑
- 与 Skia 其他字体实现一致

### 工厂方法模式 (Factory Method)

MakeFromStream 静态工厂方法:
- 封装反序列化复杂性
- 统一的创建接口
- 与 Skia 其他 Typeface 工厂一致

### RAII 模式

AutoRestorePosition 类:
```cpp
class AutoRestorePosition {
    ~AutoRestorePosition() {
        if (fStream) {
            fStream->seek(fPosition);
        }
    }
    void markDone() { fStream = nullptr; }
};
```

**用途**: 反序列化失败时自动恢复流位置。

### 逻辑 Union

GlyphRec 的 fPath 和 fDrawable:
- **设计**: 二选一使用,通过 isDrawable() 区分
- **原因**: 避免虚函数开销和类型层次
- **权衡**: 内存略有浪费(未使用字段),但简化代码

### 移动语义

detach 使用 std::move:
- **零拷贝**: 字形数据直接转移到 SkUserTypeface
- **安全**: 构建器清空,防止意外重用
- **性能**: 避免大量字形数据的复制

### 子像素定位

支持亚像素级字形定位:
- 使用 SkFixed 类型(16.16 定点数)
- 在 generateImage 中应用偏移
- 提高文本渲染质量

## 性能考量

### 内存布局

**GlyphRec 大小**:
```
sizeof(GlyphRec) ≈ sizeof(SkPath) + sizeof(sk_sp<SkDrawable>)
                   + sizeof(SkRect) + sizeof(float)
                 ≈ 56 + 8 + 16 + 4 = 84 bytes
```

对于包含 1000 个字形的字体: ~84 KB

### 稀疏数组开销

fGlyphRecs 使用连续数组:
- **优势**: 常数时间访问,良好的缓存局部性
- **劣势**: 稀疏字形集浪费内存(未使用元素为默认值)
- **权衡**: 简单性优于内存效率,现代系统内存充足

### 路径变换

generatePath 使用 makeTransform:
- 创建变换后的新路径副本
- 对频繁调用可能有性能影响
- 可以通过缓存优化(未实现)

### Drawable 光栅化

generateImage 对 Drawable 字形:
- 每次都执行 Drawable 绘图代码
- 可能包含复杂的绘图操作
- 不缓存光栅化结果(由上层缓存管理)

### 序列化性能

onOpenStream 实现:
- 使用 SkDynamicMemoryWStream 缓冲写入
- 路径/Drawable 序列化调用各自的 serialize 方法
- 对大字体可能产生较大数据

### 反序列化安全性

Deserialize 的验证开销:
- 每个字段都进行范围检查
- 验证流剩余长度
- 使用 AutoRestorePosition 的 RAII 开销很小

### 字形查询性能

onCharsToGlyphs 简单映射:
- O(n) 时间,其中 n 是字符数
- 无复杂的 Unicode 映射表
- 适合简单的字符集(ASCII、图标等)

### 缓存策略

字形数据不在 SkUserTypeface 中缓存:
- 光栅化位图由 SkGlyphCache 管理
- 路径变换结果可能重复计算
- 依赖 Skia 的全局缓存系统

### 构建器性能

添加字形的复杂度:
- ensureStorage: O(1) 平均,O(n) 最坏(vector 扩容)
- 边界计算: O(n),其中 n 是字形数量

### Drawable 开销

DrawableMatrixWrapper 的影响:
- 额外的虚函数调用层
- 矩阵变换计算
- 边界框变换

**优化**: 如果变换是单位矩阵,可以跳过包装(未实现)。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/utils/SkCustomTypeface.h | 公共 API 声明 |
| src/utils/SkCustomTypeface.cpp | 实现代码 |
| include/core/SkTypeface.h | 字体基类 |
| src/core/SkScalerContext.h | 光栅化上下文基类 |
| src/core/SkGlyph.h | 字形数据结构 |
| include/core/SkPath.h | 路径几何 |
| include/core/SkDrawable.h | Drawable 接口 |
| include/core/SkCanvas.h | Canvas 绘图接口 |
| include/core/SkFontMetrics.h | 字体度量 |
| include/core/SkFontStyle.h | 字体样式 |
| include/core/SkMatrix.h | 变换矩阵 |
| include/core/SkStream.h | 流 I/O |
| src/core/SkFontDescriptor.h | 字体描述符 |
| include/core/SkFontArguments.h | 字体参数 |
