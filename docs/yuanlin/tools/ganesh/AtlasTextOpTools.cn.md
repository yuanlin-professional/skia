# AtlasTextOpTools

> 源文件: tools/ganesh/AtlasTextOpTools.h, tools/ganesh/AtlasTextOpTools.cpp

## 概述

`AtlasTextOpTools` 是一个用于创建文本渲染操作(AtlasTextOp)的工具类,专门为 Skia 的 Ganesh GPU 后端提供测试和调试支持。该类封装了从高层文本 API(SkFont, SkPaint)到底层 GPU 操作的转换逻辑,使得测试代码能够直接生成文本渲染的 GrOp 对象,而无需经过完整的绘制管线。

该工具类主要用于单元测试和 GPU 操作测试场景,提供了一种简化的方式来验证文本 atlas 系统和 GPU 文本渲染路径的正确性。它隐藏了字形运行(GlyphRun)构建、文本 blob 创建、子运行(SubRun)生成等复杂细节,提供清晰的测试入口。

## 架构位置

该类位于 Skia 工具层的 Ganesh 特定测试工具模块:

```
skia/
  tools/
    ganesh/
      AtlasTextOpTools.h        # 工具类声明
      AtlasTextOpTools.cpp      # 工具类实现
```

在架构层次中的位置:
- **上层**: 测试代码和基准测试工具
- **本层**: Ganesh 测试工具(AtlasTextOpTools)
- **下层**:
  - `src/gpu/ganesh/ops/AtlasTextOp`: 实际的文本操作实现
  - `src/text/gpu/TextBlob`: GPU 文本 blob 系统
  - `src/gpu/ganesh/SurfaceDrawContext`: 绘制上下文

## 主要类与结构体

### AtlasTextOpTools

```cpp
namespace skgpu::ganesh {

class AtlasTextOpTools final {
public:
    static GrOp::Owner CreateOp(SurfaceDrawContext* sdc,
                                const SkPaint& paint,
                                const SkFont& font,
                                const SkMatrix& ctm,
                                const char* text,
                                int x,
                                int y);

private:
    AtlasTextOpTools();  // 不可实例化
};

}  // namespace skgpu::ganesh
```

这是一个纯静态工具类:
- **不可实例化**: 构造函数私有
- **单一职责**: 仅提供一个静态工具函数
- **命名空间隔离**: 位于 `skgpu::ganesh` 命名空间

## 公共 API 函数

### CreateOp()

```cpp
static GrOp::Owner CreateOp(SurfaceDrawContext* sdc,
                            const SkPaint& paint,
                            const SkFont& font,
                            const SkMatrix& ctm,
                            const char* text,
                            int x,
                            int y);
```

**功能**: 创建一个文本渲染操作(AtlasTextOp)

**参数说明**:
- `sdc`: 表面绘制上下文,提供渲染目标和配置信息
- `paint`: 绘制样式,包含颜色、混合模式等
- `font`: 字体配置,包含字号、抗锯齿设置等
- `ctm`: 当前变换矩阵,用于定位和变换文本
- `text`: 要渲染的文本字符串(C 风格字符串)
- `x`, `y`: 文本绘制的起始位置

**返回值**:
- `GrOp::Owner`: 文本操作的智能指针
- 如果创建失败(如空字形运行),返回 `nullptr`

**使用示例**:
```cpp
// 在测试代码中
GrOp::Owner op = AtlasTextOpTools::CreateOp(
    sdc,
    paint,
    font,
    SkMatrix::I(),  // 单位矩阵
    "Hello World",
    100, 200        // 位置
);
if (op) {
    sdc->addDrawOp(std::move(op));
}
```

## 内部实现细节

### 实现流程

```cpp
GrOp::Owner AtlasTextOpTools::CreateOp(SurfaceDrawContext* sdc,
                                       const SkPaint& skPaint,
                                       const SkFont& font,
                                       const SkMatrix& ctm,
                                       const char* text,
                                       int x, int y) {
    size_t textLen = strlen(text);

    // 步骤 1: 准备变换矩阵
    SkMatrix drawMatrix = ctm;
    drawMatrix.preTranslate(x, y);
    auto drawOrigin = SkPoint::Make(x, y);

    // 步骤 2: 将文本转换为字形运行
    sktext::GlyphRunBuilder builder;
    auto glyphRunList = builder.textToGlyphRunList(
        font, skPaint, text, textLen, drawOrigin);
    if (glyphRunList.empty()) {
        return nullptr;
    }

    // 步骤 3: 获取子运行控制器
    auto rContext = sdc->recordingContext();
    sktext::gpu::SubRunControl control =
        rContext->priv().getSubRunControl(
            sdc->surfaceProps().isUseDeviceIndependentFonts());

    // 步骤 4: 创建设备信息
    SkStrikeDeviceInfo strikeDeviceInfo{
        sdc->surfaceProps(),
        SkScalerContextFlags::kBoostContrast,
        &control
    };

    // 步骤 5: 创建文本 blob
    sk_sp<sktext::gpu::TextBlob> blob =
        sktext::gpu::TextBlob::Make(
            glyphRunList, skPaint, drawMatrix,
            strikeDeviceInfo, SkStrikeCache::GlobalStrikeCache());

    // 步骤 6: 获取第一个子运行
    const sktext::gpu::AtlasSubRun* subRun =
        sktext::gpu::TextBlobTools::FirstSubRun(blob.get());
    if (!subRun) {
        return nullptr;
    }

    // 步骤 7: 创建 AtlasTextOp
    GrOp::Owner op;
    std::tie(std::ignore, op) =
        AtlasTextOp::Make(sdc, subRun, nullptr, ctm,
                         glyphRunList.origin(), skPaint, blob);
    return op;
}
```

### 关键步骤解析

**1. 字形运行构建**:
```cpp
sktext::GlyphRunBuilder builder;
auto glyphRunList = builder.textToGlyphRunList(font, skPaint, text, textLen, drawOrigin);
```
将文本字符串转换为字形 ID 列表,这是文本渲染的第一步。

**2. 子运行控制**:
```cpp
sktext::gpu::SubRunControl control =
    rContext->priv().getSubRunControl(
        sdc->surfaceProps().isUseDeviceIndependentFonts());
```
根据是否使用设备独立字体获取相应的子运行控制器,影响字形缓存策略。

**3. 设备信息配置**:
```cpp
SkStrikeDeviceInfo strikeDeviceInfo{
    sdc->surfaceProps(),
    SkScalerContextFlags::kBoostContrast,  // 增强对比度
    &control
};
```
配置字形光栅化参数,`kBoostContrast` 标志提高文本可读性。

**4. TextBlob 创建**:
```cpp
sk_sp<sktext::gpu::TextBlob> blob =
    sktext::gpu::TextBlob::Make(glyphRunList, skPaint, drawMatrix,
                                strikeDeviceInfo, SkStrikeCache::GlobalStrikeCache());
```
将字形运行转换为 GPU 文本 blob,执行字形定位和分类。

**5. 子运行提取**:
```cpp
const sktext::gpu::AtlasSubRun* subRun =
    sktext::gpu::TextBlobTools::FirstSubRun(blob.get());
```
获取第一个 atlas 子运行,子运行代表一组可以批处理的字形。

**6. AtlasTextOp 创建**:
```cpp
std::tie(std::ignore, op) =
    AtlasTextOp::Make(sdc, subRun, nullptr, ctm, glyphRunList.origin(), skPaint, blob);
```
创建实际的 GPU 操作对象,准备提交到命令缓冲区。

### 与正常绘制路径的差异

**正常路径**:
```
SkCanvas::drawText()
  → SkDevice::drawGlyphRunList()
    → SurfaceDrawContext::drawGlyphRunList()
      → TextBlob creation
        → SubRun generation
          → AtlasTextOp::Make()
```

**工具路径**:
```
AtlasTextOpTools::CreateOp()
  → 直接创建 GlyphRunList
    → 直接创建 TextBlob
      → 直接创建 AtlasTextOp
```

工具路径跳过了 SkCanvas 和 SkDevice 层,直接访问底层实现,适合测试。

## 依赖关系

**核心依赖**:
- `src/gpu/ganesh/ops/AtlasTextOp.h`: 文本操作实现
- `src/text/gpu/TextBlob.h`: GPU 文本 blob
- `src/text/GlyphRun.h`: 字形运行
- `src/gpu/ganesh/SurfaceDrawContext.h`: 绘制上下文
- `src/core/SkStrikeCache.h`: 字形缓存

**辅助依赖**:
- `tools/text/gpu/TextBlobTools.h`: TextBlob 测试工具
- `src/core/SkScalerContext.h`: 字形缩放上下文

**条件依赖**:
```cpp
#if defined(GPU_TEST_UTILS)
#include "src/gpu/ganesh/GrDrawOpTest.h"
#include "src/gpu/ganesh/GrTestUtils.h"
#endif
```
测试工具仅在定义 `GPU_TEST_UTILS` 时编译。

## 设计模式与设计决策

### 1. Static Utility Class Pattern

```cpp
class AtlasTextOpTools final {
public:
    static GrOp::Owner CreateOp(...);
private:
    AtlasTextOpTools();  // 不可实例化
};
```

**优点**:
- 明确表示无状态工具
- 避免不必要的实例化
- 清晰的 API 边界

### 2. Factory Pattern

`CreateOp()` 是一个工厂方法:
- 隐藏复杂的对象创建逻辑
- 提供简单的参数化接口
- 统一的错误处理(返回 nullptr)

### 3. Namespace Isolation

```cpp
namespace skgpu::ganesh {
    class AtlasTextOpTools final { ... };
}
```

将工具类放入特定命名空间,避免命名冲突,明确其用途和范围。

### 4. 设计决策

**为何只创建单个操作**:
测试通常针对特定场景,单个操作足以验证文本渲染路径,避免复杂性。

**为何使用 C 字符串**:
```cpp
const char* text
```
简化测试代码编写,与常见的字符串字面量兼容。

**为何返回 GrOp::Owner**:
使用智能指针管理操作生命周期,确保内存安全。

**为何需要 SurfaceDrawContext**:
获取渲染配置、设备能力和录制上下文,这些是创建正确 GPU 操作的必要条件。

## 性能考量

### 1. 测试专用

此类仅用于测试,不在生产代码路径中,因此:
- 不需要极致的性能优化
- 简洁性和可读性优先
- 允许额外的错误检查

### 2. 字形运行构建开销

```cpp
auto glyphRunList = builder.textToGlyphRunList(font, skPaint, text, textLen, drawOrigin);
```

每次调用都重新构建字形运行,测试场景可接受,但不适合高频调用。

### 3. TextBlob 创建

```cpp
sk_sp<sktext::gpu::TextBlob> blob = sktext::gpu::TextBlob::Make(...);
```

创建 TextBlob 涉及:
- 字形查找和缓存
- 子运行生成
- 内存分配

对于单个测试调用,这些开销可忽略。

### 4. 缓存利用

使用全局字形缓存:
```cpp
SkStrikeCache::GlobalStrikeCache()
```

即使是测试代码,也能受益于字形缓存,避免重复光栅化。

## 相关文件

**头文件**:
- `tools/ganesh/AtlasTextOpTools.h`: 工具类声明

**实现文件**:
- `tools/ganesh/AtlasTextOpTools.cpp`: 工具类实现

**核心依赖**:
- `src/gpu/ganesh/ops/AtlasTextOp.h`: 文本操作实现
- `src/text/gpu/TextBlob.h`: GPU 文本 blob
- `src/text/GlyphRun.h`: 字形运行系统
- `src/gpu/ganesh/SurfaceDrawContext.h`: 绘制上下文

**测试工具**:
- `tools/text/gpu/TextBlobTools.h`: TextBlob 辅助工具
- `src/gpu/ganesh/GrDrawOpTest.h`: 操作测试框架

**测试代码**:
- `tests/AtlasTextOpTest.cpp`: 使用本工具的测试
- `tests/TextBlobTest.cpp`: 文本 blob 测试

**相关操作**:
- `src/gpu/ganesh/ops/AtlasTextOp.cpp`: 实际的文本渲染操作
- `src/gpu/ganesh/ops/GrOp.h`: 操作基类

**GR_DRAW_OP_TEST 宏**:
```cpp
#if defined(GPU_TEST_UTILS)
GR_DRAW_OP_TEST_DEFINE(AtlasTextOp) {
    // 随机测试生成逻辑
    SkMatrix ctm = GrTest::TestMatrixInvertible(random);
    SkPaint skPaint;
    skPaint.setColor(random->nextU());
    SkFont font;
    // ...
    return skgpu::ganesh::AtlasTextOpTools::CreateOp(sdc, skPaint, font, ctm, text, xInt, yInt);
}
#endif
```

该宏注册测试工厂,允许 Skia 的模糊测试框架自动生成随机的 AtlasTextOp 进行测试。
