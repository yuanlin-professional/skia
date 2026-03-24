# GrDynamicAtlas

> 源文件: src/gpu/ganesh/GrDynamicAtlas.h, src/gpu/ganesh/GrDynamicAtlas.cpp

## 概述

`GrDynamicAtlas` 是 Ganesh GPU 后端中实现动态增长纹理图集(Atlas)的核心类。与固定大小的图集不同,动态图集从较小的初始尺寸开始,在空间不足时自动扩展,直到达到硬件支持的最大纹理尺寸。该类使用惰性代理(Lazy Proxy)延迟实际 GPU 纹理的创建,并支持纹理复用以优化内存使用。

主要功能包括:
- **动态增长**: 从初始尺寸开始,按 2 的幂次递增扩展宽度或高度
- **空间分配**: 支持 Skyline 和 Pow2 两种矩形装箱算法
- **惰性实例化**: 使用 Lazy Proxy 延迟纹理创建,仅在实际需要时分配 GPU 内存
- **纹理复用**: 支持传入已存在的纹理作为后备存储,避免重复分配
- **自动填充**: 在矩形周围添加 1 像素填充,避免采样伪影
- **绘制边界追踪**: 记录实际使用的区域,优化上传和渲染

## 架构位置

该模块位于 Ganesh 渲染管线的资源管理层:

```
src/gpu/ganesh/
├── GrDynamicAtlas.h/cpp           # 动态图集(当前模块)
├── GrDrawOpAtlas.h/cpp            # 固定大小操作图集
├── GrAtlasTypes.h                 # 图集基础类型
├── GrOnFlushResourceProvider.h    # Flush 时资源提供者
└── ops/
    └── PathStencilCoverOp.cpp     # 路径渲染使用动态图集
```

**使用场景**:
- 路径渲染中的模板缓存
- 阴影贴图
- 动态生成的掩码纹理
- 裁剪路径缓存

## 主要类与结构体

### GrDynamicAtlas
动态增长的纹理图集主类。

```cpp
class GrDynamicAtlas {
public:
    static constexpr GrSurfaceOrigin kTextureOrigin = kTopLeft_GrSurfaceOrigin;
    static constexpr int kPadding = 1;  // 每个矩形的填充

    enum class InternalMultisample : bool {
        kNo = false,
        kYes = true
    };

    enum class RectanizerAlgorithm {
        kSkyline,  // Skyline 算法
        kPow2      // 2 的幂次算法
    };

    GrDynamicAtlas(GrColorType colorType, InternalMultisample,
                   SkISize initialSize, int maxAtlasSize,
                   const GrCaps&, RectanizerAlgorithm);

    bool addRect(int width, int height, SkIPoint16* location);
    bool instantiate(GrOnFlushResourceProvider*,
                     sk_sp<GrTexture> backingTexture = nullptr);
    void reset(SkISize initialSize, const GrCaps&);
};
```

**成员变量**:
- `fColorType`: 图集颜色类型
- `fInternalMultisample`: 是否使用内部多重采样
- `fMaxAtlasSize`: 最大图集尺寸限制
- `fRectanizerAlgorithm`: 空间分配算法
- `fWidth`, `fHeight`: 当前图集尺寸
- `fDrawBounds`: 实际使用的绘制区域
- `fNodeAllocator`: Node 对象的 Arena 分配器
- `fTopNode`: Node 链表头节点
- `fTextureProxy`: 惰性纹理代理
- `fBackingTexture`: 实际后备纹理

### GrDynamicAtlas::Node
内部节点类,每个节点管理图集中的一个子矩形区域。

```cpp
class GrDynamicAtlas::Node {
public:
    Node(Node* previous, Rectanizer* rectanizer, int x, int y);
    bool addRect(int w, int h, SkIPoint16* loc);
    Node* previous() const;

private:
    Node* const fPrevious;        // 前一个节点(链表)
    Rectanizer* const fRectanizer; // 该节点的空间分配器
    const int fX, fY;             // 节点在图集中的偏移
};
```

**设计理念**: 图集扩展时,新增的空间作为新的 Node 添加到链表中,每个 Node 有独立的 Rectanizer。

## 公共 API 函数

### GrDynamicAtlas::MakeLazyAtlasProxy
创建惰性实例化的图集纹理代理。

```cpp
static sk_sp<GrTextureProxy> MakeLazyAtlasProxy(
    LazyInstantiateAtlasCallback&& callback,
    GrColorType colorType,
    InternalMultisample internalMultisample,
    const GrCaps& caps,
    GrSurfaceProxy::UseAllocator useAllocator)
```

**功能**:
1. 根据颜色类型和多重采样选项确定后端格式
2. 查询硬件的内部多重采样数
3. 创建完全惰性的纹理代理

**返回**: 惰性纹理代理,延迟到 `instantiate` 时创建实际纹理

### GrDynamicAtlas::addRect
尝试在图集中分配指定尺寸的矩形。

```cpp
bool GrDynamicAtlas::addRect(int width, int height, SkIPoint16* location)
```

**实现流程**:
1. 调用 `internalPlaceRect` 尝试分配空间
2. 成功时更新 `fDrawBounds` 追踪使用边界
3. 返回分配是否成功和位置

**返回**: 成功返回 `true` 并在 `location` 中返回左上角坐标

### GrDynamicAtlas::internalPlaceRect
内部矩形分配逻辑,处理扩展。

```cpp
bool GrDynamicAtlas::internalPlaceRect(int w, int h, SkIPoint16* loc)
```

**实现流程**:
1. **边界检查**: 如果 `max(w, h) > fMaxAtlasSize`,返回失败
2. **零尺寸处理**: 如果 `min(w, h) <= 0`,返回 `(0, 0)`
3. **初始化**: 如果 `fTopNode` 为空,创建初始节点
4. **尝试现有节点**: 遍历节点链表尝试分配
5. **扩展图集**: 如果失败且未达上限,扩展图集并重试

**扩展策略**: 优先扩展较短的维度,每次扩展翻倍尺寸,直到达到 `fMaxAtlasSize`。

### GrDynamicAtlas::instantiate
实例化惰性代理,创建实际 GPU 纹理。

```cpp
bool GrDynamicAtlas::instantiate(GrOnFlushResourceProvider* onFlushRP,
                                 sk_sp<GrTexture> backingTexture = nullptr)
```

**功能**:
1. 断言当前未实例化
2. 设置代理的惰性尺寸为 `fDrawBounds`(实际使用区域)
3. 如果提供 `backingTexture`,设置为后备纹理
4. 调用 `onFlushRP->instantiateProxy` 实例化

**优化**: 只分配实际使用区域的纹理,而不是完整的 `fWidth × fHeight`。

### GrDynamicAtlas::reset
重置图集状态,复用对象。

```cpp
void GrDynamicAtlas::reset(SkISize initialSize, const GrCaps& caps)
```

**功能**:
1. 重置 Arena 分配器,释放所有 Node
2. 将尺寸重置为初始值(向上舍入到 2 的幂次)
3. 创建新的惰性纹理代理
4. 清空绘制边界

**用途**: 在帧间复用图集对象,避免重复构造析构开销。

### GrDynamicAtlas::Node::addRect
在节点的 Rectanizer 中分配矩形。

```cpp
bool Node::addRect(int w, int h, SkIPoint16* loc)
```

**实现细节**:
1. 为非全尺寸矩形添加 `kPadding` 填充
2. 调用 `fRectanizer->addRect` 分配空间
3. 将返回的位置偏移 `(fX, fY)` 转换为图集全局坐标

**填充逻辑**: 只有当矩形小于节点尺寸时才添加填充,全尺寸矩形(整个纹理)不需要填充。

## 内部实现细节

### 惰性代理回调

`reset` 中创建惰性代理的回调:

```cpp
[this](GrResourceProvider* resourceProvider, const LazyAtlasDesc& desc) {
    if (!fBackingTexture) {
        fBackingTexture = resourceProvider->createTexture(
            fTextureProxy->backingStoreDimensions(),
            desc.fFormat, desc.fTextureType, desc.fRenderable,
            desc.fSampleCnt, desc.fMipmapped, desc.fBudgeted,
            desc.fProtected, desc.fLabel);
    }
    return GrSurfaceProxy::LazyCallbackResult(fBackingTexture);
}
```

**机制**:
- 首次调用时创建纹理并存储在 `fBackingTexture`
- 后续调用直接返回缓存的纹理
- 支持外部提供 `backingTexture` 复用已存在纹理

### 图集扩展策略

`internalPlaceRect` 中的扩展逻辑:

```cpp
if (fHeight <= fWidth) {
    int top = fHeight;
    fHeight = std::min(fHeight * 2, fMaxAtlasSize);
    fTopNode = this->makeNode(fTopNode, 0, top, fWidth, fHeight);
} else {
    int left = fWidth;
    fWidth = std::min(fWidth * 2, fMaxAtlasSize);
    fTopNode = this->makeNode(fTopNode, left, 0, fWidth, fHeight);
}
```

**策略**:
- 优先扩展较短的维度,保持接近正方形
- 每次扩展翻倍尺寸
- 新增的矩形区域作为新的 Node 添加到链表头

### Node 链表结构

Node 通过 `fPrevious` 形成单向链表:

```
[Node3: (256,0)-(512,256)] -> [Node2: (0,128)-(256,256)] -> [Node1: (0,0)-(256,128)] -> nullptr
```

分配时从头节点开始遍历,先尝试新增的空间,提高空间利用率。

### Arena 分配优化

使用 `SkSTArenaAllocWithReset<512>` 分配 Node 和 Rectanizer:

```cpp
SkSTArenaAllocWithReset<512> fNodeAllocator;
```

**优势**:
- 小对象连续分配,减少内存碎片
- `reset` 时一次性释放所有对象
- 栈上缓冲区(512 字节)避免小图集的堆分配

### 绘制边界优化

`addRect` 追踪实际使用区域:

```cpp
fDrawBounds.fWidth = std::max(fDrawBounds.width(), location->x() + width);
fDrawBounds.fHeight = std::max(fDrawBounds.height(), location->y() + height);
```

`instantiate` 使用该边界而非完整尺寸:

```cpp
fTextureProxy->priv().setLazyDimensions(fDrawBounds);
```

**收益**: 如果图集扩展到 512×512 但只使用了 300×400 区域,实际只分配 300×400 纹理。

### 填充避免采样伪影

`Node::addRect` 添加填充:

```cpp
if (w < fRectanizer->width()) {
    w = std::min(w + kPadding, fRectanizer->width());
}
```

**原因**: GPU 纹理采样时可能读取相邻像素,填充避免不同矩形间的干扰。

## 依赖关系

### 外部依赖
```cpp
#include "src/gpu/Rectanizer.h"               // 矩形装箱算法接口
#include "src/gpu/RectanizerSkyline.h"        // Skyline 算法实现
#include "src/gpu/RectanizerPow2.h"           // Pow2 算法实现
#include "src/gpu/ganesh/GrOnFlushResourceProvider.h" // Flush 时资源提供者
#include "src/base/SkArenaAlloc.h"            // Arena 分配器
```

### 被依赖模块
- `src/gpu/ganesh/ops/PathStencilCoverOp.cpp` - 路径模板覆盖操作
- `src/gpu/ganesh/ops/ShadowRRectOp.cpp` - 阴影渲染
- `src/gpu/ganesh/GrClipStack.cpp` - 裁剪栈使用动态图集

## 设计模式与设计决策

### 1. 惰性实例化模式
使用 Lazy Proxy 延迟纹理创建:

```cpp
fTextureProxy = MakeLazyAtlasProxy(callback, ...);
```

**优势**:
- 可以在不知道最终尺寸时创建代理
- 避免过早占用 GPU 内存
- 支持动态调整尺寸

### 2. 链表扩展策略
新增空间作为新节点添加到链表:

```cpp
fTopNode = this->makeNode(fTopNode, left, 0, fWidth, fHeight);
```

**优势**:
- 简化逻辑,每个节点独立管理空间
- 新空间优先分配(链表头),提高连续性
- 避免重建全局 Rectanizer

### 3. 策略模式
支持多种 Rectanizer 算法:

```cpp
enum class RectanizerAlgorithm {
    kSkyline,  // 高空间利用率
    kPow2      // 快速分配
};
```

在 `makeNode` 中根据配置选择:

```cpp
Rectanizer* rectanizer = (fRectanizerAlgorithm == RectanizerAlgorithm::kSkyline)
        ? (Rectanizer*)fNodeAllocator.make<RectanizerSkyline>(width, height)
        : fNodeAllocator.make<RectanizerPow2>(width, height);
```

### 4. 对象池模式
`reset` 方法允许复用图集对象:

```cpp
void reset(SkISize initialSize, const GrCaps& caps);
```

帧间复用避免重复构造析构开销。

### 5. 资源复用
`instantiate` 支持传入已存在纹理:

```cpp
bool instantiate(GrOnFlushResourceProvider*, sk_sp<GrTexture> backingTexture = nullptr);
```

**用途**: 上一帧的图集纹理可以复用到当前帧,避免频繁分配释放。

## 性能考量

### 1. 延迟分配
惰性代理确保纹理在实际需要时才创建:
- 如果没有添加任何矩形,不会分配 GPU 内存
- 只分配实际使用区域(`fDrawBounds`)

### 2. 扩展策略优化
- **按 2 的幂次扩展**: 匹配 GPU 纹理尺寸约束,避免额外对齐开销
- **优先扩展短边**: 保持接近正方形,减少浪费
- **增量扩展**: 从小尺寸开始,避免过度分配

### 3. 空间利用率
- **Skyline 算法**: 提供 80-90% 的空间利用率
- **Pow2 算法**: 更快但利用率较低,适合对齐需求

### 4. Arena 分配
使用 Arena 分配 Node 和 Rectanizer:
- 连续内存提高缓存命中率
- 批量释放避免逐个析构开销
- 栈缓冲区避免小图集的堆分配

### 5. 避免碎片
链表结构避免 Rectanizer 碎片:
- 新增空间作为独立节点,不受现有碎片影响
- 每个节点都有机会分配新矩形

### 6. 填充权衡
1 像素填充增加了约 2-4% 的内存开销,但避免了采样伪影,权衡合理。

### 7. 绘制边界优化
追踪实际使用区域:
- 减少上传数据量
- 减少渲染覆盖的像素数
- 对于稀疏使用的图集,收益显著

## 相关文件

### 核心实现
- `src/gpu/ganesh/GrDrawOpAtlas.h/cpp` - 固定大小图集实现
- `src/gpu/ganesh/GrAtlasTypes.h` - 图集基础类型

### 算法依赖
- `src/gpu/Rectanizer.h` - 矩形装箱算法接口
- `src/gpu/RectanizerSkyline.h/cpp` - Skyline 算法
- `src/gpu/RectanizerPow2.h/cpp` - Pow2 算法

### 资源管理
- `src/gpu/ganesh/GrOnFlushResourceProvider.h` - Flush 时资源提供者
- `src/gpu/ganesh/GrResourceProvider.h` - GPU 资源提供者
- `src/gpu/ganesh/GrSurfaceProxy.h` - 表面代理

### 使用场景
- `src/gpu/ganesh/ops/PathStencilCoverOp.cpp` - 路径模板覆盖
- `src/gpu/ganesh/ops/ShadowRRectOp.cpp` - 阴影渲染
- `src/gpu/ganesh/GrClipStack.cpp` - 裁剪路径

### 测试文件
- `tests/DynamicAtlasTest.cpp` - 动态图集单元测试
