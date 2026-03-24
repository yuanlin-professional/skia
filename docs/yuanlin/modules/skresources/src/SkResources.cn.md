# SkResources 实现 - 资源加载与解码

> 源文件: `modules/skresources/src/SkResources.cpp`

## 概述

SkResources.cpp 是 skresources 模块的实现文件，提供了 ImageAsset、MultiFrameImageAsset、FileResourceProvider、ResourceProviderProxyBase、CachingResourceProvider 和 DataURIResourceProviderProxy 等资源加载类的具体实现。核心功能包括多帧动画图片的解码与缓存、基于文件系统的资源加载、线程安全的图片缓存、以及 Data URI（base64 编码）资源的解码。

## 架构位置

该文件是 skresources 模块的实现层，为 SkResources.h 中声明的接口提供完整实现。它连接了 Skia 的图片解码子系统（SkCodec/SkAnimCodecPlayer）和上层的动画/富媒体模块。

## 主要类与结构体

### `VideoAsset`（内部类，条件编译）
仅在 `HAVE_VIDEO_DECODER` 定义时可用，基于 FFmpeg 的视频资源实现：
- 使用 SkVideoDecoder 进行视频解码
- 维护两帧滑动窗口用于时间戳范围查找
- 支持向后 seek（通过完全 rewind）

### 其他主要类的实现详见 SkResources.h 文档。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `ImageAsset::getFrame(t)` | 默认返回 nullptr |
| `ImageAsset::getFrameData(t)` | 默认调用 getFrame()，使用 Linear/Nearest 采样 |
| `MultiFrameImageAsset::Make(data/codec, strategy)` | 创建多帧图片资源 |
| `MultiFrameImageAsset::isMultiFrame()` | 判断动画时长是否 > 0 |
| `MultiFrameImageAsset::getFrame(t)` | 获取帧（静态图片使用缓存） |
| `FileResourceProvider::Make(base_dir, strategy)` | 创建文件资源提供器 |
| `FileResourceProvider::load(path, name)` | 从文件系统加载数据 |
| `CachingResourceProvider::loadImageAsset(...)` | 带缓存的图片加载 |
| `DataURIResourceProviderProxy::loadImageAsset(...)` | 支持 base64 图片加载 |
| `DataURIResourceProviderProxy::loadTypeface(...)` | 支持 base64 字体加载 |

## 内部实现细节

### MultiFrameImageAsset 帧生成（`generateFrame`）
1. 调用 `fPlayer->seek()` 定位到目标时间（毫秒）
2. 获取帧图像
3. 如果策略为 PreDecode 且图像是延迟生成的：
   - 超过 2048x2048（4M 像素）：缩放后解码
   - 否则：直接强制解码为光栅图像
4. 静态图片的帧会被缓存在 `fCachedFrame` 中

### 文件资源加载（FileResourceProvider）
- `Make` 验证目录存在性（`sk_isdir`）
- `load` 使用 `SkOSPath::Join` 拼接路径
- `loadImageAsset` 优先尝试 MultiFrameImageAsset，如果有视频解码器则回退到 VideoAsset

### Data URI 解码（`decode_datauri`）
解析 `data:image/<type>;base64,<data>` 或 `data:font/<type>;base64,<data>` 格式的 URI：
1. 验证 URI 前缀
2. 查找 `;base64,` 编码标记
3. 使用 `SkBase64::Decode` 进行两次调用：第一次计算大小，第二次实际解码

### 缓存资源提供器（CachingResourceProvider）
- 使用 `SkAutoMutexExclusive` 保证线程安全
- 以 resource_id 为键缓存 ImageAsset
- 缓存命中直接返回，未命中时调用父类加载并缓存

### ResourceProviderProxyBase 转发
所有 load/loadImageAsset/loadTypeface/loadFont/loadAudioAsset 方法都执行空指针检查后转发给 `fProxy`。

### VideoAsset 滑动窗口（条件编译）
- 维护 `fWindow[2]` 两帧窗口
- 向前 seek：逐帧推进直到目标时间落入窗口
- 向后 seek：需要完全 rewind 后重新推进
- 使用 `SkTPin` 将时间钳位到 `[0, duration]`

### Data URI 格式支持
支持的 Data URI 格式：
- 图片: `data:image/<type>;base64,<base64data>`
  - 例如: `data:image/png;base64,iVBORw0KGgo...`
  - 支持任何已注册的 SkCodec 格式（PNG, JPEG, WebP 等）
- 字体: `data:font/<type>;base64,<base64data>`
  - 例如: `data:font/ttf;base64,AAEAAAARAQAA...`
  - 需要提供 SkFontMgr 来处理字体数据

### decode_datauri 函数详解
该函数解析 Data URI 的两阶段流程：
1. 验证 URI 是否以指定前缀开头（如 "data:image/" 或 "data:font/"）
2. 在前缀之后查找 ";base64," 编码标记
3. 提取 base64 数据部分
4. 第一次 `SkBase64::Decode` 调用：传入 nullptr 目标，仅计算解码后大小
5. 分配 `SkData::MakeUninitialized(dataLen)` 缓冲区
6. 第二次 `SkBase64::Decode` 调用：实际执行解码
7. 任何步骤失败返回 nullptr

### VideoAsset 条件编译
仅在 `HAVE_VIDEO_DECODER` 宏定义时可用，依赖 FFmpeg：
- 使用 `SkVideoDecoder` 进行视频解码
- 两帧滑动窗口 `fWindow[2]` 维护当前帧区间
- `advance()`: 推进窗口，将当前帧移到前一帧位置，解码下一帧
- `getFrame(t)`: 使用 `SkTPin` 钳位时间，向后 seek 需要完全 rewind

## 依赖关系

- **SkCodec / SkAnimCodecPlayer**: 图片解码和多帧播放
- **SkData / SkImage**: 数据容器和图片类型
- **SkBase64**: Base64 编解码
- **SkOSFile / SkOSPath**: 文件系统操作
- **SkFontMgr**: 字体创建（DataURI 代理）
- **SkBitmap**: 像素缓冲区（预解码路径）
- **SkTPin**: 值钳位工具
- **SkVideoDecoder**: 视频解码（可选，需 FFmpeg）

## 设计模式与设计决策

1. **缓存策略**: MultiFrameImageAsset 对静态图片缓存帧结果，CachingResourceProvider 对所有图片资源按 ID 缓存。
2. **代理链**: DataURIResourceProviderProxy -> ResourceProviderProxyBase -> 实际 Provider，形成责任链。
3. **条件编译扩展**: VideoAsset 通过 `HAVE_VIDEO_DECODER` 宏条件编译，不增加无视频需求场景的依赖。
4. **大图保护**: 4M 像素阈值避免解码超大图片导致的内存问题。

## 性能考量

- **静态图片缓存**: `fCachedFrame` 确保静态图片只解码一次
- **预解码与大图缩放**: `kMaxArea = 2048*2048`，超出时缩放而非直接解码
- **线程安全缓存**: CachingResourceProvider 使用 mutex 保护，适合多线程动画播放
- **延迟解码**: `kLazyDecode` 策略将解码推迟到光栅化时，减少动画加载时间
- **Base64 两遍解码**: 第一遍计算大小避免过度分配

## 相关文件

- `modules/skresources/include/SkResources.h` - 公共接口定义
- `modules/skresources/src/SkAnimCodecPlayer.h` - 动画编解码播放器
- `include/codec/SkCodec.h` - 图片编解码接口
- `src/base/SkBase64.h` - Base64 编解码
- `src/utils/SkOSPath.h` - 路径工具

## 使用注意事项

1. MultiFrameImageAsset 对静态图片缓存帧，多帧动画每次 seek 都重新获取
2. 预解码策略下超大图片（>4M 像素）会自动缩放，可能导致画质损失
3. Data URI 仅支持 base64 编码，不支持其他编码方式
4. FileResourceProvider 的路径拼接使用 `SkOSPath::Join`，注意路径分隔符兼容性
5. CachingResourceProvider 的缓存无大小限制，大量图片可能导致内存增长
6. VideoAsset 向后 seek 需要完全 rewind 解码器，性能较差
7. ResourceProviderProxyBase 的所有方法在 fProxy 为空时安全返回 nullptr

### 多帧动画处理
MultiFrameImageAsset 的帧获取逻辑：
- 静态图片（`duration <= 0`）：首次调用后缓存帧，后续直接返回缓存
- 动画图片（`duration > 0`）：每次 `getFrame(t)` 都调用 `generateFrame(t)` 重新获取
- 时间参数 `t` 单位为秒，内部乘以 1000 转为毫秒传给 `SkAnimCodecPlayer::seek()`

### 图片预解码的大小策略
当 `fStrategy == kPreDecode` 时的处理逻辑：
- 图片面积 <= 4M 像素: 调用 `makeRasterImage(nullptr)` 直接解码
- 图片面积 > 4M 像素: 计算缩放因子 `sqrt(kMaxArea / image_area)`，缩放后解码
- 缩放使用 `SkFilterMode::kLinear + SkMipmapMode::kNearest` 采样
