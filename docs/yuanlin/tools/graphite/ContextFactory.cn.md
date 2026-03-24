# ContextFactory

> 源文件
> - tools/graphite/ContextFactory.h
> - tools/graphite/ContextFactory.cpp

## 概述

ContextFactory 是 Skia Graphite 测试框架的核心组件,负责创建和管理不同后端的 GPU 上下文。该工厂类支持多种 GPU 后端(Metal、Vulkan、Dawn),并提供上下文的延迟创建和复用机制,用于简化测试代码中的上下文管理。

核心功能:
- 按需创建 Graphite Context 实例
- 缓存已创建的上下文,避免重复初始化
- 支持多种 GPU 后端(Metal、Vulkan、Dawn D3D11/D3D12/Metal/Vulkan/OpenGL/OpenGLES)
- 管理上下文生命周期,确保 GPU 工作完成后再销毁
- 提供测试选项配置

## 架构位置

```
skia/
├── include/gpu/graphite/
│   ├── Context.h              # Graphite Context 核心接口
│   ├── ContextOptions.h       # 上下文选项
│   └── GraphiteTypes.h        # Graphite 类型定义
├── src/gpu/graphite/
│   ├── Caps.h                 # GPU 能力查询
│   └── ContextPriv.h          # Context 内部接口
├── tools/
│   ├── gpu/ContextType.h      # 上下文类型枚举
│   └── graphite/
│       ├── ContextFactory.h          # 本模块头文件
│       ├── ContextFactory.cpp        # 本模块实现
│       ├── GraphiteTestContext.h     # 测试上下文抽象
│       ├── TestOptions.h             # 测试选项
│       ├── dawn/GraphiteDawnTestContext.h
│       ├── mtl/GraphiteMtlTestContext.h
│       └── vk/GraphiteVulkanTestContext.h
└── tests/                     # 测试代码
```

在测试架构中的位置:
- 为测试提供统一的上下文创建接口
- 隔离不同后端的创建细节
- 支持测试框架的参数化测试

## 主要类与结构体

### ContextInfo
```cpp
struct ContextInfo {
    GraphiteTestContext* fTestContext = nullptr;       // 测试上下文
    skgpu::graphite::Context* fContext = nullptr;      // Graphite 上下文
};
```
返回给测试代码的轻量级上下文信息,包含测试上下文和 Graphite 上下文的裸指针。

### ContextFactory
```cpp
class ContextFactory
```
上下文工厂类,负责创建和管理 GPU 上下文。

**主要成员**:
- `fContexts`: 已创建的上下文数组
- `fOptions`: 测试选项配置

**核心方法**:
- `ContextFactory(const TestOptions&)`: 带选项的构造函数
- `getContextInfo(skgpu::ContextType)`: 获取或创建指定类型的上下文

**特性**:
- 禁止拷贝构造和赋值
- 使用默认析构函数

### OwnedContextInfo
```cpp
struct OwnedContextInfo {
    skgpu::ContextType fType;                                    // 上下文类型
    std::unique_ptr<GraphiteTestContext> fTestContext;          // 测试上下文(拥有)
    std::unique_ptr<skgpu::graphite::Context> fContext;         // Graphite 上下文(拥有)
};
```
内部数据结构,使用 `unique_ptr` 管理上下文的所有权。

**特性**:
- 支持移动语义
- 析构时确保 GPU 工作完成
- 与 `ContextInfo` 数据相同但语义不同(所有权 vs 引用)

## 公共 API 函数

### 构造函数
```cpp
explicit ContextFactory(const TestOptions& options)
ContextFactory() = default
```
**功能**: 创建工厂实例
**参数**:
- `options`: 测试选项,包含 Dawn 特定配置等

### getContextInfo()
```cpp
ContextInfo getContextInfo(skgpu::ContextType type)
```
**功能**: 获取指定类型的上下文,如果不存在则创建
**参数**:
- `type`: 上下文类型枚举(kMetal、kVulkan、kDawn_D3D12 等)

**返回值**:
- 成功: 包含有效指针的 `ContextInfo`
- 失败: 指针为 `nullptr` 的空 `ContextInfo`

**行为**:
1. 检查选项兼容性(如非 Dawn 后端不能使用 Dawn 选项)
2. 查找已缓存的上下文
3. 如果不存在,创建新上下文并缓存
4. 返回上下文信息

## 内部实现细节

### 上下文创建流程
```cpp
ContextInfo ContextFactory::getContextInfo(skgpu::ContextType type) {
    // 1. 验证选项
    if (!skgpu::IsDawnBackend(type) && fOptions.hasDawnOptions()) {
        return {};  // Dawn 选项仅用于 Dawn 后端
    }

    // 2. 查找缓存
    for (const OwnedContextInfo& ctxInfo : fContexts) {
        if (ctxInfo.fType == type) {
            return AsContextInfo(ctxInfo);  // 复用已有上下文
        }
    }

    // 3. 创建测试上下文
    std::unique_ptr<GraphiteTestContext> testCtx;
    switch (type) {
        case skgpu::ContextType::kMetal:
            testCtx = graphite::MtlTestContext::Make();
            break;
        case skgpu::ContextType::kVulkan:
            testCtx = graphite::VulkanTestContext::Make();
            break;
        case skgpu::ContextType::kDawn_D3D12:
            testCtx = graphite::DawnTestContext::Make(wgpu::BackendType::D3D12);
            break;
        // ... 其他 Dawn 后端
    }

    // 4. 创建 Graphite Context
    std::unique_ptr<skgpu::graphite::Context> context = testCtx->makeContext(fOptions);

    // 5. 缓存并返回
    fContexts.push_back({type, std::move(testCtx), std::move(context)});
    return AsContextInfo(fContexts.back());
}
```

### Dawn 后端的宏技巧
使用条件编译宏简化多个 Dawn 后端的处理:
```cpp
#ifdef SK_DAWN
#define CASE(TYPE)                                                          \
    case skgpu::ContextType::kDawn_##TYPE:                                  \
        testCtx = graphite::DawnTestContext::Make(wgpu::BackendType::TYPE); \
        break;
#else
#define CASE(TYPE)                         \
    case skgpu::ContextType::kDawn_##TYPE: \
        break;  // Dawn 未启用时空实现
#endif

CASE(D3D11)
CASE(D3D12)
CASE(Metal)
CASE(Vulkan)
CASE(OpenGL)
CASE(OpenGLES)
#undef CASE
```

### 上下文销毁保护
```cpp
ContextFactory::OwnedContextInfo::~OwnedContextInfo() {
    if (fContext &&
        !fContext->priv().caps()->allowCpuSync() &&
        fContext->hasUnfinishedGpuWork()) {
        fTestContext->syncedSubmit(fContext.get());
        SkASSERT(!fContext->hasUnfinishedGpuWork());
    }
}
```
**关键逻辑**:
- 检查上下文是否支持 CPU 同步
- 如果不支持且有未完成的 GPU 工作,强制同步
- 确保销毁前所有 GPU 操作完成,避免崩溃

### 所有权转换
```cpp
ContextInfo ContextFactory::AsContextInfo(const OwnedContextInfo& owned) {
    return ContextInfo{owned.fTestContext.get(), owned.fContext.get()};
}
```
将拥有所有权的 `OwnedContextInfo` 转换为不拥有所有权的 `ContextInfo`,用于返回给外部。

## 依赖关系

### Graphite 核心
- `skgpu::graphite::Context`: Graphite GPU 上下文
- `skgpu::graphite::ContextOptions`: 上下文创建选项
- `skgpu::graphite::Caps`: GPU 能力查询
- `skgpu::graphite::ContextPriv`: 上下文内部接口

### 测试框架
- `GraphiteTestContext`: 测试上下文抽象基类
- `TestOptions`: 测试选项配置
- `skgpu::ContextType`: 上下文类型枚举(跨 Ganesh 和 Graphite)

### 后端实现
- `GraphiteDawnTestContext`: Dawn 后端测试上下文
- `GraphiteMtlTestContext`: Metal 后端测试上下文
- `GraphiteVulkanTestContext`: Vulkan 后端测试上下文

### 标准库
- `std::unique_ptr`: 智能指针管理所有权
- `skia_private::TArray`: Skia 的动态数组

## 设计模式与设计决策

### 工厂模式
核心设计模式,隔离对象创建细节:
```cpp
ContextInfo getContextInfo(skgpu::ContextType type)
```
根据类型参数创建相应的后端上下文。

### 单例缓存模式
每种类型的上下文只创建一次:
```cpp
for (const OwnedContextInfo& ctxInfo : fContexts) {
    if (ctxInfo.fType == type) {
        return AsContextInfo(ctxInfo);  // 复用
    }
}
```
**优点**: 避免重复初始化 GPU 资源,提高测试效率

### RAII 资源管理
使用 `unique_ptr` 自动管理资源生命周期:
```cpp
std::unique_ptr<GraphiteTestContext> fTestContext;
std::unique_ptr<skgpu::graphite::Context> fContext;
```
析构函数自动释放资源,无需手动管理。

### 所有权分离设计
- **内部**: `OwnedContextInfo` 使用 `unique_ptr` 拥有所有权
- **外部**: `ContextInfo` 使用裸指针,不拥有所有权

这避免了外部代码意外释放资源。

### 策略模式变体
不同后端使用不同的 `GraphiteTestContext` 子类:
- `MtlTestContext::Make()` - Metal 策略
- `VulkanTestContext::Make()` - Vulkan 策略
- `DawnTestContext::Make(backendType)` - Dawn 策略

### 延迟初始化
上下文仅在首次请求时创建:
```cpp
if (!testCtx) {
    return ContextInfo{};  // 创建失败
}
```
避免了预创建所有可能的上下文。

### 防御式编程
多层验证确保健壮性:
1. 选项兼容性检查
2. 测试上下文创建检查
3. Graphite 上下文创建检查
4. 销毁时的 GPU 工作完成检查

## 性能考量

### 上下文复用
```cpp
for (const OwnedContextInfo& ctxInfo : fContexts) {
    if (ctxInfo.fType == type) {
        return AsContextInfo(ctxInfo);
    }
}
```
**优势**: 避免重复 GPU 初始化,大幅提升测试速度
**开销**: 线性查找,但测试场景下上下文数量很少(< 10)

### 延迟创建
仅创建实际使用的上下文:
- 如果测试只用 Vulkan,不会创建 Metal 上下文
- 减少测试启动时间

### GPU 同步开销
```cpp
if (!fContext->priv().caps()->allowCpuSync()) {
    fTestContext->syncedSubmit(fContext.get());
}
```
销毁时的同步可能阻塞,但对于测试可接受。

### 内存占用
每个上下文可能占用大量 GPU 资源:
- 驱动程序内部状态
- 着色器缓存
- 命令缓冲区

因此复用机制尤为重要。

## 相关文件

### Graphite 核心
- `include/gpu/graphite/Context.h`: Graphite 上下文主接口
- `include/gpu/graphite/ContextOptions.h`: 上下文配置选项
- `src/gpu/graphite/Caps.h`: GPU 能力查询
- `src/gpu/graphite/ContextPriv.h`: 上下文私有接口

### 测试框架
- `tools/graphite/GraphiteTestContext.h`: 测试上下文抽象
- `tools/graphite/TestOptions.h`: 测试选项
- `tools/gpu/ContextType.h`: 上下文类型枚举

### 后端实现
- `tools/graphite/dawn/GraphiteDawnTestContext.h`: Dawn 后端
- `tools/graphite/mtl/GraphiteMtlTestContext.h`: Metal 后端
- `tools/graphite/vk/GraphiteVulkanTestContext.h`: Vulkan 后端

### 测试用途
- `tests/`: 使用工厂创建上下文进行单元测试
- `gm/`: GM 测试使用工厂运行不同后端
- `dm/`: DM 测试框架集成
