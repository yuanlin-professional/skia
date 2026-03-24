# SkImage

> 源文件: `include/core/SkImage.h`

## 概述

SkImage 是 Skia 图形库中表示不可变图像的核心类,封装了二维像素数组的多种存储形式(光栅位图、压缩数据流、GPU纹理或延迟生成器)。它提供了统一的接口用于图像创建、像素访问、颜色空间转换和跨平台渲染,是 Skia 绘图系统中最重要的图像抽象之一。

## 架构位置

SkImage 位于 Skia 核心层 (`include/core`)，是图像管理子系统的顶层抽象。它与 SkBitmap、SkPixmap、SkSurface 等类协作,为上层绘图 API 提供不可变图像语义。SkImage 支持 CPU 光栅化和 GPU 加速两种后端,通过多态机制适配不同的存储策略(光栅、延迟、纹理)。

## 主要类与结构体

### SkImage

**职责**: 表示不可变的二维像素数据,提供图像查询、转换、渲染等操作接口。

**继承关系**: `SkRefCnt` → `SkImage`

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fInfo | SkImageInfo | 图像的宽高、颜色类型、透明度类型和颜色空间信息 |
| fUniqueID | uint32_t | 每个图像实例的唯一标识符,用于缓存和比较 |

### SkImages 命名空间

**职责**: 提供静态工厂方法创建各类 SkImage 实例。

**主要工厂方法类别**:
- **光栅图像创建**: RasterFromBitmap, RasterFromPixmapCopy, RasterFromPixmap
- **延迟解码创建**: DeferredFromEncodedData, DeferredFromGenerator, DeferredFromPicture
- **压缩纹理创建**: RasterFromCompressedTextureData
- **图像过滤创建**: MakeWithFilter

### CachingHint 枚举

**职责**: 控制像素解码或复制时的内部缓存策略。

| 枚举值 | 说明 |
|--------|------|
| kAllow_CachingHint | 允许内部缓存解码的像素数据 |
| kDisallow_CachingHint | 禁止内部缓存,适用于一次性使用场景 |

### RescaleMode 枚举

**职责**: 定义图像缩放时的采样质量。

| 枚举值 | 说明 |
|--------|------|
| kNearest | 最近邻插值,速度最快 |
| kLinear | 线性插值 |
| kRepeatedLinear | 重复线性插值 |
| kRepeatedCubic | 重复三次插值,质量最高 |

### RequiredProperties 结构体

**职责**: 指定操作返回的图像必须具备的属性。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fMipmapped | bool | 是否需要 mipmap 层级 |

## 公共 API 函数

### `const SkImageInfo& imageInfo() const`
- **功能**: 返回图像的完整信息(宽度、高度、颜色类型、透明度类型、颜色空间)
- **返回值**: SkImageInfo 常量引用

### `int width() const` / `int height() const`
- **功能**: 返回图像的像素宽度/高度
- **返回值**: 整数尺寸

### `uint32_t uniqueID() const`
- **功能**: 返回图像的唯一标识符,图像内容不可变保证 ID 唯一性
- **返回值**: 32位无符号整数标识符

### `SkAlphaType alphaType() const`
- **功能**: 返回透明度类型(不透明/预乘/非预乘)
- **返回值**: SkAlphaType 枚举值

### `SkColorSpace* colorSpace() const`
- **功能**: 返回图像关联的颜色空间指针
- **返回值**: 颜色空间指针,可能为 nullptr

### `bool isTextureBacked() const`
- **功能**: 判断图像数据是否存储在 GPU 纹理中
- **返回值**: 纹理支持返回 true,否则返回 false

### `sk_sp<SkShader> makeShader(...)`
- **功能**: 根据图像创建着色器,支持平铺模式和采样选项配置
- **参数**:
  - `tmx/tmy`: X/Y 方向的平铺模式
  - `sampling`: 采样选项(过滤、mipmap)
  - `localMatrix`: 可选的局部变换矩阵
- **返回值**: SkShader 智能指针

### `sk_sp<SkShader> makeRawShader(...)`
- **功能**: 创建原始数据着色器(不应用颜色空间转换),用于法线贴图等非颜色数据
- **参数**: 同 makeShader
- **返回值**: SkShader 智能指针,不支持三次过滤时返回 nullptr

### `bool peekPixels(SkPixmap* pixmap) const`
- **功能**: 尝试直接访问图像像素数据而不复制
- **参数**: `pixmap` - 用于接收像素地址和行字节数的 SkPixmap 指针
- **返回值**: 可直接访问返回 true,否则返回 false

### `bool readPixels(GrDirectContext*, const SkImageInfo&, void*, size_t, int, int, CachingHint) const`
- **功能**: 从图像读取矩形区域像素到目标缓冲区,支持颜色格式转换
- **参数**:
  - `context`: GPU 上下文(GPU 图像需要)
  - `dstInfo`: 目标像素格式信息
  - `dstPixels`: 目标像素缓冲区
  - `dstRowBytes`: 目标行字节数
  - `srcX/srcY`: 源图像起始坐标
  - `cachingHint`: 缓存提示
- **返回值**: 成功返回 true,格式不兼容或参数无效返回 false

### `void asyncRescaleAndReadPixels(...)`
- **功能**: 异步缩放并读取像素数据(在 Ganesh 后端支持 GPU 异步读取)
- **参数**:
  - `info`: 目标像素格式
  - `srcRect`: 源矩形区域
  - `rescaleGamma`: 缩放伽马模式(线性/源)
  - `rescaleMode`: 缩放质量模式
  - `callback`: 完成回调函数
  - `context`: 传递给回调的上下文

### `bool scalePixels(const SkPixmap&, const SkSamplingOptions&, CachingHint) const`
- **功能**: 缩放图像像素到指定的 SkPixmap 目标
- **参数**:
  - `dst`: 目标 SkPixmap(包含格式和缓冲区)
  - `sampling`: 采样选项
  - `cachingHint`: 缓存提示
- **返回值**: 成功返回 true

### `sk_sp<SkImage> makeSubset(SkRecorder*, const SkIRect&, RequiredProperties) const`
- **功能**: 创建图像的子集区域(纯虚函数,由子类实现)
- **参数**:
  - `recorder`: Graphite 录制器(纹理图像需要)
  - `subset`: 子集矩形边界
  - `properties`: 必需的图像属性
- **返回值**: 子集图像智能指针,失败返回 nullptr

### `sk_sp<SkImage> makeColorSpace(SkRecorder*, sk_sp<SkColorSpace>, RequiredProperties) const`
- **功能**: 将图像转换到目标颜色空间(纯虚函数)
- **参数**:
  - `recorder`: Graphite 录制器
  - `targetColorSpace`: 目标颜色空间
  - `properties`: 必需属性
- **返回值**: 转换后的图像

### `sk_sp<SkImage> makeNonTextureImage(GrDirectContext*) const`
- **功能**: 将 GPU 纹理图像复制为 CPU 光栅图像
- **参数**: `context` - GPU 上下文
- **返回值**: 光栅图像或延迟图像

### `sk_sp<SkImage> makeRasterImage(GrDirectContext*, CachingHint) const`
- **功能**: 强制解码为光栅位图(复制 GPU 数据或解码延迟图像)
- **参数**:
  - `context`: GPU 上下文
  - `cachingHint`: 缓存提示
- **返回值**: 光栅图像智能指针

### `bool hasMipmaps() const`
- **功能**: 查询图像是否包含 mipmap 层级
- **返回值**: 包含返回 true

### `sk_sp<SkImage> withDefaultMipmaps() const`
- **功能**: 生成带自动 mipmap 层级的新图像
- **返回值**: 新图像智能指针

### `sk_sp<SkImage> reinterpretColorSpace(sk_sp<SkColorSpace>) const`
- **功能**: 创建具有不同颜色空间解释的新图像(不转换像素数据)
- **参数**: `newColorSpace` - 新的颜色空间
- **返回值**: 重新解释后的图像

## SkImages 命名空间工厂方法

### `RasterFromBitmap(const SkBitmap&)`
- **功能**: 从 SkBitmap 创建 CPU 图像,共享或复制像素
- **参数**: `bitmap` - 源位图
- **返回值**: 创建的图像,失败返回 nullptr
- **验证条件**: 尺寸大于零、颜色类型有效、行字节足够、像素地址非空

### `RasterFromPixmapCopy(const SkPixmap&)`
- **功能**: 从 SkPixmap 复制像素创建 CPU 图像
- **参数**: `pixmap` - 源像素映射
- **返回值**: 像素副本图像

### `RasterFromPixmap(const SkPixmap&, RasterReleaseProc, ReleaseContext)`
- **功能**: 从 SkPixmap 共享像素创建图像,提供释放回调
- **参数**:
  - `pixmap`: 源像素映射
  - `rasterReleaseProc`: 像素释放时的回调函数
  - `releaseContext`: 传递给回调的上下文
- **返回值**: 共享像素的图像

### `RasterFromData(const SkImageInfo&, sk_sp<SkData>, size_t)`
- **功能**: 从原始数据创建图像,不复制数据
- **参数**:
  - `info`: 图像信息
  - `pixels`: 像素数据
  - `rowBytes`: 行字节数
- **返回值**: 共享数据的图像

### `DeferredFromEncodedData(sk_sp<const SkData>, std::optional<SkAlphaType>)`
- **功能**: 从编码数据创建延迟解码图像(首次绘制时解码)
- **参数**:
  - `encoded`: 编码数据(JPEG/PNG/WebP等)
  - `alphaType`: 可选的透明度类型覆盖
- **返回值**: 延迟图像,支持系统缓存
- **说明**: 不强制不透明(kOpaque_SkAlphaType)会返回 nullptr

### `DeferredFromGenerator(std::unique_ptr<SkImageGenerator>)`
- **功能**: 从图像生成器创建延迟图像
- **参数**: `imageGenerator` - 自定义或标准图像生成器
- **返回值**: 延迟图像

### `DeferredFromPicture(sk_sp<SkPicture>, const SkISize&, ...)`
- **功能**: 从 SkPicture 绘图命令创建延迟图像
- **参数**:
  - `picture`: 绘图命令序列
  - `dimensions`: 图像尺寸
  - `matrix`: 可选变换矩阵
  - `paint`: 可选绘制参数
  - `bitDepth`: 位深度(U8/F16)
  - `colorSpace`: 颜色空间
  - `props`: 表面属性
- **返回值**: 延迟渲染图像

### `RasterFromCompressedTextureData(sk_sp<SkData>, int, int, SkTextureCompressionType)`
- **功能**: 解压缩纹理数据创建光栅图像
- **参数**:
  - `data`: 压缩数据
  - `width/height`: 图像尺寸
  - `type`: 压缩类型
- **返回值**: 解压后的光栅图像,丢弃 mipmap 层级

### `MakeWithFilter(sk_sp<SkImage>, const SkImageFilter*, ...)`
- **功能**: 对图像应用滤镜创建新图像
- **参数**:
  - `src`: 源图像
  - `filter`: 图像滤镜
  - `subset`: 处理区域
  - `clipBounds`: 预期输出边界
  - `outSubset`: 输出实际边界
  - `offset`: 输出偏移(用于动画帧对齐)
- **返回值**: 滤镜处理后的图像

## 内部实现细节

### 不可变性保证
SkImage 创建后内容完全不可变,任何修改操作都返回新图像实例。这保证了:
- **多线程安全**: 可在多线程中安全共享引用
- **缓存友好**: uniqueID 可作为缓存键
- **优化机会**: 后端可安全缓存纹理上传结果

### 多态后端架构
SkImage 是抽象基类,核心虚函数包括:
- `isTextureBacked()`: 区分 CPU/GPU 存储
- `isValid()`: 验证上下文有效性
- `makeSubset()`: 子图像创建
- `makeColorSpace()`: 颜色空间转换
- `isLazyGenerated()`: 标识延迟生成

实际子类包括:
- **SkImage_Raster**: CPU 光栅位图
- **SkImage_Lazy**: 延迟解码/生成
- **SkImage_Gpu**: GPU 纹理(Ganesh 后端)
- **SkImage_Graphite**: GPU 纹理(Graphite 后端)

### 像素读取策略
`readPixels` 根据后端类型采用不同路径:
1. **光栅图像**: 直接内存复制并格式转换
2. **GPU 图像**:
   - Ganesh: 通过 `glReadPixels` 或传输缓冲区
   - Graphite: 使用异步 API 避免阻塞
3. **延迟图像**: 先触发解码再读取

### 异步读取机制
`asyncRescaleAndReadPixels` 在 Ganesh 后端:
1. 创建传输缓冲区并发起 GPU 到 CPU 传输
2. 插入栅栏同步原语
3. 回调在传输完成后触发
4. Graphite 后端已迁移到 Context 层的独立 API

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkImageInfo | 定义图像格式元数据 |
| SkRefCnt | 提供引用计数基类 |
| SkPixmap | 像素内存访问抽象 |
| SkBitmap | 光栅位图表示 |
| SkColorSpace | 颜色空间管理 |
| SkData | 原始数据持有 |
| SkImageGenerator | 延迟解码接口 |
| SkPicture | 矢量绘图命令 |
| SkImageFilter | 图像滤镜 |
| SkShader | 着色器生成 |
| GrDirectContext | GPU 上下文(Ganesh) |
| SkRecorder | Graphite 录制器 |

### 被依赖的模块
- **SkCanvas**: 核心绘图 API,通过 `drawImage` 渲染 SkImage
- **SkPaint**: 绘制参数,支持图像着色器
- **SkSurface**: 可渲染表面,能创建图像快照
- **编解码器**: SkCodec 等编解码器输出 SkImage
- **滤镜系统**: SkImageFilter 输入输出均为 SkImage

## 设计模式与设计决策

### 工厂模式
所有创建方法集中在 `SkImages` 命名空间,避免构造函数暴露实现细节:
- 清晰的语义命名(Raster/Deferred/FromBitmap等)
- 统一返回 `sk_sp<SkImage>` 智能指针
- 失败时返回 nullptr 而非异常

### 策略模式
通过 `CachingHint` 和 `RescaleMode` 枚举允许调用者控制性能/质量权衡:
- 缓存策略适应不同内存约束场景
- 缩放模式平衡速度与质量

### 多态与封装
- 纯虚函数隐藏后端实现差异(GPU/CPU/延迟)
- 客户端代码无需关心图像存储位置
- 统一接口支持跨后端迁移

### 不可变对象模式
- 消除数据竞争,简化并发编程
- 支持安全缓存和共享
- 修改操作返回新实例(Copy-on-Write)

## 性能考量

### 零拷贝优化
- `RasterFromPixmap` 和 `RasterFromData` 支持共享像素内存
- `peekPixels` 提供直接访问而不复制
- 位图不可变时 `RasterFromBitmap` 尝试共享

### 延迟计算
- 编码图像延迟解码到首次使用
- Picture 图像延迟光栅化
- 支持系统级 GPU 纹理缓存

### mipmap 管理
- `withDefaultMipmaps` 按需生成 mipmap
- GPU 渲染时自动选择合适层级
- 避免不必要的预生成开销

### 缓存提示
- `kDisallow_CachingHint` 适用于视频帧等一次性数据
- `kAllow_CachingHint` 适用于重复使用的纹理

### 异步读取
- Ganesh 后端通过传输缓冲区减少 GPU 停顿
- 避免同步 `glReadPixels` 导致的流水线刷新

## 平台相关说明

### GPU 后端差异
- **Ganesh (OpenGL/Vulkan/Metal)**:
  - 支持同步 `readPixels`
  - 异步 API 通过传输缓冲区实现
- **Graphite (新架构)**:
  - 弃用同步读取 API
  - 异步 API 移至 `skgpu::graphite::Context`

### 编码格式支持
- **通用格式**: PNG、JPEG、WebP 跨平台支持
- **平台特定**: HEIF 需 iOS/Android 系统支持
- **构建选项**: 需启用 `SK_ENCODE_*` 宏

### 颜色空间处理
- 移动平台默认 sRGB
- HDR 显示需 P3 或 Rec2020 颜色空间
- 线性颜色空间用于物理渲染

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkBitmap.h` | 可变像素容器,可转换为 SkImage |
| `include/core/SkPixmap.h` | 像素内存访问,用于读取/创建图像 |
| `include/core/SkSurface.h` | 可绘制表面,通过 `makeImageSnapshot` 生成图像 |
| `include/core/SkImageInfo.h` | 图像格式元数据定义 |
| `include/core/SkImageGenerator.h` | 延迟图像数据生成接口 |
| `include/core/SkImageFilter.h` | 图像滤镜接口 |
| `include/core/SkCanvas.h` | 图像绘制的主要消费者 |
| `include/core/SkShader.h` | 着色器,可从图像创建 |
| `src/image/SkImage_Base.h` | 内部基类,扩展私有接口 |
| `src/image/SkImage_Raster.cpp` | 光栅图像实现 |
| `src/image/SkImage_Lazy.cpp` | 延迟图像实现 |
