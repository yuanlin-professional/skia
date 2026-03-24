# AtlasProvider

> 源文件
> - src/gpu/graphite/AtlasProvider.h
> - src/gpu/graphite/AtlasProvider.cpp

## 概述

`AtlasProvider` 是 Graphite 渲染系统中统一管理各类纹理图集（Atlas）的核心组件。它负责为文本渲染、路径渲染和裁剪提供不同策略的图集管理器，并维护共享的纹理代理池，确保 GPU 资源的高效复用。

主要职责包括：
- **文本图集管理**：提供持久化的 `TextAtlasManager` 用于字形渲染
- **路径图集管理**：支持 CPU 光栅化和 GPU 计算两种路径覆盖蒙版生成策略
- **裁剪图集管理**：为 `ClipStack` 提供裁剪蒙版图集
- **纹理池管理**：复用图集纹理代理，减少内存分配
- **上传协调**：统一管理所有图集的数据上传任务
- **资源清理**：执行 GPU 资源释放和紧凑化操作

## 架构位置

`AtlasProvider` 位于 Graphite 渲染管线的资源管理层：

```
Graphite Rendering System
└── Recorder (录制器)
    ├── AtlasProvider (本类) ← 图集资源统一入口
    │   ├── TextAtlasManager (文本图集)
    │   ├── RasterPathAtlas (CPU 路径图集)
    │   ├── ComputePathAtlas (GPU 计算路径图集)
    │   └── ClipAtlasManager (裁剪图集)
    ├── DrawContext (使用图集进行绘制)
    └── ResourceProvider (底层资源分配)
```

该类作为图集资源的门面（Facade），隔离了上层绘制逻辑和具体图集实现。

## 主要类与结构体

### AtlasProvider 类

**类定义**：
```cpp
class AtlasProvider final
```

### 关键成员变量

| 类型 | 名称 | 说明 |
|------|------|------|
| `std::unique_ptr<TextAtlasManager>` | `fTextAtlasManager` | 文本字形图集管理器（始终存在） |
| `std::unique_ptr<RasterPathAtlas>` | `fRasterPathAtlas` | CPU 光栅化路径图集 |
| `std::unique_ptr<ClipAtlasManager>` | `fClipAtlasManager` | 裁剪蒙版图集管理器（可选） |
| `std::unordered_map<uint64_t, sk_sp<TextureProxy>>` | `fTexturePool` | 图集纹理代理池，键为尺寸+类型的哈希值 |

### 纹理池键格式

```cpp
uint64_t key = (width << 48) | (height << 32) | (colorType << 16) | identifier
```

- **位 48-63**：宽度（16 位）
- **位 32-47**：高度（16 位）
- **位 16-31**：颜色类型（16 位）
- **位 0-15**：标识符（16 位）

## 公共 API 函数

### 1. 构造与析构

```cpp
explicit AtlasProvider(Recorder* recorder)
~AtlasProvider()
```

**构造逻辑**：
- 创建 `TextAtlasManager`（必需）
- 创建 `RasterPathAtlas`（必需）
- 根据路径渲染策略选择性创建 `ClipAtlasManager`

### 2. 图集访问接口

```cpp
TextAtlasManager* textAtlasManager() const
```
返回文本图集管理器指针（始终非空）。

```cpp
RasterPathAtlas* getRasterPathAtlas() const
```
返回 CPU 光栅化路径图集指针。

```cpp
ClipAtlasManager* getClipAtlasManager() const
```
返回裁剪图集管理器指针（可能为 `nullptr`）。

```cpp
std::unique_ptr<ComputePathAtlas> createComputePathAtlas(Recorder* recorder) const
```
创建临时的 GPU 计算路径图集。如果不支持计算着色器，返回 `nullptr`。

**设计注意**：
- `ComputePathAtlas` 是瞬态对象，每次 `DrawContext` 快照时重置
- 其他图集是持久化对象，跨 `Recording` 保持状态

### 3. 纹理分配

```cpp
sk_sp<TextureProxy> getAtlasTexture(
    Recorder* recorder,
    uint16_t width,
    uint16_t height,
    SkColorType colorType,
    uint16_t identifier,
    bool requireStorageUsage
)
```

**功能**：获取或创建指定规格的图集纹理代理

**参数说明**：
- `width`/`height`：纹理尺寸
- `colorType`：颜色类型（如 `kAlpha_8_SkColorType`）
- `identifier`：标识符，用于区分不同用途的图集
- `requireStorageUsage`：是否需要存储纹理用法（计算着色器写入）

**返回逻辑**：
1. 根据参数计算 64 位哈希键
2. 在 `fTexturePool` 中查找已存在的纹理
3. 如果不存在，创建新的 `TextureProxy`：
   - 存储纹理：`getDefaultStorageTextureInfo()`
   - 采样纹理：`getDefaultSampledTextureInfo()`
4. 将新纹理加入池中并返回

### 4. 上传与同步

```cpp
void recordUploads(DrawContext* dc)
```

**功能**：将所有图集的待上传数据记录到绘制上下文

**执行顺序**：
1. `fTextAtlasManager->recordUploads()`
2. `fRasterPathAtlas->recordUploads()`（如果存在）
3. `fClipAtlasManager->recordUploads()`（如果存在）

**错误处理**：文本图集上传失败会记录错误日志。

### 5. 资源管理

```cpp
void freeGpuResources()
```
释放所有图集的 GPU 资源，包括：
- 清空纹理池
- 调用各图集管理器的 `freeGpuResources()`
- 不影响正在使用的纹理（引用计数保护）

```cpp
void compact()
```
紧凑化操作，清理未使用的图集页面。

```cpp
void invalidateAtlases()
```
失效所有图集缓存，用于处理上传失败等错误情况。

## 内部实现细节

### 裁剪图集的条件创建

```cpp
static bool use_clip_atlas(const Recorder* recorder) {
    return recorder->priv().rendererProvider()->pathRendererStrategy() ==
            PathRendererStrategy::kRasterAtlas;
}
```

仅当使用光栅图集路径渲染策略时才创建裁剪图集，其他策略使用深度缓冲裁剪。

### 纹理创建逻辑

```cpp
auto textureInfo = requireStorageUsage
        ? caps->getDefaultStorageTextureInfo(colorType)
        : caps->getDefaultSampledTextureInfo(colorType,
                                             Mipmapped::kNo,
                                             recorder->priv().isProtected(),
                                             Renderable::kNo);
```

**两种纹理用法**：
- **存储纹理**：可被计算着色器写入（`ComputePathAtlas` 使用）
- **采样纹理**：通过 CPU 上传数据，仅用于着色器采样

### 资源释放策略

```cpp
void AtlasProvider::freeGpuResources() {
    fTextAtlasManager->freeGpuResources();
    if (fRasterPathAtlas) {
        fRasterPathAtlas->freeGpuResources();
    }
    if (fClipAtlasManager) {
        fClipAtlasManager->freeGpuResources();
    }
    fTexturePool.clear();
}
```

**设计安全性**：
- 直接清空纹理池不会导致使用中的纹理被销毁
- 已分配的 `TextureProxy` 通过引用计数保护
- 正在绘制的对象持有纹理引用

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `Recorder` | 提供上下文和能力查询 |
| `Caps` | 查询纹理格式和计算支持 |
| `TextureProxy` | 纹理代理创建 |
| `TextAtlasManager` | 文本字形图集管理 |
| `RasterPathAtlas` | CPU 路径光栅化 |
| `ComputePathAtlas` | GPU 计算路径 |
| `ClipAtlasManager` | 裁剪蒙版管理 |
| `DrawContext` | 上传目标 |
| `RendererProvider` | 路径渲染策略查询 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `Recorder` | 通过 `Recorder::priv().atlasProvider()` 访问 |
| `Device` | 使用图集进行文本和路径绘制 |
| `ClipStack` | 使用裁剪图集 |
| `DrawContext` | 调用 `recordUploads()` |

## 设计模式与设计决策

### 1. 门面模式（Facade Pattern）

`AtlasProvider` 统一管理多种图集，简化上层调用：
```cpp
// 上层代码只需要与 AtlasProvider 交互
atlasProvider->textAtlasManager()->addGlyph(...);
atlasProvider->recordUploads(drawContext);
```

### 2. 对象池模式

`fTexturePool` 实现纹理代理复用：
- 减少纹理分配次数
- 降低内存碎片
- 提高跨帧资源复用率

### 3. 策略模式

路径图集支持多种策略：
- **RasterPathAtlas**：CPU 软光栅化
- **ComputePathAtlas**：GPU 计算着色器
- **选择逻辑**：基于硬件能力和渲染策略

### 4. 资源所有权设计

**持久化图集**（由 `AtlasProvider` 拥有）：
- `TextAtlasManager`
- `RasterPathAtlas`
- `ClipAtlasManager`

**瞬态图集**（由调用者拥有）：
- `ComputePathAtlas`（每次 `DrawContext::snap()` 重新创建）

**理由**：
- 文本和裁剪图集需要跨帧缓存
- 计算路径图集每帧重建，避免同步开销

### 5. 条件编译与可选组件

裁剪图集的创建依赖运行时条件：
```cpp
fClipAtlasManager(use_clip_atlas(recorder) ? std::make_unique<ClipAtlasManager>(recorder)
                                           : nullptr)
```

避免不必要的内存分配。

## 性能考量

### 1. 纹理复用效率

**哈希键设计**：
```cpp
uint64_t key = (width << 48) | (height << 32) | (colorType << 16) | identifier;
```

- **快速计算**：位移和位或操作
- **无哈希冲突**：参数直接编码到键中
- **查找性能**：`std::unordered_map` O(1) 平均复杂度

### 2. 上传批处理

`recordUploads()` 集中处理所有图集上传：
- 减少命令缓冲切换
- 利用 GPU DMA 批量传输
- 提高带宽利用率

### 3. 内存管理

```cpp
void freeGpuResources() {
    // ...
    fTexturePool.clear();
}
```

**紧急释放路径**：
- 在内存压力下快速清空池
- 不影响正在使用的纹理（引用计数保护）

### 4. 计算图集的生命周期

`ComputePathAtlas` 由调用者管理生命周期：
- 避免 `AtlasProvider` 持有跨帧状态
- 减少同步开销（每帧重建）
- 简化并发控制

### 5. 裁剪图集的按需创建

只在需要时创建 `ClipAtlasManager`：
- 节省约 1-2MB 内存
- 避免不必要的图集管理开销
- 支持多种裁剪策略切换

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/text/TextAtlasManager.h` | 组件 | 文本字形图集管理 |
| `src/gpu/graphite/RasterPathAtlas.h` | 组件 | CPU 路径光栅化 |
| `src/gpu/graphite/ComputePathAtlas.h` | 工厂产品 | GPU 计算路径图集 |
| `src/gpu/graphite/ClipAtlasManager.h` | 组件 | 裁剪蒙版图集 |
| `src/gpu/graphite/TextureProxy.h` | 依赖 | 纹理代理 |
| `src/gpu/graphite/Caps.h` | 依赖 | 能力查询 |
| `include/gpu/graphite/Recorder.h` | 上下文 | 录制器公共接口 |
| `src/gpu/graphite/RecorderPriv.h` | 访问器 | 私有接口访问 |
| `src/gpu/graphite/DrawContext.h` | 使用者 | 调用上传接口 |
| `src/gpu/graphite/Device.h` | 使用者 | 使用各类图集 |
| `src/gpu/graphite/RendererProvider.h` | 策略提供者 | 路径渲染策略 |
