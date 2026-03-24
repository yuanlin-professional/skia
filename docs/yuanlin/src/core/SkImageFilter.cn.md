# SkImageFilter

> 源文件
> - include/core/SkImageFilter.h
> - src/core/SkImageFilter.cpp

## 概述

`SkImageFilter` 是 Skia 图像滤镜系统的抽象基类,提供了强大的离屏图像效果处理能力。当在 `SkPaint` 中安装图像滤镜后,所有绘制操作首先渲染到离屏缓冲区,然后滤镜处理该缓冲区生成最终图像,最后应用混合模式输出到目标设备。滤镜支持构建有向无环图(DAG)结构,实现多个滤镜的级联组合。

`SkImageFilter` 在本地坐标空间工作,这意味着模糊、变换等效果沿着绘制几何体的旋转轴应用,而非设备空间。

## 架构位置

`SkImageFilter` 位于 Skia 渲染管线的效果处理层:

- **上游**: `SkPaint` 持有并应用图像滤镜
- **下游**: 具体滤镜实现(blur、matrix、color filter、compose 等)
- **协作模块**:
  - `SkImageFilter_Base`: 内部实现基类
  - `SkImageFilterCache`: 滤镜结果缓存
  - `SkSpecialImage`: 滤镜处理的图像抽象
  - `skif::Context`: 滤镜执行上下文
- **应用场景**: 阴影、模糊、色彩调整、图像合成等高级效果

## 主要类与结构体

### SkImageFilter

**继承关系**: 继承自 `SkFlattenable`(支持序列化)

公共接口类,所有实际工作委托给 `SkImageFilter_Base`。

### SkImageFilter_Base (内部类)

**继承关系**: 继承自 `SkImageFilter`

| 关键成员变量 | 类型 | 说明 |
|-------------|------|------|
| fInputs | skia_private::STArray&lt;1, sk_sp&lt;SkImageFilter&gt;&gt; | 输入滤镜列表(DAG 节点) |
| fUsesSrcInput | bool | 是否使用源图像 |
| fUniqueID | int32_t | 滤镜唯一标识符(用于缓存键) |

### Common (辅助结构)

用于反序列化时存储公共数据:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fInputs | std::vector&lt;sk_sp&lt;SkImageFilter&gt;&gt; | 输入滤镜 |
| fCropRect | std::optional&lt;SkRect&gt; | 裁剪矩形(已废弃) |

## 公共 API 函数

### 边界计算

```cpp
enum MapDirection {
    kForward_MapDirection,   // 正向映射(源→目标)
    kReverse_MapDirection,   // 反向映射(目标→源)
};

SkIRect filterBounds(const SkIRect& src,
                     const SkMatrix& ctm,
                     MapDirection direction,
                     const SkIRect* inputRect = nullptr) const;
```

递归计算滤镜 DAG 的设备空间边界:
- **正向**: 确定源矩形经滤镜处理后的输出区域
- **反向**: 确定填充目标矩形所需的源图像区域

### 快速边界计算

```cpp
virtual SkRect computeFastBounds(const SkRect& bounds) const;
bool canComputeFastBounds() const;
```

快速近似计算对象空间边界,用于剔除和优化。

### 颜色滤镜转换

```cpp
bool isColorFilterNode(SkColorFilter** filterPtr) const;
bool asAColorFilter(SkColorFilter** filterPtr) const;
```

检查图像滤镜是否可以表示为纯颜色滤镜:
- `isColorFilterNode`: 检查节点本身是否是颜色滤镜
- `asAColorFilter`: 检查整个滤镜 DAG 是否等效于颜色滤镜

### 输入查询

```cpp
int countInputs() const;
const SkImageFilter* getInput(int i) const;
```

访问 DAG 结构的输入节点。

### 本地矩阵变换

```cpp
sk_sp<SkImageFilter> makeWithLocalMatrix(const SkMatrix& matrix) const;
```

创建应用了本地变换矩阵的滤镜副本。

### 序列化

```cpp
static sk_sp<SkImageFilter> Deserialize(const void* data,
                                        size_t size,
                                        const SkDeserialProcs* procs = nullptr);
```

从二进制数据反序列化滤镜(通过 `SkFlattenable` 机制)。

## 内部实现细节

### 滤镜 DAG 执行

核心方法 `SkImageFilter_Base::filterImage()`:

```cpp
skif::FilterResult SkImageFilter_Base::filterImage(const skif::Context& context) const {
    // 1. 检查空输出或无效矩阵
    if (context.desiredOutput().isEmpty() || !context.mapping().layerMatrix().isFinite()) {
        return result;
    }

    // 2. 构建缓存键
    SkImageFilterCacheKey key(fUniqueID,
                              context.mapping().layerMatrix().asM33(),
                              SkIRect(context.desiredOutput()),
                              srcGenID, srcSubset);

    // 3. 尝试从缓存获取结果
    if (context.backend()->cache() && context.backend()->cache()->get(key, &result)) {
        context.markCacheHit();
        return result;
    }

    // 4. 执行滤镜处理(虚函数)
    result = this->onFilterImage(context);

    // 5. 缓存结果
    if (context.backend()->cache()) {
        context.backend()->cache()->set(key, this, result);
    }

    return result;
}
```

### 边界传播算法

**正向边界计算**(`onGetOutputLayerBounds`):
```cpp
std::optional<skif::LayerSpace<SkIRect>> output =
    this->onGetOutputLayerBounds(mapping, contentBounds.roundOut());
```

从内容边界出发,通过 DAG 向下传播,计算最终输出区域。

**反向边界计算**(`onGetInputLayerBounds`):
```cpp
skif::LayerSpace<SkIRect> required =
    this->onGetInputLayerBounds(mapping, desiredOutput, contentBounds);
```

从期望输出区域出发,向上传播,计算所需输入区域。

### 透明黑色影响检测

```cpp
bool SkImageFilter_Base::affectsTransparentBlack() const {
    if (this->onAffectsTransparentBlack()) {
        return true;  // 滤镜本身影响透明黑色
    } else if (this->ignoreInputsAffectsTransparentBlack()) {
        return false;  // 滤镜明确不受输入影响
    }
    // 递归检查输入
    for (int i = 0; i < this->countInputs(); i++) {
        if (input && as_IFB(input)->affectsTransparentBlack()) {
            return true;
        }
    }
    return false;
}
```

用途: 确定是否可以使用 `computeFastBounds()` 优化。

### 矩阵能力查询

```cpp
enum class MatrixCapability {
    kTranslate,      // 仅支持平移
    kScaleTranslate, // 支持缩放和平移
    kComplex,        // 支持任意变换
};

MatrixCapability getCTMCapability() const {
    MatrixCapability result = this->onGetCTMCapability();
    // 取所有输入的最小能力
    for (int i = 0; i < count; ++i) {
        result = std::min(result, input->getCTMCapability());
    }
    return result;
}
```

用于优化变换矩阵的应用策略。

### 子滤镜辅助方法

```cpp
// 获取子滤镜的输入边界
skif::LayerSpace<SkIRect> getChildInputLayerBounds(
    int index, const skif::Mapping& mapping,
    const skif::LayerSpace<SkIRect>& desiredOutput,
    std::optional<skif::LayerSpace<SkIRect>> contentBounds) const;

// 获取子滤镜的输出边界
std::optional<skif::LayerSpace<SkIRect>> getChildOutputLayerBounds(
    int index, const skif::Mapping& mapping,
    std::optional<skif::LayerSpace<SkIRect>> contentBounds) const;

// 执行子滤镜
skif::FilterResult getChildOutput(int index, const skif::Context& ctx) const;
```

简化复合滤镜的实现,处理 null 输入(使用源图像)等边界情况。

### 唯一 ID 生成

```cpp
static int32_t next_image_filter_unique_id() {
    static std::atomic<int32_t> nextID{1};
    int32_t id;
    do {
        id = nextID.fetch_add(1, std::memory_order_relaxed);
    } while (id == 0);  // 跳过 0(保留给 SK_InvalidUniqueID)
    return id;
}
```

线程安全的 ID 分配,用于缓存键生成。

### 序列化格式

```cpp
void SkImageFilter_Base::flatten(SkWriteBuffer& buffer) const {
    buffer.writeInt(fInputs.count());
    for (int i = 0; i < fInputs.count(); i++) {
        buffer.writeBool(input != nullptr);
        if (input != nullptr) {
            buffer.writeFlattenable(input);
        }
    }
}
```

格式:
1. 输入数量(int)
2. 每个输入: 存在标志(bool) + 可选的序列化滤镜数据

历史兼容: 旧版本包含 `CropRect`,现已移除。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkFlattenable | 序列化基类 |
| SkImageFilterCache | 滤镜结果缓存 |
| SkSpecialImage | 滤镜处理的图像抽象 |
| skif::Context | 滤镜执行上下文 |
| skif::Mapping | 坐标空间映射 |
| skif::FilterResult | 滤镜输出结果 |
| SkColorFilter | 颜色滤镜(可能的优化路径) |
| SkLocalMatrixImageFilter | 本地矩阵包装器 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkPaint | 持有并应用图像滤镜 |
| SkBlurImageFilter | 模糊滤镜实现 |
| SkMatrixImageFilter | 矩阵变换滤镜 |
| SkComposeImageFilter | 滤镜组合 |
| SkMergeImageFilter | 滤镜合并 |
| SkColorFilterImageFilter | 颜色滤镜包装器 |
| SkShader | 作为着色器效果的一部分 |

## 设计模式与设计决策

### 组合模式(Composite Pattern)

滤镜 DAG 使用组合模式:
- **叶节点**: 基本滤镜(blur、color 等)
- **复合节点**: 组合滤镜(compose、merge)
- **统一接口**: 所有节点实现相同的 `filterImage()` 接口

### 模板方法模式(Template Method)

基类定义算法框架,子类实现具体步骤:
```cpp
// 基类框架
skif::FilterResult filterImage(const skif::Context& ctx) const {
    // 缓存检查 + 调用虚函数 + 缓存存储
}

// 子类实现
virtual skif::FilterResult onFilterImage(const skif::Context& ctx) const = 0;
```

### 策略模式(Backend 抽象)

通过 `skif::Backend` 抽象不同的执行后端:
- CPU 后端: 使用 `SkBitmap`
- GPU 后端: 使用纹理

### 设计决策: DAG 而非树

为什么允许滤镜 DAG(共享输入):
- 减少重复计算
- 更灵活的效果组合
- 缓存可以跨多个父节点共享

### 设计决策: 本地空间处理

为什么在本地坐标空间工作:
- 模糊等效果沿几何体方向应用(如沿旋转的矩形边缘)
- 更自然的效果表现
- 实现时将几何体绘制到未旋转的离屏缓冲区,处理后再变换回去

### 设计决策: 分离快速边界和精确边界

- `computeFastBounds()`: 保守近似,快速计算,用于剔除
- `filterBounds()`: 精确计算,可能较慢,用于分配缓冲区

### 设计决策: 移除 CropRect

历史版本包含 `CropRect` 限制输出区域,现已移除:
- 增加 API 复杂度
- 与 `filterBounds()` 功能重叠
- 现代实现通过 `desiredOutput` 参数实现相同功能

## 性能考量

### 结果缓存

`SkImageFilterCache` 缓存中间结果:
- **缓存键**: 滤镜 ID + 变换矩阵 + 输出区域 + 源图像 ID
- **缓存命中**: 避免重复滤镜处理
- **内存管理**: 自动清理最少使用的条目

### 边界优化

通过精确边界计算减少处理区域:
- **剔除**: `computeFastBounds()` 快速判断是否完全在屏幕外
- **裁剪**: `filterBounds()` 确定最小必要的源区域
- **分配优化**: 仅分配所需大小的临时缓冲区

### 透明黑色优化

```cpp
bool canComputeFastBounds() const {
    return !as_IFB(this)->affectsTransparentBlack();
}
```

如果滤镜不影响透明区域,可以使用简化的边界计算。

### 颜色滤镜降级

```cpp
bool asAColorFilter(SkColorFilter** filterPtr) const {
    if (!this->isColorFilterNode(filterPtr)) {
        return false;
    }
    // 检查是否有输入或影响透明黑色
    if (this->getInput(0) != nullptr || filterPtr->affectsTransparentBlack()) {
        return false;
    }
    return true;  // 可以优化为颜色滤镜
}
```

将简单的图像滤镜优化为更高效的颜色滤镜。

### 矩阵能力优化

根据 `getCTMCapability()` 选择优化路径:
- `kTranslate`: 仅调整输出位置,无需重新绘制
- `kScaleTranslate`: 可以使用缩放的缓存结果
- `kComplex`: 需要完整重新处理

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkImageFilter_Base.h | 实现 | 内部基类 |
| src/core/SkImageFilterCache.h | 依赖 | 结果缓存 |
| src/core/SkImageFilterTypes.h | 依赖 | 类型定义(skif 命名空间) |
| src/core/SkSpecialImage.h | 依赖 | 滤镜图像抽象 |
| src/core/SkLocalMatrixImageFilter.h | 实现 | 本地矩阵包装器 |
| src/effects/imagefilters/*.cpp | 实现 | 具体滤镜实现 |
| include/core/SkPaint.h | 使用者 | 持有图像滤镜 |
| include/core/SkColorFilter.h | 协作 | 颜色滤镜优化 |
| include/core/SkFlattenable.h | 基类 | 序列化支持 |
