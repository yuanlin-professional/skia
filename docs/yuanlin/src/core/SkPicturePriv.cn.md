# SkPicturePriv

> 源文件
> - src/core/SkPicturePriv.h

## 概述

`SkPicturePriv.h` 定义了 Skia Picture 子系统的内部辅助类 `SkPicturePriv`，提供私有 API 和版本管理功能。该文件是 Picture 序列化版本控制的核心，定义了所有历史版本枚举和版本兼容性范围，确保不同版本的 Skia 能够正确读取和写入 Picture 文件。

该类还提供了访问 Picture 内部实现（如 `SkBigPicture`）和缓存管理的私有接口。

## 架构位置

`SkPicturePriv` 位于 Picture 子系统的内部基础设施层：

- 不是公共 API（位于 `src/core`）
- 被所有 Picture 相关类使用
- 管理版本兼容性
- 提供内部序列化支持

## 主要类与结构体

### SkPicturePriv

静态辅助类，不可实例化。

**所有方法都是静态的**

## 公共 API 函数

### 序列化/反序列化

```cpp
// 从缓冲区创建 Picture
static sk_sp<SkPicture> MakeFromBuffer(SkReadBuffer& buffer);

// 扁平化 Picture 到缓冲区
static void Flatten(const sk_sp<const SkPicture> picture,
                   SkWriteBuffer& buffer);
```

### 内部访问

```cpp
// 获取 SkBigPicture 实现（如果不是则返回 nullptr）
static const SkBigPicture* AsSkBigPicture(
    const sk_sp<const SkPicture>& picture);

// 生成共享 ID（用于资源缓存）
static uint64_t MakeSharedID(uint32_t pictureID);

// 通知 Picture 已添加到缓存
static void AddedToCache(const SkPicture* pic);
```

### 版本枚举

定义了完整的 Picture 格式版本历史：

```cpp
enum Version {
    // v82: Picture 着色器滤镜参数
    kPictureShaderFilterParam_Version = 82,

    // v83: 矩阵图像滤镜采样选项
    kMatrixImageFilterSampling_Version = 83,

    // v84: 图像滤镜采样选项
    kImageFilterImageSampling_Version = 84,

    // v85: 不再从 Paint 继承滤镜质量
    kNoFilterQualityShaders_Version = 85,

    // v86: 移除顶点自定义数据
    kVerticesRemoveCustomData_Version = 86,

    // v87: Paint 中的 SkBlender
    kSkBlenderInSkPaint = 87,

    // v88: 效果中的 Blender
    kBlenderInEffects = 88,

    // v89: 不再支持扩展裁剪操作
    kNoExpandingClipOps = 89,

    // v90: 背景缩放因子
    kBackdropScaleFactor = 90,

    // ... 更多版本（见完整枚举）

    // v109: 工作颜色空间输出控制
    kWorkingColorSpaceOutput = 109,

    // 支持的最小版本
    kMin_Version = kPictureShaderFilterParam_Version,

    // 当前版本
    kCurrent_Version = kWorkingColorSpaceOutput
};
```

## 内部实现细节

### 版本管理

版本枚举记录所有格式变更：

**版本范围**：
- `kMin_Version`：支持的最旧版本
- `kCurrent_Version`：当前写入版本
- 中间所有版本都有明确的变更描述

**版本更新流程**（注释中详细说明）：

1. 查找目标 `kMin_Version` 成为 `kCurrent_Version` 的 git hash
2. 在该时间点查找 SKP 资源版本号
3. （可选）增加 SKP 资源版本并验证
4. 更新 `infra/bots/gen_tasks_logic/gen_tasks_logic.go` 中的 `oldestSupportedSkpVersion`
5. 运行 `make -C infra/bots train`

### 共享 ID 生成

```cpp
static uint64_t MakeSharedID(uint32_t pictureID) {
    uint64_t sharedID = SkSetFourByteTag('p', 'i', 'c', 't');
    return (sharedID << 32) | pictureID;
}
```

生成64位唯一 ID：
- 高32位：'pict' 标签（0x70696374）
- 低32位：Picture ID
- 用于资源缓存键

### 缓存标记

```cpp
static void AddedToCache(const SkPicture* pic) {
    pic->fAddedToCache.store(true);
}
```

标记 Picture 已添加到缓存，触发后续的缓存失效通知。

### SkBigPicture 转换

```cpp
static const SkBigPicture* AsSkBigPicture(
    const sk_sp<const SkPicture>& picture)
{
    return picture->asSkBigPicture();
}
```

安全地获取内部实现，如果不是 `SkBigPicture` 则返回 `nullptr`。

### 版本历史（部分）

| 版本 | 变更 | 描述 |
|-----|------|------|
| v35 | SkRect 头部 | 在头部存储 SkRect 而非宽高 |
| v43 | DRAW_IMAGE | 添加 DRAW_IMAGE 和 DRAW_IMAGE_RECT 操作码 |
| v49 | SkColor4f | 渐变序列化为 SkColor4f + 颜色空间 |
| v50 | SkBlendMode | SkXfermode → SkBlendMode |
| v67 | Blob 字体 | Blob 序列化字体而非 Paint |
| v82 | 滤镜参数 | Picture 着色器滤镜参数 |
| v85 | 采样选项 | 不再从 Paint 继承滤镜质量 |
| v89 | 裁剪操作 | 不再支持扩展裁剪操作 |
| v104 | 多滤镜 | SaveLayer 支持多个图像滤镜 |
| v109 | 颜色空间 | 工作颜色空间输出控制 |

### 流验证

```cpp
bool SkPicture_StreamIsSKP(SkStream* stream, SkPictInfo* info);
```

检查流是否为有效的 SKP 文件（声明但实现在其他文件）。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkPicture | 基类 |
| SkBigPicture | 内部实现类 |
| SkReadBuffer/SkWriteBuffer | 序列化缓冲区 |
| SkStream | 流式 I/O |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| SkPictureData | 使用版本信息 |
| SkPicturePlayback | 检查版本兼容性 |
| SkPictureRecord | 写入当前版本 |
| SkBigPicture | 使用私有 API |

## 设计模式与设计决策

### 静态工具类

所有方法都是静态的：
- 无状态
- 纯工具函数
- 命名空间作用

### 版本枚举驱动

使用枚举管理版本：
- 编译时常量
- 清晰的版本历史
- 便于版本检查

### 向后兼容

维护最小支持版本：
- 旧文件仍可读取
- 平滑版本升级
- 明确的兼容性范围

### 私有 API 隔离

内部功能不暴露给公共 API：
- 封装实现细节
- 保持 API 稳定
- 灵活的内部变更

## 性能考量

### 版本检查开销

版本检查使用整数比较：
- O(1) 时间复杂度
- 编译时优化
- 零运行时开销

### 共享 ID 生成

ID 生成使用位操作：
- 快速的位移和或运算
- 无分配
- 可内联

### 缓存标记

原子布尔标记：
- 单次原子存储
- 无锁操作
- 最小开销

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| include/core/SkPicture.h | Picture 公共接口 |
| src/core/SkBigPicture.h/cpp | Picture 主要实现 |
| src/core/SkPictureData.h/cpp | 数据管理 |
| src/core/SkPicturePlayback.h/cpp | 回放引擎 |
| src/core/SkReadBuffer.h | 反序列化缓冲区 |
| src/core/SkWriteBuffer.h | 序列化缓冲区 |
| infra/bots/gen_tasks_logic/gen_tasks_logic.go | CI 版本配置 |
