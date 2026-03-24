# SkSGMaskEffect

> 源文件: modules/sksg/include/SkSGMaskEffect.h

## 概述

SkSGMaskEffect 是 Skia 场景图中的效果节点，用于对渲染节点应用遮罩（mask）效果。它通过另一个渲染节点作为遮罩源，控制目标节点的可见性和透明度。支持 Alpha 通道和亮度（Luma）两种遮罩模式，以及正常和反转两种极性。

遮罩效果是图形合成中的基础技术，广泛应用于图像编辑、动画和特效中。MaskEffect 使得场景图能够实现复杂的视觉合成，如渐变遮罩、形状遮罩、文字镂空等效果。

## 架构位置

在 Skia 场景图架构中的位置：

- **继承关系**: MaskEffect → EffectNode → RenderNode → Node
- **功能定位**: 合成效果节点，控制子节点的可见性
- **输入**: 一个子节点（被遮罩内容）+ 一个遮罩节点
- **输出**: 遮罩后的渲染结果
- **模块位置**: modules/sksg 效果系统

MaskEffect 是场景图效果系统的重要组成部分，与 OpacityEffect、ClipEffect 等并列，提供不同的视觉效果能力。

## 主要类与结构体

### MaskEffect 类

```cpp
class MaskEffect final : public EffectNode {
public:
    enum class Mode : uint32_t {
        kAlphaNormal,  // 使用遮罩的 Alpha 通道（正常）
        kAlphaInvert,  // 使用遮罩的 Alpha 通道（反转）
        kLumaNormal,   // 使用遮罩的亮度（正常）
        kLumaInvert,   // 使用遮罩的亮度（反转）
    };

    static sk_sp<MaskEffect> Make(sk_sp<RenderNode> child,
                                  sk_sp<RenderNode> mask,
                                  Mode mode = Mode::kAlphaNormal);
    ~MaskEffect() override;

protected:
    MaskEffect(sk_sp<RenderNode>, sk_sp<RenderNode> mask, Mode);

    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    const sk_sp<RenderNode> fMaskNode;
    const Mode              fMaskMode;

    using INHERITED = EffectNode;
};
```

### Mode 枚举

**kAlphaNormal**: 使用遮罩图像的 Alpha 通道控制透明度。Alpha=1 完全可见，Alpha=0 完全透明。

**kAlphaInvert**: 反转 Alpha 遮罩。Alpha=0 完全可见，Alpha=1 完全透明。

**kLumaNormal**: 使用遮罩图像的亮度控制透明度。白色（亮度=1）完全可见，黑色（亮度=0）完全透明。

**kLumaInvert**: 反转亮度遮罩。黑色完全可见，白色完全透明。

## 公共 API 函数

### Make()
```cpp
static sk_sp<MaskEffect> Make(sk_sp<RenderNode> child,
                              sk_sp<RenderNode> mask,
                              Mode mode = Mode::kAlphaNormal);
```
创建遮罩效果节点。

**参数**:
- `child`: 被遮罩的子节点（内容）
- `mask`: 遮罩节点（提供遮罩形状/图像）
- `mode`: 遮罩模式，默认 Alpha 正常模式

**返回**: 智能指针，如果 child 或 mask 为空则返回 nullptr

**使用示例**:
```cpp
auto content = sksg::Image::Make(photo);
auto maskShape = sksg::Draw::Make(circle, paint);
auto masked = sksg::MaskEffect::Make(content, maskShape,
                                     MaskEffect::Mode::kAlphaNormal);
```

## 内部实现细节

### 渲染实现 (onRender)

遮罩渲染的典型流程：
1. 创建离屏表面（saveLayer）用于子节点渲染
2. 渲染子节点到离屏表面
3. 创建另一个离屏表面用于遮罩节点
4. 渲染遮罩节点
5. 根据 Mode 应用遮罩：
   - Alpha 模式：使用混合模式（如 kDstIn）
   - Luma 模式：转换为灰度后应用
   - Invert 模式：反转遮罩值
6. 合成最终结果到画布

### 边界计算 (onRevalidate)

重验证逻辑：
1. 重验证子节点，获取子节点边界
2. 重验证遮罩节点，获取遮罩边界
3. 计算两者的交集作为有效区域
   - Alpha Normal: 结果边界 ≤ min(child, mask)
   - Invert 模式可能扩展边界
4. 返回计算的边界

**观察者关系**:
- MaskEffect 观察 child 和 fMaskNode
- 任一节点失效触发 MaskEffect 重验证

### 命中测试 (onNodeAt)

命中测试需考虑遮罩：
1. 检查点是否在子节点边界内
2. 采样遮罩节点在该点的值
3. 根据 Mode 判断该点是否可见：
   - 如果遮罩值使该点透明，返回 nullptr
   - 否则委托给子节点的 nodeAt()

### 构造函数

受保护的构造函数：
- 初始化 EffectNode（传递 child）
- 存储 fMaskNode 和 fMaskMode
- 建立对 fMaskNode 的观察（observeInval）

## 依赖关系

### 核心依赖
- **include/core/SkRect.h**: 边界框
- **include/core/SkRefCnt.h**: 引用计数
- **modules/sksg/include/SkSGEffectNode.h**: 效果节点基类
- **modules/sksg/include/SkSGRenderNode.h**: 渲染节点

### 渲染依赖
- **SkCanvas**: 画布，saveLayer 等 API
- **SkMatrix**: 变换矩阵
- **SkPoint**: 点坐标
- **SkBlendMode**: 混合模式（用于遮罩合成）

### 场景图依赖
- **InvalidationController**: 失效管理

### 标准库
- **<cstdint>**: uint32_t（Mode 底层类型）
- **<utility>**: std::move

## 设计模式与设计决策

### 1. 终态类设计
MaskEffect 声明为 final：
- 遮罩逻辑相对固定
- 不需要进一步特化
- 简化虚函数调度

### 2. 不可变遮罩和模式
fMaskNode 和 fMaskMode 声明为 const：
- 构造后不可修改
- 简化失效追踪
- 需要不同遮罩时创建新节点

### 3. 空检查保护
Make() 检查参数有效性：
- 防止空指针异常
- 返回 nullptr 允许调用者处理
- 符合防御性编程原则

### 4. 默认 Alpha 模式
默认使用 kAlphaNormal：
- 最常见的遮罩模式
- 符合大多数用户预期
- 简化 API 调用

### 5. 模式枚举设计
使用强类型枚举类（enum class）：
- 类型安全
- 避免命名冲突
- 明确底层类型（uint32_t）

## 性能考量

### 1. 离屏渲染开销
遮罩效果需要多个 saveLayer：
- 分配离屏表面（纹理/位图）
- 额外的绘制通道
- 最终合成操作
- 是最昂贵的效果之一

### 2. 遮罩节点渲染
遮罩节点每帧都需要渲染：
- 即使内容未改变
- 可考虑缓存遮罩结果（实现复杂）
- 简单遮罩（纯色形状）相对便宜

### 3. 边界计算优化
精确边界计算可减少离屏表面大小：
- 更小的表面意味着更少内存和带宽
- 交集计算避免浪费

### 4. Luma 模式额外开销
亮度模式需要颜色空间转换：
- 比 Alpha 模式慢
- 涉及加权颜色通道计算
- 选择合适模式优化性能

### 5. 命中测试成本
精确命中测试需要采样遮罩：
- 可能需要光栅化遮罩
- 对于频繁交互场景影响明显
- 可使用边界框快速拒绝优化

### 6. 缓存策略
可能的优化方向：
- 缓存静态遮罩的渲染结果
- 检测简单遮罩形状使用硬件加速路径
- 对于动画遮罩，预计算关键帧

## 相关文件

### 头文件
- **modules/sksg/include/SkSGEffectNode.h**: EffectNode 基类
- **modules/sksg/include/SkSGRenderNode.h**: RenderNode 定义
- **include/core/SkBlendMode.h**: 混合模式

### 实现文件
- **modules/sksg/src/SkSGMaskEffect.cpp**: MaskEffect 实现

### 相关效果节点
- **SkSGOpacityEffect.h**: 透明度效果
- **SkSGClipEffect.h**: 裁剪效果（硬边遮罩）
- **SkSGRenderEffect.h**: 其他渲染效果

### 使用场景
- **modules/skottie**: Lottie 动画中的遮罩层
- 图像编辑中的选区和遮罩
- 视频特效中的转场效果
- UI 中的渐变消失效果

### 示例用法
```cpp
// 圆形遮罩头像
auto avatar = sksg::Image::Make(userPhoto);
auto circle = sksg::Circle::Make(center, radius);
auto circlePaint = sksg::Color::Make(SK_ColorWHITE);
auto circleDraw = sksg::Draw::Make(circle, circlePaint);
auto maskedAvatar = sksg::MaskEffect::Make(avatar, circleDraw);

// 文字镂空效果（反转遮罩）
auto background = sksg::Image::Make(texture);
auto text = createTextNode("HELLO");
auto cutout = sksg::MaskEffect::Make(background, text,
                                     MaskEffect::Mode::kAlphaInvert);
```
