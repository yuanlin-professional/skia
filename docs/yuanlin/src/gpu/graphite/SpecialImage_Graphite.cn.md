# SpecialImage_Graphite

> 源文件: src/gpu/graphite/SpecialImage_Graphite.h, src/gpu/graphite/SpecialImage_Graphite.cpp

## 概述

`SpecialImage_Graphite` 是 Skia Graphite 渲染架构中 `SkSpecialImage` 的 GPU 后端实现。`SkSpecialImage` 是 Skia 图像滤镜系统中的核心概念，用于表示滤镜处理过程中的中间图像结果。在 Graphite 中，该类通过包装 `SkImage` 来表示 GPU 支持的特殊图像。

该类的主要作用是为图像滤镜提供高效的 GPU 纹理表示，并支持子区域裁剪操作。它是连接 Skia 核心图像滤镜系统和 Graphite GPU 后端的桥梁。

## 架构位置

```
Skia 图像滤镜架构：
  ├── SkSpecialImage（抽象基类）
  │   ├── SpecialImage_Graphite（Graphite 实现）★
  │   ├── SpecialImage_Ganesh（Ganesh 实现）
  │   └── SpecialImage_Raster（光栅实现）
  ├── SkImageFilter（滤镜基类）
  └── FilterResult（滤镜结果容器）
```

## 主要类与结构体

### SpecialImage 类

```cpp
class SpecialImage final : public SkSpecialImage {
public:
    SpecialImage(const SkIRect& subset,
                sk_sp<SkImage> image,
                const SkSurfaceProps& props);

    size_t getSize() const override;
    bool isGraphiteBacked() const override;
    SkISize backingStoreDimensions() const override;
    sk_sp<SkSpecialImage> onMakeBackingStoreSubset(const SkIRect&) const override;
    sk_sp<SkImage> asImage() const override;

private:
    sk_sp<SkImage> fImage;  // 包装的 Graphite 图像
};
```

### 工厂函数

```cpp
namespace SkSpecialImages {
    sk_sp<SkSpecialImage> MakeGraphite(
        skgpu::graphite::Recorder* recorder,
        const SkIRect& subset,
        sk_sp<SkImage> image,
        const SkSurfaceProps& props);
}
```

## 公共 API 函数

### MakeGraphite 工厂函数

```cpp
sk_sp<SkSpecialImage> MakeGraphite(
    Recorder* recorder,
    const SkIRect& subset,
    sk_sp<SkImage> image,
    const SkSurfaceProps& props);
```

**功能**: 创建 Graphite 支持的特殊图像。

**参数说明**:
- `recorder`: 命令录制器（可为 null，如果图像已经是 Graphite 支持的）
- `subset`: 图像的子区域矩形
- `image`: 源图像（可以是任何后端）
- `props`: Surface 属性配置

**工作流程**:
1. 验证输入参数（图像非空，子区域非空）
2. 检查图像是否已经是 Graphite 后端
3. 如果不是，使用 `GetGraphiteBacked()` 转换为 Graphite 图像
4. 创建并返回 `SpecialImage` 实例

**特殊情况**: Recorder 可为 null，当包装已经是 Graphite 后端的图像时（例如从不可变设备快照时）。

### 成员方法

#### getSize

```cpp
size_t getSize() const override;
```
返回图像的 GPU 纹理大小（字节）。

#### isGraphiteBacked

```cpp
bool isGraphiteBacked() const override;
```
始终返回 `true`，表示该图像由 Graphite 后端支持。

#### backingStoreDimensions

```cpp
SkISize backingStoreDimensions() const override;
```
返回底层纹理的完整尺寸（可能大于 subset）。

#### onMakeBackingStoreSubset

```cpp
sk_sp<SkSpecialImage> onMakeBackingStoreSubset(const SkIRect& subset) const override;
```
创建当前图像的子区域视图，共享同一纹理。

#### asImage

```cpp
sk_sp<SkImage> asImage() const override;
```
返回包装的 `SkImage` 对象，可用于渲染或进一步处理。

## 内部实现细节

### 构造函数实现

```cpp
SpecialImage::SpecialImage(const SkIRect& subset,
                          sk_sp<SkImage> image,
                          const SkSurfaceProps& props)
    : SkSpecialImage(subset, image->uniqueID(),
                    image->imageInfo().colorInfo(), props)
    , fImage(std::move(image)) {
    SkASSERT(as_IB(fImage)->isGraphiteBacked());
}
```

**关键点**:
- 调用基类构造函数，传递 subset、uniqueID 和颜色信息
- 移动语义转移图像所有权
- 断言确保图像确实是 Graphite 后端

### 子区域创建逻辑

```cpp
sk_sp<SkSpecialImage> onMakeBackingStoreSubset(const SkIRect& subset) const override {
    SkASSERT(fImage->bounds().contains(subset));
    return sk_make_sp<SpecialImage>(subset, fImage, this->props());
}
```

**零拷贝设计**: 子区域图像与原图像共享同一纹理，仅更新 subset 矩形。

### 图像转换逻辑

```cpp
if (!as_IB(image)->isGraphiteBacked()) {
    if (!recorder) {
        return nullptr;  // 无法转换
    }
    auto [graphiteImage, _] = GetGraphiteBacked(recorder, image.get(), {});
    if (!graphiteImage) {
        return nullptr;  // 转换失败
    }
    image = graphiteImage;
}
```

**转换策略**:
1. 检查图像后端类型
2. 如果需要转换，使用 `GetGraphiteBacked()` 上传到 GPU
3. 如果没有 Recorder 或转换失败，返回 null

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `SkSpecialImage` | 抽象基类 |
| `SkImage` | 图像数据容器 |
| `Recorder` | 命令录制器 |
| `Image_Graphite` | Graphite 图像实现 |
| `TextureUtils` | 图像转换辅助函数 |

### 外部依赖

| 依赖 | 用途 |
|------|------|
| Skia Core | 图像和颜色类型定义 |
| `SkSurfaceProps` | Surface 属性配置 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `Device` | 创建滤镜中间结果 |
| `SkImageFilter` | 滤镜处理过程中使用 |
| `FilterResult` | 封装滤镜结果 |

## 设计模式与设计决策

### 包装器模式

`SpecialImage` 包装 `SkImage`，为滤镜系统提供统一接口：
- 隐藏 GPU 纹理细节
- 提供子区域裁剪能力
- 支持零拷贝的子图像创建

### 工厂方法

使用独立的 `MakeGraphite()` 函数而非构造函数：
- 封装复杂的图像转换逻辑
- 支持失败情况（返回 null）
- 允许在不同命名空间中定义工厂函数

### 延迟计算

- Subset 仅记录矩形，不触发纹理拷贝
- 图像转换仅在必要时执行
- 尺寸查询直接委托给包装的图像

### 关键设计决策

1. **简单包装**: 不创建新纹理，直接包装 `SkImage`
2. **零拷贝子图像**: 子区域图像共享底层纹理
3. **可选 Recorder**: 支持无 Recorder 的图像包装（已经是 Graphite 后端时）
4. **自动转换**: 工厂函数自动处理非 Graphite 图像的转换
5. **未来方向**: 注释表明该类可能被 `FilterResult` 替代

## 性能考量

### 内存效率

1. **零拷贝**: 子图像不复制纹理数据
2. **共享纹理**: 多个 SpecialImage 可共享同一 GPU 纹理
3. **智能指针**: 使用 `sk_sp` 管理生命周期，避免泄漏

### 转换开销

1. **按需转换**: 仅在非 Graphite 图像时才上传到 GPU
2. **缓存复用**: `GetGraphiteBacked()` 可能复用已上传的纹理
3. **失败快速返回**: 无效输入立即返回 null

### 接口开销

- 虚函数调用开销（继承自 `SkSpecialImage`）
- 所有访问器直接委托给 `SkImage`，最小化间接层

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/core/SkSpecialImage.h` | 抽象基类定义 |
| `src/gpu/graphite/Image_Graphite.h` | Graphite 图像实现 |
| `src/gpu/graphite/Device.h` | Graphite 设备类 |
| `src/gpu/graphite/TextureUtils.h` | 图像转换辅助函数 |
| `src/gpu/graphite/Recorder.h` | 命令录制器 |
| `src/core/SkImageFilter.h` | 图像滤镜基类 |
| `include/core/SkImage.h` | 图像接口定义 |
| `include/core/SkSurfaceProps.h` | Surface 属性定义 |
