# GraphiteDawnToggles

> 源文件
> - tools/graphite/dawn/GraphiteDawnToggles.h
> - tools/graphite/dawn/GraphiteDawnToggles.cpp

## 概述

GraphiteDawnToggles 是 Skia Graphite 测试工具中用于配置 Dawn GPU 后端的模块。该模块提供了 Dawn 实例和适配器的开关(toggles)配置,以及推荐的 GPU 特性列表,用于优化测试性能和行为,使测试环境更接近生产环境。

核心功能:
- 提供 Dawn 实例创建时的开关配置
- 提供 Dawn 适配器创建时的开关配置
- 根据适配器能力添加推荐的 GPU 特性
- 优化测试性能(跳过验证、禁用延迟清除等)
- Debug 模式下启用额外的调试工具

## 架构位置

```
skia/
├── include/gpu/graphite/
│   └── dawn/DawnBackendContext.h    # Dawn 后端上下文
├── tools/graphite/
│   ├── dawn/
│   │   ├── GraphiteDawnToggles.h    # 本模块头文件
│   │   ├── GraphiteDawnToggles.cpp  # 本模块实现
│   │   └── GraphiteDawnTestContext.h
│   └── TestOptions.h
└── third_party/externals/dawn/       # Dawn WebGPU 实现
```

在测试架构中:
- 被 `GraphiteDawnTestContext` 使用
- 配置 Dawn 实例和设备创建
- 优化测试性能和行为

## 主要类与结构体

该模块仅提供工具函数,无类定义。

## 公共 API 函数

### GetInstanceToggles()
```cpp
wgpu::DawnTogglesDescriptor GetInstanceToggles()
```
**功能**: 返回创建 Dawn 实例时的开关配置
**返回值**: `DawnTogglesDescriptor` 对象

**启用的开关**:
- `"allow_unsafe_apis"`: 允许使用未在 WebGPU 中正式发布的新 Dawn API

**用途**: 使用实验性 Dawn 功能

### GetAdapterToggles()
```cpp
wgpu::DawnTogglesDescriptor GetAdapterToggles()
```
**功能**: 返回创建 Dawn 适配器时的开关配置
**返回值**: `DawnTogglesDescriptor` 对象

**Debug 模式开关**:
- `"use_user_defined_labels_in_backend"`: 在后端使用用户定义的标签(用于调试)

**Release 模式开关**:
- `"skip_validation"`: 跳过 API 验证(提升性能)

**通用开关**:
- `"disable_lazy_clear_for_mapped_at_creation_buffer"`: 禁用延迟清除(减少开销)
- `"disable_robustness"`: 禁用健壮性检查(匹配 Chrome 行为)
- `"enable_spirv_validation"`: 启用 SPIR-V 着色器验证

### AddPreferredFeatures()
```cpp
void AddPreferredFeatures(const wgpu::Adapter& adapter,
                          std::vector<wgpu::FeatureName>& features)
```
**功能**: 添加适配器支持的推荐特性到特性列表
**参数**:
- `adapter`: Dawn 适配器对象
- `features`: 输入输出参数,特性列表

**行为**:
- 检查适配器是否支持特定特性
- 如果支持且未在列表中,则添加
- 避免重复添加

**推荐特性列表**:
- `BufferMapExtendedUsages`: 扩展的缓冲区映射用途
- `DawnLoadResolveTexture`: Dawn 加载解析纹理
- `DawnPartialLoadResolveTexture`: Dawn 部分加载解析纹理
- `DawnTexelCopyBufferRowAlignment`: Dawn 纹素拷贝缓冲区行对齐
- `DualSourceBlending`: 双源混合
- `FramebufferFetch`: 帧缓冲区获取
- `ImplicitDeviceSynchronization`: 隐式设备同步
- `MSAARenderToSingleSampled`: MSAA 渲染到单采样
- `ShaderF16`: 着色器 F16 支持
- `TextureCompressionBC`: BC 纹理压缩
- `TextureCompressionETC2`: ETC2 纹理压缩
- `TextureFormatsTier1`: 纹理格式 Tier 1
- `TimestampQuery`: 时间戳查询
- `TransientAttachments`: 瞬态附件
- `Unorm16TextureFormats`: Unorm16 纹理格式
- `RenderPassRenderArea`: 渲染通道渲染区域

## 内部实现细节

### 实例开关实现
```cpp
wgpu::DawnTogglesDescriptor GetInstanceToggles() {
    static constexpr const char* kToggles[] = {
        "allow_unsafe_apis",
    };
    wgpu::DawnTogglesDescriptor togglesDesc;
    togglesDesc.enabledToggleCount = std::size(kToggles);
    togglesDesc.enabledToggles = kToggles;
    return togglesDesc;
}
```
**设计**: 使用静态常量数组,编译时确定

### 适配器开关实现
```cpp
wgpu::DawnTogglesDescriptor GetAdapterToggles() {
    static constexpr const char* kToggles[] = {
#if defined(SK_DEBUG)
        "use_user_defined_labels_in_backend",
#else
        "skip_validation",
#endif
        "disable_lazy_clear_for_mapped_at_creation_buffer",
        "disable_robustness",
        "enable_spirv_validation",
    };
    // ...
}
```
**条件编译**: Debug 和 Release 使用不同的第一个开关

### 特性添加实现
```cpp
void AddPreferredFeatures(const wgpu::Adapter& adapter,
                          std::vector<wgpu::FeatureName>& features) {
    auto addFeature = [&](wgpu::FeatureName feature) {
        if (adapter.HasFeature(feature)) {
            for (auto existing : features) {
                if (existing == feature) {
                    return;  // 避免重复
                }
            }
            features.push_back(feature);
        }
    };

    addFeature(wgpu::FeatureName::BufferMapExtendedUsages);
    addFeature(wgpu::FeatureName::DawnLoadResolveTexture);
    // ... 更多特性
}
```

**去重逻辑**: 线性查找避免重复添加
**效率**: O(n*m),n 为推荐特性数,m 为已有特性数

## 依赖关系

### Dawn/WebGPU
- `webgpu/webgpu_cpp.h`: Dawn C++ 绑定
- `wgpu::DawnTogglesDescriptor`: 开关描述符
- `wgpu::Adapter`: GPU 适配器
- `wgpu::FeatureName`: 特性枚举

### 标准库
- `<vector>`: 动态数组

## 设计模式与设计决策

### 工厂函数模式
```cpp
wgpu::DawnTogglesDescriptor GetInstanceToggles()
wgpu::DawnTogglesDescriptor GetAdapterToggles()
```
提供预配置的对象,隐藏创建细节。

### 策略模式
Debug 和 Release 使用不同的开关策略:
```cpp
#if defined(SK_DEBUG)
    "use_user_defined_labels_in_backend",  // 调试策略
#else
    "skip_validation",                     // 性能策略
#endif
```

### 构建器模式的变体
`AddPreferredFeatures()` 逐步构建特性列表。

### 性能优化决策

**跳过验证** (Release):
```cpp
"skip_validation"
```
- **收益**: 显著提升性能
- **风险**: 可能隐藏 API 使用错误
- **理由**: 测试代码已验证正确

**禁用延迟清除**:
```cpp
"disable_lazy_clear_for_mapped_at_creation_buffer"
```
- **收益**: 减少内存清零开销
- **理由**: 测试通常会立即写入数据

**禁用健壮性**:
```cpp
"disable_robustness"
```
- **收益**: 减少边界检查开销
- **理由**: 匹配 Chrome 生产环境行为

### 调试工具决策

**用户标签** (Debug):
```cpp
"use_user_defined_labels_in_backend"
```
- **用途**: GPU 调试工具显示有意义的对象名称
- **开销**: 额外的字符串存储和传递
- **仅 Debug**: 避免生产环境性能损失

**SPIR-V 验证**:
```cpp
"enable_spirv_validation"
```
- **用途**: 验证 Tint 生成的 SPIR-V 着色器
- **开销**: 验证时间
- **理由**: 虽有开销,但能早期发现着色器问题

## 性能考量

### 验证跳过的影响
Release 模式跳过验证可节省:
- 参数检查
- 状态验证
- 约 10-20% 的 API 调用开销

### 延迟清除的开销
禁用延迟清除避免:
- 首次使用时的内存清零
- 对于大缓冲区可节省毫秒级时间

### 健壮性的成本
禁用健壮性检查节省:
- 数组越界检查
- 除零检查
- 约 5-10% 的着色器执行时间

### 特性查询开销
```cpp
if (adapter.HasFeature(feature))
```
每个特性一次查询,总开销约 14 次查询,微不足道。

### 重复检查的代价
```cpp
for (auto existing : features) {
    if (existing == feature) return;
}
```
线性查找,最坏情况 O(14*m),m 为已有特性数,通常很小。

## 相关文件

### Dawn 集成
- `include/gpu/graphite/dawn/DawnBackendContext.h`: Dawn 后端上下文
- `src/gpu/graphite/dawn/`: Dawn 后端实现

### 测试框架
- `tools/graphite/dawn/GraphiteDawnTestContext.h`: Dawn 测试上下文
- `tools/graphite/TestOptions.h`: 测试选项

### 第三方
- `third_party/externals/dawn/`: Dawn WebGPU 实现

### 参考文档
- Dawn Toggles 文档: https://dawn.googlesource.com/dawn/+/refs/heads/main/docs/dawn/toggles.md
- WebGPU 规范: https://www.w3.org/TR/webgpu/
