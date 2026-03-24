# ImageProvider

> 源文件: `include/gpu/graphite/ImageProvider.h`

## 概述

ImageProvider 是 Graphite 中用于图像缓存和转换的抽象接口类。当 Graphite 遇到非 Graphite 后端的 SkImage 时,会通过 ImageProvider 将其转换为 Graphite 支持的纹理图像。它为客户端提供了一个集中式的图像缓存管理点。

## 架构位置

该文件位于 Skia Graphite GPU 后端的公共接口层 (`skgpu::graphite` 命名空间),是图像资源管理架构的核心组件。它定义了一个可扩展的抽象基类,允许客户端自定义图像转换和缓存策略。

## 主要类与结构体

### ImageProvider

```cpp
class SK_API ImageProvider : public SkRefCnt
```

**职责**: 提供图像转换和缓存的抽象接口,客户端可以派生该类实现自定义的缓存策略。

**继承关系**: `SkRefCnt → ImageProvider`

**关键特性**:
- 抽象基类,需要客户端实现具体的缓存逻辑
- 使用引用计数管理生命周期
- 可在多个 Recorder 间共享(需要客户端处理线程同步)

## 公共 API 函数

### `findOrCreate` (纯虚函数)

```cpp
virtual sk_sp<SkImage> findOrCreate(Recorder* recorder,
                                    const SkImage* image,
                                    SkImage::RequiredProperties) = 0;
```

- **功能**: 查找或创建与给定图像内容相同的 Graphite 后端图像
- **参数**:
  - `recorder` - Graphite Recorder 对象,用于创建和上传
  - `image` - 源图像对象
  - `RequiredProperties` - 要求的图像属性(如 mipmap)
- **返回值**: Graphite 后端的 SkImage,如果失败返回 nullptr
- **实现要求**:
  - 如果已有满足要求的缓存图像,可直接返回
  - 可调用 `makeTextureImage` 创建可接受的 Graphite 图像
  - 返回的图像可以被缓存供后续使用

## 内部实现细节

### 图像属性要求

Skia 要求 `findOrCreate` 返回的 Graphite 图像必须满足以下条件:

1. **尺寸和透明度类型**: 必须与原始图像相同
2. **通道要求**: 返回的图像必须包含原始图像通道的超集
   - 例如: 565 → 8888 opaque 是允许的
3. **位深度**: 可以改变,例如 4444 → 8888
4. **Mipmap 灵活性**:
   - 如果请求 mipmap 但未返回,采样级别会降级为 linear
   - 如果返回的图像不满足要求(除 mipmap 外),Graphite 会丢弃绘制操作

### 纹理原点要求

所有返回的图像必须由 TopLeft 原点的纹理支持:
- 使用 Skia API(如 `makeTextureImage`)创建的纹理自动保证这一点
- 客户端自行创建并包装的纹理必须确保是 TopLeft 原点

### 默认行为

注意: 默认情况下,Graphite 不执行任何图像缓存。客户端需要提供 ImageProvider 实现才能启用缓存。

## 线程安全与同步

### 多 Recorder 场景

如果同一个 ImageProvider 被多个 Recorder 使用:

1. **客户端责任**:
   - 需要处理所有必要的线程同步
   - 不仅限于缓存 map 的访问同步
   - 还包括确保图像创建工作已提交

2. **跨 Recorder 使用**:
   - 在 Recorder A 上创建的图像在 Recorder B 使用前
   - 必须确保 Recorder A 的创建工作已经提交
   - 这是所有 Graphite SkImage 的通用要求

### 生命周期管理

- ImageProvider 使用 `SkRefCnt` 管理生命周期
- 客户端持有的缓存图像也需要正确管理引用计数
- 关闭顺序问题尚待文档化(TODO: b/240996632)

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkImage.h` | SkImage 基类定义 |
| `include/core/SkRefCnt.h` | 引用计数基础设施 |
| `skgpu::graphite::Recorder` | 前向声明,命令记录器 |

### 被依赖的模块

- Graphite 的图像绘制管线(当遇到非 Graphite 图像时调用)
- 客户端应用程序(实现自定义缓存策略)
- Recorder 实现(集成 ImageProvider)

## 设计模式与设计决策

### 策略模式

ImageProvider 是典型的策略模式应用:
- 定义了图像转换的接口
- 客户端可以提供不同的实现策略
- 解耦了图像转换逻辑与核心渲染管线

### 抽象工厂模式

`findOrCreate` 方法体现了抽象工厂模式:
- 根据给定参数查找或创建对象
- 具体创建逻辑由子类决定
- 支持缓存和复用

### 为什么使用纯虚函数

- 强制客户端提供实现
- Graphite 不提供默认缓存实现,给予客户端最大灵活性
- 不同应用有不同的缓存需求(内存限制、缓存策略等)

## 性能考量

### 缓存策略

客户端实现时需要考虑:
1. **缓存键**: 如何唯一标识图像(内容哈希、指针地址等)
2. **缓存大小**: 内存预算和淘汰策略
3. **命中率**: 平衡缓存大小和命中率
4. **线程安全开销**: 多 Recorder 场景下的锁竞争

### 纹理上传开销

- 首次转换需要纹理上传,开销较大
- 后续使用可直接从缓存获取
- Mipmap 生成也有额外开销

### 推荐实现策略

```cpp
// 伪代码示例
class MyImageProvider : public ImageProvider {
    std::map<ImageKey, sk_sp<SkImage>> fCache;
    std::mutex fMutex;

    sk_sp<SkImage> findOrCreate(Recorder* recorder,
                                const SkImage* image,
                                SkImage::RequiredProperties props) override {
        std::lock_guard lock(fMutex);

        auto key = makeKey(image, props);
        auto it = fCache.find(key);
        if (it != fCache.end()) {
            return it->second;
        }

        auto textureImage = image->makeTextureImage(recorder, props);
        if (textureImage) {
            fCache[key] = textureImage;
        }
        return textureImage;
    }
};
```

## 待解决问题

根据源码注释,以下问题尚待完善:

1. **TODO(b/240996632)**: 添加关于关闭顺序的文档
   - ImageProvider 与 Context/Recorder 的销毁顺序
   - 缓存清理时机

2. **TODO(b/240997067)**: 添加单元测试
   - 多 Recorder 并发场景
   - 生命周期管理
   - 错误处理

## 使用场景示例

### 场景 1: CPU 位图转 GPU 纹理

应用使用 CPU 位图(如解码的 PNG),Graphite 自动通过 ImageProvider 转换为 GPU 纹理。

### 场景 2: 跨后端图像共享

从旧 GPU 后端(ganesh)迁移到 Graphite 时,ImageProvider 可以处理图像转换。

### 场景 3: LRU 缓存实现

实现固定大小的 LRU 缓存,自动淘汰最少使用的纹理图像。

### 场景 4: 多分辨率缓存

根据 RequiredProperties 中的 mipmap 要求,缓存不同 mipmap 级别的版本。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkImage.h` | 基类和接口定义 |
| `include/gpu/graphite/Recorder.h` | 图像创建上下文 |
| `include/gpu/graphite/Context.h` | Context 可设置 ImageProvider |
| `src/gpu/graphite/Image_Graphite.cpp` | Graphite 图像实现 |
| `include/core/SkRefCnt.h` | 引用计数基类 |

## 集成要点

### 设置 ImageProvider

ImageProvider 通常在创建 Recorder 时设置:

```cpp
RecorderOptions options;
options.fImageProvider = sk_make_sp<MyImageProvider>();
auto recorder = context->makeRecorder(options);
```

### 多 Recorder 共享

```cpp
auto provider = sk_make_sp<MyImageProvider>();
recorder1 = context->makeRecorder({.fImageProvider = provider});
recorder2 = context->makeRecorder({.fImageProvider = provider});
// 客户端需要在 MyImageProvider 中处理线程同步
```

### 不使用 ImageProvider

如果不设置 ImageProvider,Graphite 遇到非 Graphite 图像时可能:
- 每次都重新创建纹理(性能差)
- 或者直接丢弃绘制(取决于实现)
