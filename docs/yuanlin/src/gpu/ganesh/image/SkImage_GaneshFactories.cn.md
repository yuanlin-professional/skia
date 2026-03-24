# SkImage_GaneshFactories — Ganesh GPU Image 工厂集合

> 源文件: `src/gpu/ganesh/image/SkImage_GaneshFactories.cpp`

## 概述

本文件是 Ganesh GPU 后端中 `SkImage` 创建的核心工厂集合，实现了 `SkImages` 命名空间中的多种图像创建方式。涵盖了从后端纹理借用/收养、压缩纹理、Promise 图像、跨上下文纹理、YUVA 纹理到从现有 SkImage 创建 GPU 纹理等全部场景。这是 Skia 与外部 GPU 纹理交互的主要接口。

## 架构位置

```
SkImages 命名空间（公共 API）
    └── SkImage_GaneshFactories (本文件)
        ├── BorrowTextureFrom / AdoptTextureFrom → SkImage_Ganesh
        ├── TextureFromCompressed* → SkImage_Ganesh
        ├── PromiseTextureFrom → SkImage_Ganesh (延迟代理)
        ├── CrossContextTextureFromPixmap → GrBackendTextureImageGenerator
        ├── TextureFromImage → 转换/重用 SkImage_Ganesh
        ├── TextureFromYUVA* → SkImage_GaneshYUVA
        └── MakeBackendTextureFromImage → 提取 GrBackendTexture
```

## 主要类与结构体

本文件不定义新类，使用以下核心图像类型：

| 类型 | 描述 |
|------|------|
| `SkImage_Ganesh` | 标准 Ganesh GPU 图像 |
| `SkImage_GaneshYUVA` | YUVA 多平面 GPU 图像 |
| `GrBackendTextureImageGenerator` | 跨上下文纹理生成器 |
| `GrYUVATextureProxies` | YUVA 纹理代理集合 |
| `GrMippedBitmap` | 带 mipmap 的位图封装 |

## 公共 API 函数

### 后端纹理提取

**`MakeBackendTextureFromImage()`**: 从 SkImage 中提取 `GrBackendTexture`，转移所有权。若图像非唯一或纹理包装外部对象，先创建拷贝再提取。通过 `GrTexture::StealBackendTexture()` "窃取"底层纹理。

**`GetBackendTextureFromImage()`**: 获取已有纹理的只读引用（不转移所有权），可选刷新待处理 IO。仅支持 `SkImage_Ganesh` 类型。

### 纹理借用与收养

**`BorrowTextureFrom()`**: 从已有后端纹理创建图像，Skia 不拥有纹理。通过 `TextureReleaseProc` 回调通知调用者可以安全释放纹理。

**`AdoptTextureFrom()`** (3 个重载): 从已有后端纹理创建图像，Skia 接管纹理所有权。仅支持 `GrDirectContext`（不支持 DDL 上下文）。

### 压缩纹理

**`TextureFromCompressedTexture()`**: 从已有压缩后端纹理创建图像。

**`TextureFromCompressedTextureData()`**: 从压缩数据创建 GPU 纹理。若后端不支持压缩格式，回退到先解码为光栅图像再上传。

### Promise 图像

**`PromiseTextureFrom()`**: 创建延迟图像，纹理在首次绘制时通过 `textureFulfillProc` 回调获取。保证即使失败也会调用 `textureReleaseProc`。支持线程安全代理。

### 跨上下文纹理

**`CrossContextTextureFromPixmap()`**: 从像素数据创建可跨 GPU 上下文使用的纹理图像。包含像素上传、信号量同步、生成器包装等完整流程。若不支持跨上下文，回退到光栅拷贝。

### 通用转换

**`TextureFromImage()`**: 将任意 SkImage 转换为 GPU 纹理图像。若已是 Ganesh 图像且 mipmap 满足要求，直接返回；否则创建新的 GPU 纹理。

### YUVA 纹理

**`TextureFromYUVATextures()`** (2 个重载): 从 YUVA 后端纹理集合创建图像。包装每个平面纹理为代理，创建 `SkImage_GaneshYUVA`。

**`TextureFromYUVAPixmaps()`** (2 个重载): 从 YUVA 像素数据创建 GPU 图像。上传每个平面到纹理，支持 mipmap 和尺寸限制。

**`PromiseTextureFromYUVA()`**: YUVA 版本的 Promise 图像，为每个平面创建延迟代理。

## 内部实现细节

### new_wrapped_texture_common()

`BorrowTextureFrom` 和 `AdoptTextureFrom` 共享的内部辅助函数。处理后端纹理验证、代理包装、swizzle 计算和 `SkImage_Ganesh` 创建。

### MakeBackendTextureFromImage 的拷贝逻辑

当图像不唯一或纹理包装外部对象时：
1. 通过 `onMakeSubset()` 创建完整图像副本
2. 递归调用自身处理新副本
3. 最终确保纹理唯一后通过 `StealBackendTexture()` 提取

### 跨上下文信号量

`CrossContextTextureFromPixmap` 使用 `prepareTextureForCrossContextUsage()` 创建 GPU 信号量，确保纹理数据在源上下文的操作完成后才能在目标上下文中使用。

### YUVA 像素调整

`TextureFromYUVAPixmaps` 当图像超过最大纹理尺寸时：
- 计算缩放比例
- 分配新的 `SkYUVAPixmaps`
- 使用线性过滤缩放每个平面
- 上传调整后的数据

### Release 回调保证

Promise 图像系列函数保证即使创建失败也会调用 `textureReleaseProc`。空的 release proc 被替换为空 lambda，确保 `RefCntedCallback::Make()` 不会失败。

## 依赖关系

**核心**:
- `src/gpu/ganesh/image/SkImage_Ganesh.h`, `SkImage_GaneshYUVA.h` — 图像实现类
- `src/gpu/ganesh/GrProxyProvider.h` — 纹理代理创建和包装

**纹理管理**:
- `src/gpu/ganesh/GrTexture.h` — GPU 纹理资源
- `src/gpu/ganesh/GrSemaphore.h` — 跨上下文同步
- `src/gpu/ganesh/image/GrMippedBitmap.h` — Mipmap 位图工具

**工具**:
- `src/gpu/ganesh/GrBackendUtils.h` — 后端格式工具
- `src/gpu/ganesh/SkGr.h` — 颜色类型转换
- `src/gpu/RefCntedCallback.h` — 释放回调封装

## 设计模式与设计决策

1. **所有权二分**: `Borrow` vs `Adopt` 清晰区分纹理所有权——借用时 Skia 不删除纹理，收养时 Skia 负责销毁。

2. **渐进式回退**: 多处实现在最优路径失败时提供回退方案：压缩纹理回退到光栅解码+上传，跨上下文回退到像素拷贝。

3. **Promise 图像模式**: 延迟纹理实例化允许在录制绘图命令时不需要实际的 GPU 纹理，适用于 DDL（延迟显示列表）场景。

4. **统一 YUVA 处理**: YUVA 从纹理、像素数据和 Promise 三种来源都统一收敛到 `GrYUVATextureProxies` + `SkImage_GaneshYUVA` 路径。

5. **RefCntedCallback 一致性**: 所有释放回调都通过 `RefCntedCallback` 包装，确保多引用场景下正确的生命周期管理。

## 性能考量

- **TextureFromImage 优化**: 已是 Ganesh 图像且满足 mipmap 要求时直接返回引用，零拷贝。
- **跨上下文信号量**: `CrossContextTextureFromPixmap` 的 GPU 信号量同步可能引入延迟，但保证了数据一致性。
- **尺寸限制缩放**: 超大纹理自动缩放到最大尺寸内，避免 GPU 驱动拒绝分配。
- **Mipmap 按需生成**: 仅在 caps 支持且需要时生成 mipmap，避免不必要的内存和计算开销。
- **YUVA 避免扁平化**: YUVA 图像保持多平面格式，避免预先转换为 RGBA 的内存和带宽开销（但 `TextureFromImage` 中标注了 TODO 来改进此点）。

## 相关文件

- `include/gpu/ganesh/SkImageGanesh.h` — 公共 API 声明
- `src/gpu/ganesh/image/SkImage_Ganesh.h` — Ganesh 图像实现
- `src/gpu/ganesh/image/SkImage_GaneshYUVA.h` — YUVA 图像实现
- `src/gpu/ganesh/image/SkImage_GaneshFactories_Android.cpp` — Android 特化工厂
- `src/gpu/ganesh/GrBackendTextureImageGenerator.h` — 跨上下文纹理生成器
- `src/gpu/ganesh/image/GrImageUtils.h` — 图像到视图转换工具
- `src/gpu/ganesh/GrProxyProvider.h` — 代理创建服务
