# SkImage_Picture

> 源文件：src/image/SkImage_Picture.h, src/image/SkImage_Picture.cpp

## 概述

`SkImage_Picture` 是基于 `SkPicture` 矢量图形的延迟加载图像实现。它继承自 `SkImage_Lazy`，使用 `SkPictureImageGenerator` 将 Picture 命令序列按需栅格化为像素数据。该类是连接 Skia 矢量图形系统和栅格图像系统的关键桥梁，允许 Picture 像普通图像一样使用，同时保持矢量内容的灵活性和延迟栅格化的性能优势。

与普通的 `SkImage_Lazy` 相比，`SkImage_Picture` 针对 Picture 场景提供了特殊优化，包括高效的子集创建（通过调整矩阵而非像素拷贝）和缓存键生成（用于平铺图像场景）。

## 架构位置

`SkImage_Picture` 在 Skia 图像架构中的位置：

- **继承关系**：继承自 `SkImage_Lazy`（延迟加载图像基类）
- **生成器**：使用 `SkPictureImageGenerator` 提供像素数据
- **所属模块**：`src/image/` 图像实现模块
- **类型标识**：`SkImage_Base::Type::kLazyPicture`
- **创建方式**：通过静态工厂函数 `Make()` 创建

在图像生命周期中，该类负责将矢量 Picture 转换为栅格图像，采用延迟策略仅在真正需要像素时才执行绘制。

## 主要类与结构体

### SkImage_Picture

基于 Picture 的延迟加载图像类。

**继承关系**：
```cpp
class SkImage_Picture : public SkImage_Lazy
```

**核心方法**：
- `Make()`：静态工厂函数，创建 Picture 图像
- `replay()`：在 Canvas 上重放 Picture 绘制
- `onMakeSubset()`：创建子集图像（通过矩阵变换优化）
- `props()`：获取表面属性
- `getImageKeyValues()`：提取缓存键值（用于平铺图像优化）
- `type()`：返回类型标识 `kLazyPicture`

**特点**：
- 轻量级构造：只接受 `Validator` 参数，实际逻辑由基类处理
- 友元依赖：通过友元关系访问 `SkPictureImageGenerator` 的私有成员

## 公共 API 函数

### SkImage_Picture::Make

```cpp
static sk_sp<SkImage> Make(sk_sp<SkPicture> picture,
                           const SkISize& dimensions,
                           const SkMatrix* matrix,
                           const SkPaint* paint,
                           SkImages::BitDepth bitDepth,
                           sk_sp<SkColorSpace> colorSpace,
                           SkSurfaceProps props)
```

从 Picture 创建延迟加载图像。

**参数**：
- `picture`：Picture 命令序列
- `dimensions`：图像尺寸
- `matrix`：可选的变换矩阵
- `paint`：可选的绘制参数
- `bitDepth`：位深度（`kU8` 或 `kF16`）
- `colorSpace`：颜色空间
- `props`：表面属性

**返回值**：成功返回图像指针，失败返回 `nullptr`

### replay

```cpp
void replay(SkCanvas* canvas) const
```

在指定 Canvas 上重放 Picture 绘制，线程安全（内部加锁）。

**实现**：
1. 获取共享生成器并加锁
2. 清空画布为透明
3. 绘制 Picture，应用矩阵和可选的 Paint

### props

```cpp
const SkSurfaceProps* props() const
```

获取表面属性指针，线程安全（表面属性在构造时设置，只读访问）。

### getImageKeyValues

```cpp
bool getImageKeyValues(uint32_t keyValues[SkTiledImageUtils::kNumImageKeyValues]) const
```

提取 Picture 图像的缓存键值，用于平铺图像场景的优化。

**返回值**：成功返回 `true` 并填充键值数组，失败返回 `false`

**失败条件**：
- Picture 有自定义 Paint（过于复杂）
- 颜色空间不是 sRGB
- 矩阵不是恒等或平移（复杂变换难以缓存）

## 内部实现细节

### 工厂函数实现

`Make()` 函数通过生成器和验证器创建图像：

```cpp
sk_sp<SkImage> SkImage_Picture::Make(...) {
    // 1. 创建 Picture 图像生成器
    auto gen = SkImageGenerators::MakeFromPicture(dimensions, std::move(picture),
                                                  matrix, paint, bitDepth,
                                                  std::move(colorSpace), props);

    // 2. 包装为共享生成器
    SkImage_Lazy::Validator validator(SharedGenerator::Make(std::move(gen)), nullptr, nullptr);

    // 3. 创建 SkImage_Picture 实例
    return validator ? sk_make_sp<SkImage_Picture>(&validator) : nullptr;
}
```

使用 `Validator` 机制确保参数有效，验证失败时返回 `nullptr`。

### Picture 重放

`replay()` 实现线程安全的 Picture 绘制：

```cpp
void SkImage_Picture::replay(SkCanvas* canvas) const {
    auto sharedGenerator = this->generator();
    SkAutoMutexExclusive mutex(sharedGenerator->fMutex);

    auto pictureIG = static_cast<SkPictureImageGenerator*>(sharedGenerator->fGenerator.get());
    canvas->clear(SkColors::kTransparent);
    canvas->drawPicture(pictureIG->fPicture,
                        &pictureIG->fMatrix,
                        SkOptAddressOrNull(pictureIG->fPaint));
}
```

**关键点**：
1. **互斥锁保护**：确保多线程访问生成器的安全性
2. **类型转换**：通过 `static_cast` 访问具体生成器类型
3. **透明背景**：先清空画布，避免脏像素
4. **可选 Paint**：通过 `SkOptAddressOrNull` 处理 `std::optional`

### 高效子集创建

`onMakeSubset()` 通过调整矩阵而非像素拷贝实现子集：

```cpp
sk_sp<SkImage> SkImage_Picture::onMakeSubset(SkRecorder*,
                                             const SkIRect& subset,
                                             RequiredProperties) const {
    auto sharedGenerator = this->generator();
    auto pictureIG = static_cast<SkPictureImageGenerator*>(sharedGenerator->fGenerator.get());

    // 调整矩阵以实现裁剪效果
    SkMatrix matrix = pictureIG->fMatrix;
    matrix.postTranslate(-subset.left(), -subset.top());

    // 确定位深度
    SkImages::BitDepth bitDepth =
            this->colorType() == kRGBA_F16_SkColorType ? SkImages::BitDepth::kF16
                                                       : SkImages::BitDepth::kU8;

    // 创建新的 Picture 图像，尺寸为子集大小
    return SkImage_Picture::Make(pictureIG->fPicture, subset.size(),
                                 &matrix, SkOptAddressOrNull(pictureIG->fPaint),
                                 bitDepth, this->refColorSpace(), pictureIG->fProps);
}
```

**优化原理**：
- **零拷贝**：不栅格化原图像，只创建新的 Picture 图像
- **矩阵平移**：通过 `postTranslate()` 移动 Picture 内容
- **参数复用**：复制原图像的 Paint、颜色空间、表面属性

这种方法比栅格图像的子集创建（需要像素拷贝）高效得多。

### 缓存键生成

`getImageKeyValues()` 为平铺图像场景生成唯一键：

```cpp
bool SkImage_Picture::getImageKeyValues(uint32_t keyValues[6]) const {
    auto sharedGenerator = this->generator();
    SkAutoMutexExclusive mutex(sharedGenerator->fMutex);

    auto pictureIG = static_cast<SkPictureImageGenerator*>(sharedGenerator->fGenerator.get());

    // 1. 拒绝复杂情况
    if (pictureIG->fPaint.has_value()) return false;
    if (!sharedGenerator->getInfo().colorSpace()->isSRGB()) return false;
    if (!pictureIG->fMatrix.isIdentity() && !pictureIG->fMatrix.isTranslate()) return false;

    // 2. 提取关键参数
    bool isU8 = sharedGenerator->getInfo().colorType() != kRGBA_F16_SkColorType;
    uint32_t pixelGeometry = this->props()->pixelGeometry();
    uint32_t surfacePropFlags = this->props()->flags();
    int width = sharedGenerator->getInfo().width();
    int height = sharedGenerator->getInfo().height();
    float transX = pictureIG->fMatrix.getTranslateX();
    float transY = pictureIG->fMatrix.getTranslateY();

    // 3. 编码到键值数组
    keyValues[0] = (isU8 ? 0x1 : 0x0) | (pixelGeometry << 1) | (surfacePropFlags << 4);
    keyValues[1] = pictureIG->fPicture->uniqueID();
    keyValues[2] = width;
    keyValues[3] = height;
    memcpy(&keyValues[4], &transX, sizeof(uint32_t));
    memcpy(&keyValues[5], &transY, sizeof(uint32_t));

    return true;
}
```

**键结构**（6 个 uint32）：
- `[0]`：位深度标志、像素几何、表面属性标志
- `[1]`：Picture 唯一 ID
- `[2]`：宽度
- `[3]`：高度
- `[4]`：X 平移（浮点数按位拷贝）
- `[5]`：Y 平移（浮点数按位拷贝）

**限制条件**：
- 只支持简单矩阵（恒等或平移）
- 只支持 sRGB 颜色空间
- 不能有自定义 Paint

这些限制确保键足够小且常见场景覆盖率高。

### 表面属性访问

```cpp
const SkSurfaceProps* SkImage_Picture::props() const {
    auto pictureIG = static_cast<SkPictureImageGenerator*>(this->generator()->fGenerator.get());
    return &pictureIG->fProps;
}
```

直接访问生成器的表面属性，无需加锁（表面属性是不可变的）。

## 依赖关系

### 核心依赖

| 依赖项 | 用途 |
|--------|------|
| `SkImage_Lazy` | 基类，提供延迟加载框架 |
| `SkPictureImageGenerator` | 生成器，提供像素数据 |
| `SkPicture` | Picture 命令序列 |
| `SharedGenerator` | 线程安全的生成器包装 |

### 次要依赖

| 依赖项 | 用途 |
|--------|------|
| `SkMatrix` | 几何变换 |
| `SkPaint` | 绘制参数 |
| `SkSurfaceProps` | 表面属性 |
| `SkCanvas` | 重放绘制 |
| `SkTiledImageUtils` | 平铺图像键值定义 |

### 反向依赖

| 依赖方 | 用途 |
|--------|------|
| 图像工厂 | 通过 `SkImages::DeferredFromPicture()` 创建 |
| 平铺图像系统 | 使用 `getImageKeyValues()` 进行缓存 |

## 设计模式与设计决策

### 继承与组合

`SkImage_Picture` 通过继承 `SkImage_Lazy` 复用延迟加载逻辑，同时通过组合 `SkPictureImageGenerator` 处理 Picture 特定行为。

### 决策 1：子集通过矩阵变换而非像素拷贝

- **原因**：Picture 是矢量内容，调整矩阵比栅格化后裁剪高效
- **优势**：零拷贝，保持延迟栅格化优势
- **权衡**：增加了代码复杂性

### 决策 2：限制缓存键条件

```cpp
if (pictureIG->fPaint.has_value()) return false;
```

- **原因**：Paint 可能包含复杂的着色器、滤镜，难以编码到固定大小键
- **权衡**：覆盖常见场景（简单 Picture），牺牲复杂场景

### 决策 3：友元访问生成器私有成员

```cpp
friend class SkImage_Picture;
```

- **原因**：频繁访问生成器的 `fPicture`、`fMatrix`、`fPaint`、`fProps`
- **优势**：避免为每个成员添加访问器
- **权衡**：打破封装性，增加耦合

### 决策 4：键值数组按位拷贝浮点数

```cpp
memcpy(&keyValues[4], &transX, sizeof(uint32_t));
```

- **原因**：需要浮点平移值参与缓存键
- **权衡**：假设 `sizeof(float) == sizeof(uint32_t)`，有平台依赖风险（但实际上现代平台都满足）

### 决策 5：replay 清空画布

```cpp
canvas->clear(SkColors::kTransparent);
```

- **原因**：Picture 可能不覆盖整个画布，避免脏像素
- **权衡**：额外的清空开销，但保证正确性

## 性能考量

### 延迟栅格化优势

- **构造开销小**：只创建生成器，不栅格化
- **内存占用低**：Picture 本身通常比栅格数据小
- **多尺寸友好**：同一 Picture 可生成不同尺寸图像

### 子集创建性能

**Picture 图像**：
```cpp
// O(1) - 只创建新的 Picture 图像对象
matrix.postTranslate(-subset.left(), -subset.top());
return SkImage_Picture::Make(fPicture, subset.size(), &matrix, ...);
```

**栅格图像**：
```cpp
// O(W×H) - 需要拷贝像素
SkRectMemcpy(dst, ..., subset.height());
```

Picture 子集创建比栅格图像快数百倍（取决于尺寸）。

### 缓存键查找

`getImageKeyValues()` 用于平铺图像缓存，避免重复栅格化：

```cpp
// 伪代码：平铺图像系统
uint32_t key[6];
if (pictureImage->getImageKeyValues(key)) {
    if (auto cached = cache.find(key)) {
        return cached;  // 命中缓存，避免栅格化
    }
}
```

对于重复绘制相同 Picture 的场景（如 UI 平铺），性能提升显著。

### replay 开销

每次调用都重新绘制 Picture：

```cpp
canvas->clear(...);           // O(W×H)
canvas->drawPicture(...);     // O(命令数)
```

对于复杂 Picture，开销可能很大。建议调用方缓存栅格化结果。

### 线程安全成本

互斥锁保护生成器访问：

```cpp
SkAutoMutexExclusive mutex(sharedGenerator->fMutex);
```

多线程并发访问时会产生锁竞争，但通常栅格化时间远大于锁等待时间。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/image/SkImage_Lazy.h` | 基类 | 延迟加载图像基类 |
| `src/image/SkPictureImageGenerator.h` | 生成器 | Picture 栅格化生成器 |
| `include/core/SkPicture.h` | 核心依赖 | Picture 命令序列 |
| `include/core/SkMatrix.h` | 几何变换 | 矩阵变换支持 |
| `include/core/SkCanvas.h` | 绘制引擎 | 重放 Picture |
| `include/core/SkTiledImageUtils.h` | 平铺工具 | 缓存键定义 |
| `src/image/SkImage_Base.h` | 图像基类 | 图像实现框架 |
| `include/core/SkSurfaceProps.h` | 表面属性 | 渲染属性配置 |
