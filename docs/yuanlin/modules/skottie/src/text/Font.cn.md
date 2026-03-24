# Font

> 源文件
> - `modules/skottie/src/text/Font.h`
> - `modules/skottie/src/text/Font.cpp`

## 概述

`Font` 模块实现了 Skottie 的自定义字体系统,支持基于 Lottie 字符数据（字形路径和字形组合）创建字体。该模块能够解析 Lottie JSON 中的字形定义,包括路径字形和组合字形,并生成可用于文本渲染的 `SkTypeface` 对象。它为 Lottie 动画提供了嵌入式字体支持,使动画文件能够包含自定义字体数据,确保跨平台的视觉一致性。

自定义字体支持两种字形类型:路径字形（基于贝塞尔曲线）和组合字形（基于预合成图层）。组合字形允许字符包含完整的动画场景图,为创意文本效果提供了强大的可能性。

## 架构位置

`Font` 位于 Skottie 文本系统的字体支持层:

```
Skottie 文本系统
├── TextAdapter (文本适配器)
│   └── CustomFont ← 本模块 (自定义字体)
│       ├── Builder (字形解析器)
│       └── GlyphCompMapper (字形映射器)
├── TextShaper (文本塑形)
└── TextRenderer (文本渲染)
```

数据流程:
1. 解析 Lottie JSON 中的字形数据
2. 构建 `SkCustomTypeface`
3. 塑形时使用自定义字体
4. 渲染时解析组合字形

## 主要类与结构体

### CustomFont

自定义字体主类:

```cpp
class CustomFont final : SkNoncopyable {
public:
    ~CustomFont();

    using GlyphCompMap = skia_private::THashMap<SkGlyphID, sk_sp<sksg::RenderNode>>;

    class Builder;           // 字形解析器
    class GlyphCompMapper;   // 字形映射器

    const sk_sp<SkTypeface>& typeface() const { return fTypeface; }
    int glyphCompCount() const { return fGlyphComps.count(); }

private:
    CustomFont(GlyphCompMap&&, sk_sp<SkTypeface> tf);

    const GlyphCompMap fGlyphComps;        // 字形组合映射
    const sk_sp<SkTypeface> fTypeface;     // 自定义字体
};
```

### CustomFont::Builder

字体构建器,负责解析和积累字形:

```cpp
class Builder final : SkNoncopyable {
public:
    bool parseGlyph(const AnimationBuilder*, const skjson::ObjectValue&);
    std::unique_ptr<CustomFont> detach();

private:
    static bool ParseGlyphPath(const AnimationBuilder*,
                               const skjson::ObjectValue&,
                               SkPath*);

    static sk_sp<sksg::RenderNode> ParseGlyphComp(
        const AnimationBuilder*,
        const skjson::ObjectValue&,
        SkSize*);

    GlyphCompMap fGlyphComps;               // 组合字形映射
    SkCustomTypefaceBuilder fCustomBuilder; // 字体构建器
};
```

### CustomFont::GlyphCompMapper

字形组合映射器,用于渲染时查找组合字形:

```cpp
class GlyphCompMapper final : public SkRefCnt {
public:
    explicit GlyphCompMapper(std::vector<std::unique_ptr<CustomFont>>&& fonts);

    ~GlyphCompMapper() override = default;

    sk_sp<sksg::RenderNode> getGlyphComp(const SkTypeface*, SkGlyphID) const;

private:
    const std::vector<std::unique_ptr<CustomFont>> fFonts;
};
```

## 公共 API 函数

### CustomFont::Builder 方法

**parseGlyph**
```cpp
bool parseGlyph(const AnimationBuilder* abuilder,
               const skjson::ObjectValue& jchar);
```
解析单个字形定义:
1. 提取字符编码和宽度
2. 判断是组合字形还是路径字形
3. 为组合字形创建场景图节点
4. 为路径字形解析贝塞尔路径
5. 注册字形到 `SkCustomTypefaceBuilder`

字形 JSON 格式:
```json
{
  "ch": "A",           // 字符
  "w": 32.67,          // 宽度/前进量 (1/100 单位)
  "size": 50,          // 忽略
  "t": 1,              // 组合字形标记
  "data": { ... }      // 字形数据
}
```

**detach**
```cpp
std::unique_ptr<CustomFont> detach();
```
完成字体构建,返回自定义字体实例。清空构建器状态。

**ParseGlyphPath (静态)**
```cpp
static bool ParseGlyphPath(const AnimationBuilder* abuilder,
                          const skjson::ObjectValue& jdata,
                          SkPath* path);
```
解析字形路径数据:
- 遍历形状组
- 提取路径节点
- 合并所有路径
- 验证无动画器

路径数据格式:
```json
{
  "shapes": [
    {
      "ty": "gr",              // 组类型
      "it": [
        {
          "ty": "sh",          // 形状类型
          "ks": <路径数据>      // 静态路径
        }
      ]
    }
  ]
}
```

**ParseGlyphComp (静态)**
```cpp
static sk_sp<sksg::RenderNode> ParseGlyphComp(
    const AnimationBuilder* abuilder,
    const skjson::ObjectValue& jdata,
    SkSize* glyph_size);
```
解析字形组合（预合成字形）:
- 提取入点/出点
- 附加预合成图层
- 应用缩放变换（归一化为 1pt）
- 计算字形边界

组合数据格式:
```json
{
  "ip": <入点>,
  "op": <出点>,
  "refId": <组合ID>,
  "ks": <变换信息>
}
```

### CustomFont::GlyphCompMapper 方法

**getGlyphComp**
```cpp
sk_sp<sksg::RenderNode> getGlyphComp(const SkTypeface* tf,
                                     SkGlyphID gid) const;
```
查找给定字体和字形ID的组合渲染节点。
- 遍历所有自定义字体
- 匹配字体引用
- 查找字形组合映射
- 返回场景图节点或 `nullptr`

## 内部实现细节

### 字符编码处理

使用 Unicode 编码作为字形ID:

```cpp
const auto* ch_ptr = jch->begin();
const auto ch_len = jch->size();
if (SkUTF::CountUTF8(ch_ptr, ch_len) != 1) {
    return false;  // 必须是单个字符
}

const auto uni = SkUTF::NextUTF8(&ch_ptr, ch_ptr + ch_len);
if (!SkTFitsIn<SkGlyphID>(uni)) {
    return false;  // Unicode 码点必须适配 SkGlyphID
}
const auto glyph_id = SkTo<SkGlyphID>(uni);
```

这种设计简化了字形查找,但限制了对超出 BMP 的 Unicode 字符的支持。

### 归一化缩放

所有字形数据归一化为 1pt:

```cpp
static constexpr float kPtScale = 0.01f;
const auto advance = ParseDefault(jchar["w"], 0.0f) * kPtScale;

// 路径字形
path = path.makeTransform(SkMatrix::Scale(kPtScale, kPtScale));

// 组合字形
sk_sp<sksg::Transform> glyph_transform =
    sksg::Matrix<SkMatrix>::Make(SkMatrix::Scale(kPtScale, kPtScale));
```

Lottie 使用 100 单位表示 1pt,需要缩放 0.01 倍。

### 组合字形边界

组合字形使用左下角原点:

```cpp
// TODO: Lottie 可能需要添加原点属性,允许设计师完全控制字形位置
const auto glyph_bounds = SkRect::MakeLTRB(0, -glyph_size.fHeight,
                                            glyph_size.fWidth, 0);
fCustomBuilder.setGlyph(glyph_id, advance, SkPath::Rect(glyph_bounds));
```

负高度用于 Skia 的坐标系统（Y 轴向下）。

### 双重用途设计

组合字形使用 `SkCustomTypeface` 仅用于塑形,不用于渲染:

```cpp
// 塑形: 使用 SkCustomTypeface 提供的边界和前进量
fCustomBuilder.setGlyph(glyph_id, advance, SkPath::Rect(glyph_bounds));

// 渲染: 使用场景图节点
fGlyphComps.set(glyph_id, std::move(comp_node));
```

这种分离允许组合字形包含复杂的动画场景图,超越路径的限制。

### 路径合并

路径字形可能包含多个形状,需要合并:

```cpp
SkPathBuilder builder;
for (const skjson::ObjectValue* jgrp : *jshapes) {
    const skjson::ArrayValue* jit = (*jgrp)["it"];
    for (const skjson::ObjectValue* jshape : *jit) {
        auto path_node = abuilder->attachPath((*jshape)["ks"]);
        builder.addPath(path_node->getPath());
    }
}
*path = builder.detach();
```

### 动画器验证

字形路径必须是静态的:

```cpp
AnimationBuilder::AutoScope ascope(abuilder);
auto path_node = abuilder->attachPath((*jshape)["ks"]);
auto animators = ascope.release();

if (!path_node || !animators.empty()) {
    return false;  // 拒绝动画路径
}
```

虽然 Lottie 使用可动画属性格式编码,但字形路径不应该有动画。

### 空格字形处理

空格字符可能没有路径数据:

```cpp
const skjson::ArrayValue* jshapes = jdata["shapes"];
if (!jshapes) {
    // 空格/空字形
    return true;
}
```

返回空路径但不报错。

### 字形查找优化

`GlyphCompMapper` 使用线性查找:

```cpp
for (const auto& font : fFonts) {
    if (font->typeface().get() == tf) {
        auto* comp_node = font->fGlyphComps.find(gid);
        return comp_node ? *comp_node : nullptr;
    }
}
```

对于少量字体,线性查找足够高效。哈希查找用于字形ID映射。

## 依赖关系

### 对外依赖

- **SkCustomTypeface**: 自定义字体构建器
- **SkTypeface**: Skia 字体抽象
- **SkPath**: 路径表示
- **sksg::RenderNode**: 场景图渲染节点
- **sksg::Transform**: 变换节点
- **AnimationBuilder**: 动画构建器,提供场景图附加功能
- **SkTHash**: 哈希表,用于字形映射

### 内部依赖

- **SkottieJson**: JSON 解析工具 `Parse`、`ParseDefault`
- **SkottiePriv**: 私有工具函数,如 `LayerInfo`
- **SkUTF**: UTF-8 编码解析
- **SkTo**: 类型转换函数

### 被依赖情况

- **TextAdapter**: 使用自定义字体进行文本塑形和渲染
- **AnimationBuilder**: 在解析字体列表时创建自定义字体
- **TextShaper**: 通过 `SkTypeface` 间接使用

## 设计模式与设计决策

### 构建器模式

`CustomFont::Builder` 使用构建器模式积累字形:

```cpp
Builder builder;
builder.parseGlyph(...);
builder.parseGlyph(...);
auto font = builder.detach();
```

分离字形解析和字体创建,支持增量构建。

### 工厂方法

静态方法 `ParseGlyphPath` 和 `ParseGlyphComp` 作为工厂方法创建不同类型的字形:

```cpp
if (auto comp_node = ParseGlyphComp(...)) {
    // 组合字形
} else if (ParseGlyphPath(...)) {
    // 路径字形
}
```

### 不可复制设计

`CustomFont` 和 `Builder` 禁止复制:

```cpp
class CustomFont final : SkNoncopyable { ... };
class Builder final : SkNoncopyable { ... };
```

确保资源的唯一所有权。

### 类型擦除

`GlyphCompMapper` 存储不透明的 `std::unique_ptr<CustomFont>`:

```cpp
const std::vector<std::unique_ptr<CustomFont>> fFonts;
```

避免暴露实现细节,支持多态。

### 延迟查找

组合字形在渲染时才查找,而不是塑形时:

```cpp
sk_sp<sksg::RenderNode> getGlyphComp(const SkTypeface*, SkGlyphID) const;
```

允许塑形使用标准 Skia API,渲染时替换为场景图节点。

## 性能考量

### 归一化预计算

所有字形在构建时归一化,避免运行时缩放:

```cpp
path = path.makeTransform(SkMatrix::Scale(kPtScale, kPtScale));
```

### 哈希表查找

字形组合使用哈希表存储:

```cpp
using GlyphCompMap = skia_private::THashMap<SkGlyphID, sk_sp<sksg::RenderNode>>;
```

O(1) 平均查找时间。

### 引用计数

使用智能指针管理生命周期:

```cpp
const sk_sp<SkTypeface> fTypeface;
sk_sp<sksg::RenderNode> comp_node;
```

避免不必要的复制和手动内存管理。

### 早期验证

在构建时验证字形数据,避免运行时错误:

```cpp
if (SkUTF::CountUTF8(ch_ptr, ch_len) != 1) {
    return false;
}
if (!animators.empty()) {
    return false;
}
```

### 路径预合并

构建时合并所有形状路径:

```cpp
builder.addPath(path_node->getPath());
```

避免运行时合并开销。

## 相关文件

**头文件依赖**:
- `include/core/SkTypeface.h` - Skia 字体抽象
- `include/utils/SkCustomTypeface.h` - 自定义字体构建
- `include/core/SkRefCnt.h` - 引用计数
- `modules/sksg/include/SkSGRenderNode.h` - 场景图节点
- `src/core/SkTHash.h` - 哈希表

**实现文件依赖**:
- `include/core/SkPath.h` - 路径类型
- `include/core/SkPathBuilder.h` - 路径构建器
- `modules/skottie/src/SkottieJson.h` - JSON 解析
- `modules/skottie/src/SkottiePriv.h` - 私有工具
- `modules/sksg/include/SkSGPath.h` - 路径节点
- `modules/sksg/include/SkSGTransform.h` - 变换节点
- `src/base/SkUTF.h` - UTF-8 编码

**相关模块**:
- `modules/skottie/src/text/TextAdapter.h` - 文本适配器
- `modules/skottie/include/TextShaper.h` - 文本塑形
- `modules/skottie/src/SkottiePriv.h` - 动画构建器
