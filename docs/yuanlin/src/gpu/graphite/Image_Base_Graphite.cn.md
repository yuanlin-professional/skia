# Image_Base_Graphite

> 源文件
> - src/gpu/graphite/Image_Base_Graphite.h
> - src/gpu/graphite/Image_Base_Graphite.cpp

## 概述

`Image_Base` 是 Skia Graphite 渲染引擎中所有图像类型的抽象基类。该类继承自 `SkImage_Base`，为 Graphite 后端的图像（包括普通 RGBA 图像和 YUVA 图像）提供统一的接口和通用功能。

核心职责包括：管理图像与渲染设备的动态链接、提供图像复制和子集操作的默认实现、处理色彩空间转换、以及确保图像在绘制时正确同步设备的渲染任务。该类采用设备链接机制，允许图像跟踪可能修改其纹理的设备，实现动态图像的自动刷新。

## 架构位置

```
SkImage (公共 API)
  └── SkImage_Base (跨平台基础)
      └── Image_Base (Graphite 专用基类)
          ├── Image (RGBA 图像)
          └── Image_YUVA (YUVA 图像)
```

`Image_Base` 位于 Graphite 图像层次结构的中间层，向上连接 Skia 公共 API，向下为具体图像类型提供通用实现。它封装了 Graphite 特有的资源管理和设备交互逻辑。

## 主要类与结构体

### Image_Base

**核心职责**：
- 管理与渲染设备的链接关系
- 提供默认的图像复制实现（Copy-as-draw）
- 实现图像子集和色彩空间转换
- 确保图像使用时同步设备任务
- 阻止 Ganesh API 调用（返回 no-op）

**关键成员**：

```cpp
mutable skia_private::STArray<1, sk_sp<Device>> fLinkedDevices SK_GUARDED_BY(fDeviceLinkLock);
mutable SkSpinlock fDeviceLinkLock;
```

使用小容量数组（默认容量 1）优化常见情况：大多数图像只链接一个设备或不链接设备。使用自旋锁保护并发访问，因为操作通常很快且无竞争。

## 公共 API 函数

### 设备链接管理

#### linkDevice

```cpp
void linkDevice(sk_sp<Device> device);
```

**功能**：将图像链接到可能修改其纹理的设备

**使用场景**：
- `Image::WrapDevice` 包装设备表面时
- `Image_YUVA::WrapImages` 包装平面图像时

**线程安全**：虽然仅在对象创建时调用，但仍使用自旋锁避免线程警告。

#### linkDevices

```cpp
void linkDevices(const Image_Base* other);
```

**功能**：复制另一个图像的所有设备链接

**使用场景**：
- 共享纹理的图像视图（如 `onReinterpretColorSpace`）
- `Image_YUVA::WrapImages` 继承平面图像的链接

#### notifyInUse

```cpp
void notifyInUse(Recorder* recorder, DrawContext* drawContext) const;
```

**功能**：通知所有链接设备图像将被使用，触发设备刷新

**核心逻辑**：
1. 遍历 `fLinkedDevices` 数组
2. 调用每个设备的 `notifyInUse`
3. 如果设备返回 `true` 或已无效，解除链接（`reset()`）
4. 所有设备都解除链接后清空数组

**解除链接条件**：
- 设备已被销毁（指针为空）
- 设备不再需要链接（`notifyInUse` 返回 `true`）
- 设备已标记为不可变
- 设备被图像独占持有

#### isDynamic

```cpp
bool isDynamic() const;
```

**功能**：判断图像是否链接到可能修改其纹理的设备

**返回值**：
- `true`：有活跃的设备链接
- `false`：无设备链接或所有设备已失效

**清理逻辑**：检查过程中自动清理失效的设备链接。

### 图像操作

#### copyImage

```cpp
virtual sk_sp<Image> copyImage(
    Recorder* recorder,
    const SkIRect& subset,
    Budgeted budgeted,
    Mipmapped mipmapped,
    SkBackingFit backingFit,
    std::string_view label) const;
```

**功能**：复制图像或其子集

**默认实现**：调用 `CopyAsDraw`（通过绘制复制）

**子类重写**：
- `Image` 类优先使用 blit-based 复制
- 如果 blit 不可用才回退到 draw-based 复制

#### onMakeSubset

```cpp
sk_sp<SkImage> onMakeSubset(
    SkRecorder* recorder,
    const SkIRect& subset,
    RequiredProperties requiredProps) const final;
```

**功能**：创建图像的子集

**优化策略**：
1. 如果 `subset` 等于图像边界
2. 且满足 mipmap 要求
3. 且图像不是动态的
4. 则直接返回自身（`sk_ref_sp(this)`）

**标签处理**：
- 从原始纹理代理获取标签
- 如果有标签，添加 `_Subset` 后缀
- 否则使用默认标签 `"ImageSubsetTexture"`

#### makeColorTypeAndColorSpace

```cpp
sk_sp<SkImage> makeColorTypeAndColorSpace(
    SkRecorder* recorder,
    SkColorType targetCT,
    sk_sp<SkColorSpace> targetCS,
    RequiredProperties requiredProps) const final;
```

**功能**：创建具有不同色彩类型和色彩空间的图像

**优化策略**：
- 如果色彩信息不变且图像非动态，返回自身
- 否则调用 `CopyAsDraw` 执行转换

**标签处理**：添加 `_CTandCSConversion` 后缀。

#### onMakeSurface

```cpp
sk_sp<SkSurface> onMakeSurface(SkRecorder* recorder, const SkImageInfo& info) const final;
```

创建具有指定信息的渲染目标表面，调用 `SkSurfaces::RenderTarget`。

### Recorder 验证

#### isValid

```cpp
bool isValid(SkRecorder* recorder) const final;
```

验证 recorder 类型是否为 `SkRecorder::Type::kGraphite`。

### Ganesh API 阻断

#### onReadPixels

```cpp
bool onReadPixels(GrDirectContext*, ...) const final { return false; }
```

#### getROPixels

```cpp
bool getROPixels(GrDirectContext*, SkBitmap*, CachingHint) const final { return false; }
```

#### onAsyncRescaleAndReadPixels

```cpp
void onAsyncRescaleAndReadPixels(...) const override;
```

记录警告日志并立即调用回调返回 `nullptr`：

```cpp
SKGPU_LOG_W("Cannot use Ganesh async API with Graphite-backed image, use API on Context");
```

## 内部实现细节

### 设备链接的线程安全

使用 `SkSpinlock` 保护 `fLinkedDevices` 访问：

```cpp
SkAutoSpinlock lock{fDeviceLinkLock};
```

**选择自旋锁的原因**：
1. 大多数图像只在 Recorder 线程使用，无竞争
2. 临界区很短（简单的遍历和检查）
3. 自旋锁比互斥锁开销更小

### 空数组优化

检查前先检测数组是否为空，避免无谓的锁竞争：

```cpp
// 注意：实际代码在锁内检查，但这里的注释说明了设计意图
if (!fLinkedDevices.empty()) {
    // 处理设备链接
}
```

一旦数组变为空，在不添加新设备的情况下永远不会再有元素（设计保证）。

### 设备链接清理策略

`notifyInUse` 和 `isDynamic` 使用延迟清理：

```cpp
for (sk_sp<Device>& device : fLinkedDevices) {
    if (!device || device->notifyInUse(recorder, drawContext)) {
        device.reset();  // 标记为空但不立即删除
        emptyCount++;
    }
}
if (emptyCount == fLinkedDevices.size()) {
    fLinkedDevices.clear();  // 所有都失效时才清空数组
}
```

**好处**：
- 避免在遍历过程中修改数组
- 减少内存分配/释放次数

### 代理标签获取

辅助函数 `get_base_proxy_for_label` 处理不同图像类型：

```cpp
TextureProxy* get_base_proxy_for_label(const Image_Base* baseImage) {
    if (baseImage->type() == SkImage_Base::Type::kGraphite) {
        return static_cast<const Image*>(baseImage)->textureProxyView().proxy();
    }
    // YUVA 图像：使用第一个通道的代理标签
    SkASSERT(baseImage->type() == SkImage_Base::Type::kGraphiteYUVA);
    return static_cast<const Image_YUVA*>(baseImage)->proxyView(0).proxy();
}
```

对于 YUVA 图像，由于子集操作会展平为 RGBA，因此随意选择一个代理的标签即可。

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `SkImage_Base` | Skia 图像基类 |
| `Device` | 渲染设备，可能修改图像纹理 |
| `Recorder` | 资源管理和任务调度 |
| `DrawContext` | 绘制上下文，用于任务依赖 |

### 工具类和函数

| 类型 | 用途 |
|------|------|
| `CopyAsDraw` | 通过绘制复制图像（在 TextureUtils 中） |
| `AsGraphiteRecorder` | 将 SkRecorder 转换为 Graphite Recorder |
| `SkSurfaces::RenderTarget` | 创建渲染目标表面 |

## 设计模式与设计决策

### 1. 模板方法模式

`Image_Base` 定义了图像操作的骨架（如 `onMakeSubset`），具体步骤（如 `copyImage`）可由子类定制。

### 2. 观察者模式变体

设备链接机制类似观察者模式：
- 图像是"被观察者"
- 设备是"观察者"
- `notifyInUse` 通知所有观察者

**差异**：链接是双向的，图像持有设备的强引用。

### 3. 延迟清理模式

设备链接数组使用延迟清理，标记为空但不立即删除，减少数组重新分配。

### 4. RAII 和自旋锁

使用 `SkAutoSpinlock` 自动管理锁的获取和释放，避免锁泄漏。

### 5. 策略分离

将复制的默认策略（draw-based）定义在基类，允许子类根据能力选择更优策略（blit-based）。

### 6. 非虚拟接口（NVI）

`onMakeSubset`、`makeColorTypeAndColorSpace` 等标记为 `final`，防止子类意外重写，确保优化逻辑一致。

## 性能考量

### 设备链接开销

1. **小数组优化**：`STArray<1>` 在只有一个设备时避免堆分配
2. **自旋锁选择**：假设无竞争，自旋锁比互斥锁快
3. **延迟清理**：减少数组重新分配次数
4. **空数组快速路径**：空数组时跳过锁（虽然实际代码在锁内检查）

### 复制优化

1. **自引用优化**：满足条件时直接返回 `this`，避免复制
2. **按需复制**：仅在必要时创建新图像
3. **Draw-based 默认**：虽然较慢，但通用性强，子类可优化

### 动态图像检测

`isDynamic` 的开销：
- 需要加锁
- 遍历设备数组
- 检查设备有效性

**优化**：结果可能被缓存在调用方（如 `onMakeSubset`）。

### 内存管理

1. **共享纹理**：视图创建操作（如 `onReinterpretColorSpace`）零拷贝
2. **设备链接引用**：使用 `sk_sp` 自动管理设备生命周期
3. **及时解除链接**：设备失效后立即释放引用，避免内存泄漏

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/image/SkImage_Base.h` | Skia 图像基类 |
| `src/gpu/graphite/Image_Graphite.h` | RGBA 图像实现 |
| `src/gpu/graphite/Image_YUVA_Graphite.h` | YUVA 图像实现 |
| `src/gpu/graphite/Device.h` | 渲染设备 |
| `src/gpu/graphite/DrawContext.h` | 绘制上下文 |
| `src/gpu/graphite/TextureUtils.h` | 纹理工具函数（CopyAsDraw） |
| `src/gpu/graphite/RecorderPriv.h` | Recorder 私有接口 |
| `src/gpu/graphite/Surface_Graphite.h` | Graphite 表面实现 |
| `src/gpu/graphite/Log.h` | 日志工具 |
| `include/core/SkRecorder.h` | Recorder 公共接口 |
| `include/gpu/graphite/Recorder.h` | Graphite Recorder 公共接口 |
| `include/gpu/GpuTypes.h` | GPU 类型定义（Budgeted、Mipmapped） |
