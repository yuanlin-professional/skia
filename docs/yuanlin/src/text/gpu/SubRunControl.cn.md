# SubRunControl

> 源文件
> - src/text/gpu/SubRunControl.h
> - src/text/gpu/SubRunControl.cpp

## 概述

`SubRunControl` 是 Skia GPU 文本渲染系统的策略控制类，负责决定文本应该使用何种渲染技术：直接图集渲染（Direct）、有符号距离场文本（SDFT）还是路径渲染。它根据文本大小、变换矩阵和绘制参数智能选择最优的渲染策略，并管理 SDFT 的缩放范围和字体配置。

## 架构位置

该组件位于 GPU 文本渲染系统的策略层（`src/text/gpu/`），在文本输入和具体渲染实现之间起桥接作用：

```
GlyphRunList (输入)
   ↓
SubRunControl (策略决策)
   ↓
   ├─→ Direct Rendering (小字体，无变换)
   ├─→ SDFT Rendering (中大字体，有缩放)
   └─→ Path Rendering (超大字体，路径描边)
```

## 主要类与结构体

### SubRunControl 类

渲染策略控制器，根据文本参数决定渲染方式。

**成员变量（启用 SDFT 时）：**
- `fMinDistanceFieldFontSize`: `SkScalar` - 最小 SDFT 字体大小（设备空间）
- `fMaxDistanceFieldFontSize`: `SkScalar` - 最大 SDFT 字体大小（设备空间）
- `fAbleToUseSDFT`: `bool` - 是否支持使用 SDFT
- `fAbleToUsePerspectiveSDFT`: `bool` - 是否支持透视下的 SDFT
- `fForcePathAA`: `bool` - 是否强制路径渲染使用抗锯齿

### SDFTMatrixRange 类

SDFT 矩阵缩放范围，定义可重用 SDFT 字形的矩阵范围。

**成员变量：**
- `fMatrixMin`: `SkScalar` - 最小矩阵缩放因子
- `fMatrixMax`: `SkScalar` - 最大矩阵缩放因子

**方法：**
- `matrixInRange(const SkMatrix&)` - 检查矩阵是否在范围内
- `flatten()` / `MakeFromBuffer()` - 序列化支持

## 公共 API 函数

### 构造函数
```cpp
SubRunControl(bool ableToUseSDFT,
              bool useSDFTForSmallText,
              bool useSDFTForPerspectiveText,
              SkScalar min, SkScalar max,
              bool forcePathAA=false)
```
完整参数构造（SDFT 启用时）。

```cpp
explicit SubRunControl(bool forcePathAA = false)
```
简化构造（SDFT 禁用时）。

### 渲染策略判断
```cpp
bool isDirect(SkScalar approximateDeviceTextSize,
              const SkPaint& paint,
              const SkMatrix& matrix) const
```
判断是否使用直接图集渲染。

**条件：**
- 不是 SDFT
- 无透视变换
- 字体大小在 0 到 `kSkSideTooBigForAtlas` 之间

```cpp
bool isSDFT(SkScalar approximateDeviceTextSize,
            const SkPaint& paint,
            const SkMatrix& matrix) const
```
判断是否使用有符号距离场文本。

**条件：**
- 支持 SDFT
- 无遮罩滤镜
- 填充模式或宽描边模式
- 字体大小在 SDFT 范围内
- 无透视或支持透视 SDFT

### SDFT 字体配置
```cpp
std::tuple<SkFont, SkScalar, SDFTMatrixRange>
getSDFFont(const SkFont& font,
           const SkMatrix& viewMatrix,
           const SkPoint& textLocation) const
```
根据原始字体和视图矩阵生成 SDFT 字体配置。

**返回值：**
1. `SkFont` - 配置好的 SDFT 字体
2. `SkScalar` - 从源空间到掩码空间的缩放因子
3. `SDFTMatrixRange` - 可重用的矩阵范围

### 其他接口
```cpp
bool forcePathAA() const              // 是否强制路径抗锯齿
SkScalar maxSize() const              // 最大 SDFT 字体大小
```

## 内部实现细节

### SDFT 尺寸分级策略

Skia 使用分级的 SDFT 掩码大小以平衡质量和性能：

**尺寸阈值常量：**
```cpp
kSmallDFFontLimit = 32       // 小号 SDFT 上限
kMediumDFFontLimit = 72      // 中号 SDFT 上限
kLargeDFFontLimit = 162      // 大号 SDFT 上限（通用）
kExtraLargeDFFontLimit = 256 // 超大号 SDFT 上限（仅 macOS）
```

**分级逻辑（getSDFFont）：**
```cpp
if (scaledTextSize <= 32) {
    dfMaskSize = 32;
    range = [min, 32];
} else if (scaledTextSize <= 72) {
    dfMaskSize = 72;
    range = [32, 72];
} else if (scaledTextSize <= 162) {
    dfMaskSize = 162;
    range = [72, max];
}
// macOS 额外支持 256 号掩码
```

**为什么分级？**
- 小字体使用小掩码节省内存
- 大字体使用大掩码保证质量
- 每个分级有重用范围，提高缓存命中率

### SDFT 字体配置流程

**1. 计算缩放文本大小**
```cpp
SkScalar scaledTextSize = SkFontPriv::ApproximateTransformedTextSize(
    font, viewMatrix, textLoc);
```

**2. 选择掩码大小**
根据分级阈值确定 `dfMaskSize` 和有效矩阵范围。

**3. 配置字体属性**
```cpp
dfFont.setSize(dfMaskSize);           // 设置掩码大小
dfFont.setForceAutoHinting(false);    // 禁用自动提示
dfFont.setHinting(SkFontHinting::kNormal);  // 正常提示
dfFont.setSubpixel(false);            // 禁用次像素定位
dfFont.setEdging(SkFont::Edging::kAntiAlias);  // 抗锯齿模式
```

**为什么禁用次像素和 LCD？**
SDFT 在变换到屏幕时自然处理次像素定位，因此在创建掩码时禁用以简化处理。

**4. 计算缩放因子和矩阵范围**
```cpp
SkScalar textScale = textSize / dfMaskSize;  // 源空间到掩码空间的缩放
SkScalar minMatrixScale = dfMaskScaleFloor / textSize;
SkScalar maxMatrixScale = dfMaskScaleCeil / textSize;
```

### 直接渲染判断逻辑

```cpp
bool isDirect = !isSDFT &&              // 不使用 SDFT
                !matrix.hasPerspective() &&  // 无透视
                0 < size < kSkSideTooBigForAtlas;  // 大小适合图集
```

直接渲染适合小字体且无复杂变换的场景，将字形直接光栅化到图集。

### SDFT 渲染判断逻辑

```cpp
bool isSDFT = fAbleToUseSDFT &&         // 支持 SDFT
              !hasMaskFilter &&          // 无遮罩滤镜
              (fill || wideStroke) &&    // 填充或宽描边
              0 < size &&                 // 有效大小
              (perspectiveOK || !hasPerspective) &&  // 透视检查
              (min <= size || hasPerspective) &&     // 最小尺寸
              size <= max;                // 最大尺寸
```

**特殊透视处理：**
透视变换下，即使小于最小阈值也可能使用 SDFT，因为透视会放大文本。

### 最小 SDFT 范围计算

```cpp
SkScalar MinSDFTRange(bool useSDFTForSmallText, SkScalar min) {
    if (!useSDFTForSmallText) {
        return kLargeDFFontLimit;  // 仅对大字体使用 SDFT
    }
    return min;  // 小字体也使用 SDFT
}
```

`useSDFTForSmallText` 标志控制是否对小字体启用 SDFT。

## 依赖关系

**直接依赖：**
- `include/core/SkFont.h` - 字体类
- `include/core/SkMatrix.h` - 变换矩阵
- `include/core/SkPaint.h` - 绘制参数
- `src/core/SkFontPriv.h` - 字体私有工具
- `src/core/SkGlyph.h` - 字形定义

**使用场景：**
- `SubRunContainer` - 决定子运行类型
- `TextBlob::Make` - 创建文本块时选择策略
- GPU 文本渲染管道

## 设计模式与设计决策

### 策略模式
`SubRunControl` 充当策略选择器，根据上下文决定使用哪种渲染技术。

### 平台差异化
macOS 支持额外的超大号 SDFT（256），其他平台最大到 162，体现了平台特定的优化。

### 编译时特性开关
通过 `SK_DISABLE_SDF_TEXT` 宏在编译时完全禁用 SDFT 功能，减少代码体积。

### 不可变配置
构造后所有策略参数不可修改，保证线程安全和决策一致性。

### 范围重用设计
`SDFTMatrixRange` 允许在一定矩阵范围内重用相同的 SDFT 掩码，提高缓存效率。

## 性能考量

### SDFT 的优势
1. **尺寸无关**：一个掩码可以渲染多种大小
2. **变换友好**：支持缩放和轻微旋转
3. **内存效率**：相比直接渲染大字体更节省图集空间
4. **质量稳定**：在缩放下保持平滑的边缘

### 直接渲染的优势
1. **速度快**：无需距离场计算
2. **精确**：像素级精确渲染
3. **简单**：着色器逻辑简单

### 路径渲染的场景
超大字体（> 162 或 256）使用路径渲染：
- 字形作为独立路径绘制
- 支持任意大小
- 避免图集内存爆炸

### 分级策略的权衡
- **小掩码**：节省内存，但质量有限
- **大掩码**：质量好，但占用更多图集空间
- **分级**：在质量和内存间取得平衡

### 时间复杂度
所有判断函数都是 O(1) 的简单条件检查。

### 空间复杂度
仅存储几个配置标志和阈值，空间开销极小。

## 相关文件

**核心依赖：**
- `include/core/SkFont.h` - 字体接口
- `include/core/SkMatrix.h` - 矩阵运算
- `src/core/SkGlyph.h` - 字形定义

**使用此类的模块：**
- `src/text/gpu/SubRunContainer.cpp` - 子运行创建
- `src/text/gpu/TextBlob.cpp` - 文本块实现
- `src/gpu/ganesh/text/GrSDFTControl.cpp` - SDFT 控制

**相关配置：**
- 编译标志 `SK_DISABLE_SDF_TEXT` 控制 SDFT 特性
- 平台标志 `SK_BUILD_FOR_MAC` 控制超大号 SDFT
