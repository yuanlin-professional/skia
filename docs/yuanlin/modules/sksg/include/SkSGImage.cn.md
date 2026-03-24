# SkSGImage

> 源文件: modules/sksg/include/SkSGImage.h

## 概述

SkSGImage 是 Skia 场景图（Scene Graph）系统中的具体渲染节点，用于在场景图中显示位图图像。该模块封装了 SkImage 对象，并提供采样选项、抗锯齿等图像渲染控制能力。

Image 类继承自 RenderNode，负责将 Skia 的位图图像集成到场景图的渲染流程中。它支持动态更改图像内容、采样方式和抗锯齿设置，并参与场景图的失效和重验证机制。

## 架构位置

在 Skia 场景图架构中的位置：

- **继承层次**: Image → RenderNode → Node
- **模块归属**: modules/sksg，场景图系统的一部分
- **功能定位**: 具体渲染节点，负责图像内容的显示
- **协作关系**:
  - 可作为 Group 的子节点进行组合
  - 可被 Effect 节点包装以应用效果
  - 参与场景图的统一渲染流程

RenderNode 提供了通用的渲染能力和上下文管理，Image 在此基础上专注于图像的绘制逻辑。

## 主要类与结构体

### Image 类

```cpp
class Image final : public RenderNode {
public:
    static sk_sp<Image> Make(sk_sp<SkImage> image);

    SG_ATTRIBUTE(Image, sk_sp<SkImage>, fImage)
    SG_ATTRIBUTE(SamplingOptions, SkSamplingOptions, fSamplingOptions)
    SG_ATTRIBUTE(AntiAlias, bool, fAntiAlias)

protected:
    explicit Image(sk_sp<SkImage>);

    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    SkSamplingOptions fSamplingOptions;
    sk_sp<SkImage>    fImage;
    bool              fAntiAlias = true;

    using INHERITED = RenderNode;
};
```

**关键成员**:
- `fImage`: 持有的 SkImage 智能指针，表示实际的位图数据
- `fSamplingOptions`: 采样选项，控制图像缩放时的质量
- `fAntiAlias`: 抗锯齿标志（默认启用）

## 公共 API 函数

### 静态工厂方法

```cpp
static sk_sp<Image> Make(sk_sp<SkImage> image)
```
创建 Image 节点的唯一公共方式。参数 `image` 为要显示的 Skia 图像对象。返回智能指针管理的 Image 节点。

**使用示例**:
```cpp
auto skImage = SkImage::MakeFromBitmap(bitmap);
auto imageNode = sksg::Image::Make(std::move(skImage));
```

### 属性访问器

通过 SG_ATTRIBUTE 宏生成的访问器：

#### getImage() / setImage()
```cpp
const sk_sp<SkImage>& getImage() const;
void setImage(const sk_sp<SkImage>& v);
void setImage(sk_sp<SkImage>&& v);
```
获取或设置显示的图像。更改图像会自动触发节点失效，导致重新渲染。

#### getSamplingOptions() / setSamplingOptions()
```cpp
const SkSamplingOptions& getSamplingOptions() const;
void setSamplingOptions(const SkSamplingOptions& v);
void setSamplingOptions(SkSamplingOptions&& v);
```
控制图像采样方式。SkSamplingOptions 包含过滤模式（最近邻、线性、立方等）和 MipMap 选项，影响图像缩放的质量和性能。

#### getAntiAlias() / setAntiAlias()
```cpp
bool getAntiAlias() const;
void setAntiAlias(bool v);
```
控制图像边缘的抗锯齿。默认启用，可提升视觉质量但可能略微影响性能。

## 内部实现细节

### 渲染实现 (onRender)

`onRender()` 方法负责将图像绘制到画布：
- 接收 SkCanvas 和 RenderContext 参数
- RenderContext 可能包含变换矩阵、裁剪区域等上下文信息
- 使用 SkCanvas 的图像绘制 API，应用 fSamplingOptions 和抗锯齿设置
- 通常将图像绘制到其原始尺寸的矩形区域

### 命中测试 (onNodeAt)

`onNodeAt()` 方法实现点击检测：
- 接收屏幕坐标点
- 判断该点是否位于图像的边界框内
- 返回自身指针（如果命中）或 nullptr
- 用于交互场景中的节点选择

### 重验证 (onRevalidate)

`onRevalidate()` 方法计算节点边界：
- 接收 InvalidationController 和当前变换矩阵
- 根据 SkImage 的尺寸计算本地坐标系的边界框
- 应用变换矩阵得到父坐标系的边界
- 返回的 SkRect 用于裁剪优化和失效区域计算
- 如果图像为空，通常返回空矩形

### 构造函数

构造函数为 explicit 和 private：
- 防止隐式类型转换
- 强制使用 Make() 工厂方法
- 初始化成员变量（fAntiAlias 默认为 true）

## 依赖关系

### 外部依赖
- **include/core/SkImage.h**: Skia 图像类
- **include/core/SkRect.h**: 矩形定义
- **include/core/SkRefCnt.h**: 引用计数
- **include/core/SkSamplingOptions.h**: 采样选项结构

### 场景图依赖
- **modules/sksg/include/SkSGNode.h**: 节点基类
- **modules/sksg/include/SkSGRenderNode.h**: 渲染节点基类
- **sksg::InvalidationController**: 失效控制器

### 渲染依赖
- **SkCanvas**: Skia 画布，用于实际绘制
- **SkMatrix**: 变换矩阵
- **SkPoint**: 点坐标

### 标准库依赖
- **<utility>**: std::move 等工具

## 设计模式与设计决策

### 1. 终态类设计
Image 类声明为 final，不可被继承。这是合理的设计决策，因为：
- 图像渲染逻辑相对固定，无需进一步特化
- 简化虚函数调用开销
- 明确类的使用意图

### 2. 值语义的采样选项
fSamplingOptions 直接存储为值类型而非指针，因为：
- SkSamplingOptions 是轻量级结构体
- 避免额外的堆分配和间接访问
- 简化内存管理

### 3. 默认启用抗锯齿
fAntiAlias 默认为 true，体现了质量优先的设计哲学。对于大多数 UI 和动画场景，抗锯齿带来的视觉提升超过性能开销。

### 4. 智能指针管理图像
使用 sk_sp<SkImage> 而非原始指针：
- 自动管理图像生命周期
- 支持图像在多个节点间共享
- 防止内存泄漏

### 5. 工厂方法封装
Make() 方法接受右值引用（std::move），鼓励移动语义，减少引用计数操作。

## 性能考量

### 1. 采样选项的影响
不同的 SkSamplingOptions 设置对性能影响显著：
- 最近邻（Nearest）：最快，适合像素艺术
- 线性（Linear）：中等，适合一般缩放
- 立方/Mitchell：最慢但质量最高，适合高质量缩放
- MipMap：预计算多级纹理，加速重复缩放

### 2. 图像共享
多个 Image 节点可以共享同一个 SkImage 实例，通过引用计数实现。这对于显示相同内容的多个实例非常高效。

### 3. 抗锯齿开销
启用抗锯齿会增加渲染成本，但在现代硬件上通常可接受。对于性能敏感的场景，可以禁用。

### 4. 边界计算缓存
重验证后的边界框被缓存在 Node 基类中，避免重复计算。只有在节点失效时才重新计算。

### 5. 图像解码延迟
SkImage 可能采用延迟解码策略。首次渲染时可能触发解码，后续渲染可使用缓存的像素数据。

## 相关文件

### 头文件
- **modules/sksg/include/SkSGRenderNode.h**: RenderNode 基类定义
- **modules/sksg/include/SkSGNode.h**: Node 基类和宏定义
- **include/core/SkImage.h**: Skia 图像 API

### 实现文件
- **modules/sksg/src/SkSGImage.cpp**: Image 类的实现

### 相关节点
- **SkSGGroup.h**: 可包含 Image 作为子节点
- **SkSGTransform.h**: 对 Image 应用变换
- **SkSGClipEffect.h**: 裁剪 Image
- **SkSGOpacityEffect.h**: 控制 Image 透明度

### 使用场景
- **modules/skottie**: Lottie 动画中的图像层
- 2D 游戏中的精灵渲染
- UI 系统中的图标和背景图
