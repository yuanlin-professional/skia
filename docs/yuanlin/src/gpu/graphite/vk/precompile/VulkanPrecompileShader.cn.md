# VulkanPrecompileShader

> 源文件：
> - include/gpu/graphite/vk/precompile/VulkanPrecompileShader.h
> - src/gpu/graphite/vk/precompile/VulkanPrecompileShader.cpp

## 概述

`VulkanPrecompileShader` 模块提供了 Skia Graphite 框架中 Vulkan 后端特定的预编译着色器 API，专门用于处理 YCbCr 图像着色器的预编译。该模块允许应用程序在实际渲染前预先编译使用 YCbCr 格式纹理的着色器，从而减少运行时的着色器编译延迟。

这是一个非常小的辅助模块，提供一个工厂函数用于创建 Vulkan 特定的 YCbCr 图像预编译着色器对象。

## 架构位置

该模块位于 Skia Graphite 渲染框架的 Vulkan 后端预编译子系统：

```
skia/
├── include/
│   └── gpu/
│       └── graphite/
│           ├── precompile/
│           │   └── PrecompileShader.h           # 后端无关的预编译接口
│           └── vk/
│               └── precompile/
│                   └── VulkanPrecompileShader.h  # Vulkan YCbCr 预编译 API
└── src/
    └── gpu/
        └── graphite/
            ├── precompile/
            │   └── PrecompileImageShader.h       # 图像着色器预编译实现
            └── vk/
                ├── VulkanYcbcrConversion.h       # YCbCr 转换辅助
                └── precompile/
                    └── VulkanPrecompileShader.cpp # 实现
```

该模块是 Graphite 预编译系统的一部分，与 Metal、Direct3D 等后端的预编译模块平行。

## 主要类与结构体

该模块没有定义类，只提供一个命名空间函数。

### 命名空间函数

所有 API 都在 `skgpu::graphite::PrecompileShaders` 命名空间中定义。

## 公共 API 函数

### YCbCr 图像预编译

| 函数签名 | 说明 |
|---------|------|
| `sk_sp<PrecompileShader> VulkanYCbCrImage(const VulkanYcbcrConversionInfo&, ImageShaderFlags, SkSpan<const SkColorInfo>, SkSpan<const SkTileMode>)` | 为特定 YCbCr 配置创建预编译着色器对象 |

**参数说明：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `YCbCrInfo` | `const VulkanYcbcrConversionInfo&` | 无 | YCbCr 转换配置信息 |
| `shaderFlags` | `ImageShaderFlags` | `kAll` | 着色器标志（如采样、mipmap 等） |
| `colorInfos` | `SkSpan<const SkColorInfo>` | 空 | 可能的颜色信息变体 |
| `tileModes` | `SkSpan<const SkTileMode>` | `{kAllTileModes}` | 可能的平铺模式（clamp、repeat、mirror） |

**返回值：**
- 成功：返回 `sk_sp<PrecompileShader>` 智能指针，包含预编译着色器对象
- 失败：如果 `YCbCrInfo` 无效，返回 `nullptr`

## 内部实现细节

### 函数实现

`VulkanYCbCrImage()` 的完整实现非常简洁：

```cpp
sk_sp<PrecompileShader> PrecompileShaders::VulkanYCbCrImage(
        const skgpu::VulkanYcbcrConversionInfo& YCbCrConversionInfo,
        ImageShaderFlags shaderFlags,
        SkSpan<const SkColorInfo> colorInfos,
        SkSpan<const SkTileMode> tileModes) {
    // 1. 验证 YCbCr 配置有效性
    if (!YCbCrConversionInfo.isValid()) {
        return nullptr;
    }

    // 2. 创建通用图像预编译着色器
    sk_sp<PrecompileImageShader> shader = sk_make_sp<PrecompileImageShader>(
        shaderFlags,
        colorInfos,
        tileModes,
        /* raw= */false  // 不是 raw 图像
    );

    // 3. 设置 YCbCr 不可变采样器信息
    shader->setImmutableSamplerInfo(
        VulkanYcbcrConversion::ToImmutableSamplerInfo(YCbCrConversionInfo));

    // 4. 包装为 LocalMatrix 着色器（支持变换）
    return PrecompileShaders::LocalMatrix({{ std::move(shader) }});
}
```

### 实现步骤解析

#### 步骤 1：有效性检查

```cpp
if (!YCbCrConversionInfo.isValid()) {
    return nullptr;
}
```

- 调用 `VulkanYcbcrConversionInfo::isValid()` 检查配置
- 无效配置包括：未初始化、不支持的格式、无效的转换参数等
- 早期返回避免创建无效的着色器对象

#### 步骤 2：创建基础着色器

```cpp
sk_sp<PrecompileImageShader> shader = sk_make_sp<PrecompileImageShader>(
    shaderFlags,
    colorInfos,
    tileModes,
    /* raw= */false
);
```

- 使用 `PrecompileImageShader` 作为基础，它处理图像采样的通用逻辑
- `shaderFlags` 控制着色器变体（如是否支持 mipmap、立方体贴图等）
- `colorInfos` 和 `tileModes` 定义需要预编译的颜色空间和平铺模式组合
- `raw=false` 表示不是原始图像数据，需要颜色空间转换

#### 步骤 3：设置 YCbCr 采样器

```cpp
shader->setImmutableSamplerInfo(
    VulkanYcbcrConversion::ToImmutableSamplerInfo(YCbCrConversionInfo));
```

- **关键操作**：将 YCbCr 配置转换为不可变采样器信息
- 不可变采样器是 Vulkan 的一个特性，YCbCr 采样器必须在管线创建时固定
- `VulkanYcbcrConversion::ToImmutableSamplerInfo()` 将 Skia 的 YCbCr 配置转换为 Graphite 内部表示
- 这个信息会影响着色器变体的生成和管线布局

#### 步骤 4：包装为变换着色器

```cpp
return PrecompileShaders::LocalMatrix({{ std::move(shader) }});
```

- 使用 `LocalMatrix` 包装器添加局部变换支持
- 即使不使用变换，这也是 Skia 图像着色器的标准结构
- 双层大括号 `{{ }}` 是初始化列表语法，创建包含一个着色器的数组

### YCbCr 背景知识

**YCbCr 是什么？**
- Y：亮度分量（Luminance）
- Cb：蓝色色度分量（Chrominance Blue）
- Cr：红色色度分量（Chrominance Red）
- 常用于视频编码和图像压缩（如 JPEG、视频流）

**Vulkan 中的 YCbCr 处理：**
- Vulkan 提供硬件加速的 YCbCr 到 RGB 转换
- 通过 `VkSamplerYcbcrConversion` 对象配置转换参数
- 需要在管线创建时将采样器设置为不可变（immutable）
- 这就是为什么需要预编译支持

### 与主 API 的对应关系

在主渲染 API 中，YCbCr 图像通常这样创建：

```cpp
// 主 API：运行时创建 YCbCr 图像
auto backendTexture = BackendTextures::MakeVulkan(
    size,
    vulkanTextureInfo  // 包含 YCbCr 信息
);
auto image = SkImages::WrapBackendTexture(backendTexture, ...);
auto shader = image->makeShader(...);
```

预编译 API 允许在不创建实际纹理的情况下预先编译这些着色器：

```cpp
// 预编译 API：提前编译
auto precompileShader = PrecompileShaders::VulkanYCbCrImage(
    ycbcrConversionInfo,
    ImageShaderFlags::kAll
);
precompileContext->precompile(precompileShader);
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/gpu/graphite/precompile/PrecompileShader.h` | 预编译着色器基类和接口 |
| `include/gpu/vk/VulkanTypes.h` | `VulkanYcbcrConversionInfo` 类型定义 |
| `src/gpu/graphite/precompile/PrecompileImageShader.h` | 图像着色器预编译实现 |
| `src/gpu/graphite/vk/VulkanYcbcrConversion.h` | YCbCr 转换辅助函数 |

### 被依赖的模块

该模块主要被以下场景使用：

| 使用者 | 场景 |
|--------|------|
| Skia 应用程序 | 预编译 YCbCr 视频帧着色器 |
| Graphite 预编译系统 | 构建完整的预编译着色器图 |
| 视频播放器集成 | 减少视频播放启动延迟 |
| 相机应用 | 预编译相机预览着色器 |

## 设计模式与设计决策

### 工厂函数模式

使用命名空间自由函数而非类构造函数：
- **优点**：清晰的 API，避免类层次爆炸
- **优点**：易于扩展，添加新的预编译变体不需要修改基类
- **符合 Skia 风格**：Skia 广泛使用工厂函数（如 `SkShaders::Blend()`）

### 参数验证原则

早期失败（fail-fast）：
- 在函数开始立即检查参数有效性
- 返回 `nullptr` 表示失败，而非抛出异常
- 符合 Skia 的 C++ 风格（无异常）

### 后端特定 API 隔离

将 Vulkan 特定 API 放在独立的命名空间和头文件：
- 不污染后端无关的预编译接口
- 使用 Vulkan 后端的应用显式包含该头文件
- 编译隔离，不使用 Vulkan 后端时可以完全排除

### 组合优于继承

不创建 `VulkanYCbCrPrecompileShader` 类，而是组合现有组件：
- 复用 `PrecompileImageShader` 的通用逻辑
- 通过 `setImmutableSamplerInfo()` 定制 YCbCr 特性
- 通过 `LocalMatrix` 包装添加变换支持

### 参数默认值设计

提供合理的默认值：
- `shaderFlags = kAll`：预编译所有可能的变体（安全但可能过度）
- `tileModes = {kAllTileModes}`：覆盖所有平铺模式
- `colorInfos = {}`：空表示使用纹理的颜色空间

这些默认值优先考虑正确性和覆盖率，而非最小化编译时间。

## 性能考量

### 预编译收益

**减少的延迟：**
- 首次使用 YCbCr 纹理时，避免着色器编译卡顿（可能数百毫秒）
- 特别重要对于实时视频和相机应用

**预编译成本：**
- 在应用启动或后台线程中执行
- 时间成本：每个着色器变体数十到数百毫秒
- 内存成本：存储编译后的管线缓存

### 变体数量控制

参数组合可能导致大量变体：
- `ImageShaderFlags` 的多个位组合
- `colorInfos` 的每个元素
- `tileModes` 的每个元素（Clamp, Repeat, Mirror, Decal）

**优化策略：**
- 只预编译应用实际使用的配置
- 使用更具体的 `ImageShaderFlags` 而非 `kAll`
- 限制 `colorInfos` 和 `tileModes` 的数量

### 不可变采样器的影响

YCbCr 采样器设置为不可变：
- **优点**：驱动可以在管线编译时优化采样操作
- **缺点**：每个不同的 YCbCr 配置需要独立的管线
- **影响**：必须为每种 YCbCr 格式（NV12, YV12, P010 等）预编译

### 内存占用

预编译着色器对象本身很轻：
- `PrecompileImageShader` 对象：数十字节
- 主要内存在实际编译后的管线缓存中（每个管线数 KB 到数十 KB）

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/graphite/precompile/PrecompileShader.h` | 基类 | 预编译着色器抽象接口 |
| `src/gpu/graphite/precompile/PrecompileImageShader.h` | 实现基础 | 图像着色器预编译逻辑 |
| `include/gpu/vk/VulkanTypes.h` | 类型定义 | `VulkanYcbcrConversionInfo` 结构体 |
| `src/gpu/graphite/vk/VulkanYcbcrConversion.h` | 辅助工具 | YCbCr 配置转换 |
| `include/gpu/graphite/precompile/PrecompileShaders.h` | 工厂集合 | 所有预编译着色器工厂函数 |
| `src/gpu/graphite/vk/VulkanGraphicsPipeline.cpp` | 管线创建 | 使用不可变采样器信息创建管线 |

## 典型使用场景

### 场景 1：视频播放器预编译

```cpp
// 应用启动时，预编译常见的视频格式着色器
void precompileVideoShaders(PrecompileContext* precompileCtx) {
    // NV12 格式（最常见的视频格式）
    VulkanYcbcrConversionInfo nv12Info;
    nv12Info.fFormat = VK_FORMAT_G8_B8R8_2PLANE_420_UNORM;
    nv12Info.fYcbcrModel = VK_SAMPLER_YCBCR_MODEL_CONVERSION_YCBCR_709;
    nv12Info.fYcbcrRange = VK_SAMPLER_YCBCR_RANGE_ITU_NARROW;
    // ... 其他配置 ...

    auto shader = PrecompileShaders::VulkanYCbCrImage(
        nv12Info,
        ImageShaderFlags::kLinearFilter,  // 只预编译线性过滤
        {},  // 默认颜色空间
        {SkTileMode::kClamp}  // 只使用 clamp 模式
    );

    if (shader) {
        precompileCtx->precompile(shader);
    }
}
```

### 场景 2：相机应用预编译

```cpp
// 相机应用可能使用多种 YCbCr 格式
void precompileCameraShaders(PrecompileContext* precompileCtx) {
    std::vector<VulkanYcbcrConversionInfo> cameraFormats = {
        createYcbcrInfo(VK_FORMAT_G8_B8R8_2PLANE_420_UNORM),  // NV12
        createYcbcrInfo(VK_FORMAT_G8_B8_R8_3PLANE_420_UNORM), // YV12
    };

    for (const auto& format : cameraFormats) {
        auto shader = PrecompileShaders::VulkanYCbCrImage(
            format,
            ImageShaderFlags::kAll  // 预编译所有变体
        );
        if (shader) {
            precompileCtx->precompile(shader);
        }
    }
}
```

### 场景 3：动态预编译

```cpp
// 运行时检测到新的 YCbCr 格式时动态预编译
void onNewVideoFormat(const VulkanYcbcrConversionInfo& format) {
    if (format.isValid() && !isPreviouslyCompiled(format)) {
        auto shader = PrecompileShaders::VulkanYCbCrImage(format);
        if (shader) {
            // 在后台线程预编译
            backgroundThreadPool.enqueue([shader, ctx=precompileContext]() {
                ctx->precompile(shader);
            });
            markAsCompiled(format);
        }
    }
}
```

### 使用注意事项

1. **格式匹配**：预编译的 `VulkanYcbcrConversionInfo` 必须与运行时使用的完全匹配
2. **线程安全**：预编译可以在后台线程执行，但需要正确的同步
3. **错误处理**：检查返回值，无效配置会返回 `nullptr`
4. **平衡策略**：在预编译时间和覆盖率之间找到平衡，不要盲目预编译所有可能组合
