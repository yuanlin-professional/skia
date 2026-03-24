# GrExternalTextureGenerator

> 源文件: `include/gpu/ganesh/GrExternalTextureGenerator.h`

## 概述
GrExternalTextureGenerator 是一个抽象基类,允许应用程序实现延迟纹理生成策略,在需要时才从外部源动态创建 GPU 纹理。该模块为视频解码、远程纹理提供商、加密内容等场景提供了灵活的纹理生成机制,避免了预先分配 GPU 资源的开销。

## 架构位置
该文件位于 Ganesh GPU 后端的纹理管理子系统,继承自 GrTextureGenerator 基类。它与 SkImage 延迟加载机制紧密集成,为需要按需生成纹理的高级应用场景提供扩展点。

## 主要类与结构体

### GrExternalTexture (抽象基类)
```cpp
class GrExternalTexture {
public:
    virtual ~GrExternalTexture() = default;
    virtual GrBackendTexture getBackendTexture() = 0;
    virtual void dispose() = 0;
};
```

**职责**: 封装外部创建的 GPU 纹理及其生命周期管理

**关键方法**:

#### `getBackendTexture()`
- **功能**: 返回底层的 GPU 后端纹理对象
- **返回值**: GrBackendTexture - 平台无关的纹理句柄
- **调用时机**: Ganesh 需要访问纹理数据时

#### `dispose()`
- **功能**: 释放外部纹理资源
- **调用时机**: SkImage 不再需要该纹理时
- **实现责任**: 子类负责调用平台特定的纹理释放 API

**设计意图**:
- 支持多种纹理来源(硬件视频解码器、远程 GPU、加密媒体)
- 延迟资源分配,仅在实际渲染时创建纹理
- 允许应用程序完全控制纹理生命周期

### GrExternalTextureGenerator (抽象基类)
```cpp
class SK_API GrExternalTextureGenerator : public GrTextureGenerator {
public:
    explicit GrExternalTextureGenerator(const SkImageInfo& info);

    GrSurfaceProxyView onGenerateTexture(GrRecordingContext*,
                                         const SkImageInfo&,
                                         skgpu::Mipmapped,
                                         GrImageTexGenPolicy) override;

    virtual std::unique_ptr<GrExternalTexture> generateExternalTexture(
        GrRecordingContext*,
        skgpu::Mipmapped) = 0;
};
```

**继承关系**: GrTextureGenerator → GrExternalTextureGenerator

**关键成员函数**:

#### 构造函数
```cpp
explicit GrExternalTextureGenerator(const SkImageInfo& info);
```
- **参数**: info - 图像信息(尺寸、颜色类型、Alpha 类型、色彩空间)
- **用途**: 初始化生成器的元数据,无需立即创建纹理

#### `onGenerateTexture` (重写自基类)
```cpp
GrSurfaceProxyView onGenerateTexture(
    GrRecordingContext* context,
    const SkImageInfo& info,
    skgpu::Mipmapped mipmapped,
    GrImageTexGenPolicy policy) override;
```
- **功能**: Ganesh 内部调用以获取纹理代理视图
- **实现**: 调用 generateExternalTexture,然后封装为 GrSurfaceProxyView
- **参数**:
  - `context`: GPU 录制上下文
  - `info`: 请求的图像信息
  - `mipmapped`: 是否需要 mipmap 层级
  - `policy`: 纹理生成策略(预算、缓存等)
- **返回值**: GrSurfaceProxyView - Ganesh 内部纹理视图

#### `generateExternalTexture` (纯虚函数)
```cpp
virtual std::unique_ptr<GrExternalTexture> generateExternalTexture(
    GrRecordingContext* context,
    skgpu::Mipmapped mipmapped) = 0;
```
- **功能**: 子类实现的核心方法,创建外部纹理
- **参数**:
  - `context`: GPU 录制上下文,用于分配 GPU 资源
  - `mipmapped`: 是否需要 mipmap
- **返回值**: 唯一指针指向 GrExternalTexture 实现
- **失败处理**: 返回 nullptr 表示生成失败

**典型实现示例**:
```cpp
class VideoTextureGenerator : public GrExternalTextureGenerator {
    std::unique_ptr<GrExternalTexture> generateExternalTexture(
        GrRecordingContext* context,
        skgpu::Mipmapped mipmapped) override {
        // 1. 从视频解码器获取硬件纹理句柄
        VideoFrame* frame = decoder->getNextFrame();

        // 2. 将硬件句柄包装为 GrBackendTexture
        GrBackendTexture backendTex = wrapHardwareTexture(frame);

        // 3. 返回自定义 GrExternalTexture 实现
        return std::make_unique<VideoExternalTexture>(frame, backendTex);
    }
};
```

## 公共 API 函数 (SkImages 命名空间)

### `DeferredFromTextureGenerator`
```cpp
namespace SkImages {
SK_API sk_sp<SkImage> DeferredFromTextureGenerator(
    std::unique_ptr<GrTextureGenerator> gen);
}
```
- **功能**: 从 GrTextureGenerator(包括 GrExternalTextureGenerator)创建延迟图像
- **参数**: gen - 纹理生成器唯一指针,所有权转移
- **返回值**: sk_sp<SkImage> - 延迟图像对象,失败返回 nullptr
- **延迟加载**: 图像创建时不生成纹理,仅在首次绘制时调用生成器
- **线程安全**: 生成器可能在渲染线程调用,需确保线程安全

**使用场景**:
- 视频播放:每帧按需解码
- 大型纹理集:仅加载可见纹理
- 远程资源:延迟网络请求

## 内部实现细节

### 延迟生成流程
1. 应用创建 GrExternalTextureGenerator 子类实例
2. 通过 DeferredFromTextureGenerator 创建 SkImage
3. SkImage 被添加到 SkCanvas 绘制命令
4. Ganesh 在录制/回放时调用 onGenerateTexture
5. onGenerateTexture 调用 generateExternalTexture
6. 返回的纹理被封装为 GrSurfaceProxyView
7. 纹理用于渲染后,dispose() 被调用

### 缓存策略
- Ganesh 可能缓存生成的纹理代理
- GrImageTexGenPolicy 控制缓存行为
- 缓存命中时不会调用 generateExternalTexture

### 资源追踪
- GrBackendTexture 生命周期由 GrExternalTexture::dispose 管理
- 避免纹理泄漏需正确实现 dispose
- 支持引用计数或其他生命周期管理模式

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | sk_sp 智能指针 |
| include/gpu/ganesh/GrBackendSurface.h | GrBackendTexture 类型 |
| include/private/gpu/ganesh/GrTextureGenerator.h | 基类定义 |
| GrRecordingContext | GPU 上下文 |
| SkImageInfo | 图像元数据 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| 视频播放器 | 硬件解码纹理集成 |
| WebGL/远程渲染 | 跨进程纹理共享 |
| DRM 内容播放 | 加密纹理处理 |
| SkImage | 延迟图像实现 |

## 设计模式与设计决策

### 策略模式
GrExternalTextureGenerator 实现策略模式:
- 定义纹理生成算法族(视频解码、远程获取等)
- 运行时选择生成策略
- 客户端与具体生成逻辑解耦

### 模板方法模式
onGenerateTexture 实现模板方法:
- 定义生成流程框架(调用 generateExternalTexture + 封装)
- 子类实现关键步骤(generateExternalTexture)

### 所有权转移
使用 unique_ptr 确保:
- 明确的所有权语义
- 避免生命周期管理错误
- 支持移动语义优化

## 性能考量

### 延迟加载优势
- 避免预分配不使用的纹理
- 减少初始内存占用
- 支持按需流式加载

### 同步开销
- generateExternalTexture 在渲染线程调用
- 阻塞操作(如解码)会影响帧率
- 考虑异步预生成策略

### 缓存策略
- 合理设置 GrImageTexGenPolicy 避免重复生成
- 缓存命中大幅提升性能
- 平衡缓存大小和生成开销

## 使用示例

### 视频纹理生成器
```cpp
class HardwareVideoTexture : public GrExternalTexture {
    VideoFrame* frame_;
    GrBackendTexture tex_;
public:
    HardwareVideoTexture(VideoFrame* f, GrBackendTexture t)
        : frame_(f), tex_(t) {}

    GrBackendTexture getBackendTexture() override { return tex_; }

    void dispose() override {
        frame_->release();  // 释放视频帧
    }
};

class VideoGenerator : public GrExternalTextureGenerator {
    VideoDecoder* decoder_;
public:
    VideoGenerator(VideoDecoder* d, const SkImageInfo& info)
        : GrExternalTextureGenerator(info), decoder_(d) {}

    std::unique_ptr<GrExternalTexture> generateExternalTexture(
        GrRecordingContext* ctx, skgpu::Mipmapped mipped) override {
        VideoFrame* frame = decoder_->decodeNextFrame();
        if (!frame) return nullptr;

        GrBackendTexture tex = createBackendTexture(ctx, frame);
        return std::make_unique<HardwareVideoTexture>(frame, tex);
    }
};

// 使用
auto gen = std::make_unique<VideoGenerator>(decoder, info);
auto image = SkImages::DeferredFromTextureGenerator(std::move(gen));
canvas->drawImage(image, 0, 0);  // 此时才解码并创建纹理
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/gpu/ganesh/GrTextureGenerator.h | 基类定义 |
| src/image/SkImage_GaneshFactories.cpp | DeferredFromTextureGenerator 实现 |
| include/gpu/ganesh/GrBackendSurface.h | 后端纹理类型 |
| src/gpu/ganesh/GrSurfaceProxyView.h | 纹理代理视图 |
