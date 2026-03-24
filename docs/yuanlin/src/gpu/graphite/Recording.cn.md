# Recording

> 源文件: include/gpu/graphite/Recording.h, src/gpu/graphite/Recording.cpp

## 概述

`Recording` 是 Skia Graphite 中封装已记录绘制命令的核心类。它代表了一个完整的命令序列，从 `Recorder` 中生成，随后可以提交到 `Context` 执行。该类负责管理命令列表、资源引用、延迟纹理代理实例化以及完成回调等关键渲染资源。

主要职责：
- 封装一组待提交的绘制命令（TaskList）
- 管理命令执行所需的资源引用
- 处理延迟纹理代理的实例化（volatile 和 non-volatile）
- 支持目标纹理的延迟绑定（deferred target）
- 执行完成回调通知

## 架构位置

`Recording` 在 Graphite 渲染管线中处于命令记录和执行之间的关键位置：

```
渲染流程：
Canvas → Device → Recorder → Recording → Context → CommandBuffer → GPU

详细结构：
Recorder (记录命令)
    ↓ 生成
Recording (命令封装)
    ├── TaskList (命令列表)
    ├── Resource References (资源引用)
    ├── LazyProxyData (延迟代理数据)
    └── Finished Callbacks (完成回调)
    ↓ 提交到
Context (执行命令)
```

## 主要类与结构体

### Recording

封装已记录命令的主类。

**继承关系**
- 无继承关系，final 类
- 不可拷贝，不可移动

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fUniqueID` | `uint32_t` | Recording 唯一标识符 |
| `fRecorderID` | `uint32_t` | 生成该 Recording 的 Recorder ID |
| `fRootTaskList` | `std::unique_ptr<TaskList>` | 根任务列表 |
| `fExtraResourceRefs` | `std::vector<sk_sp<Resource>>` | 额外资源引用 |
| `fNonVolatileLazyProxies` | `std::unordered_set<sk_sp<TextureProxy>>` | 非易失延迟代理集合 |
| `fVolatileLazyProxies` | `std::unordered_set<sk_sp<TextureProxy>>` | 易失延迟代理集合 |
| `fTargetProxyData` | `std::unique_ptr<LazyProxyData>` | 目标代理数据 |
| `fFinishedProcs` | `TArray<sk_sp<RefCntedCallback>>` | 完成回调数组 |

### Recording::LazyProxyData

管理延迟目标纹理代理的内部类。

**继承关系**
- 内部类，无继承

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fTarget` | `sk_sp<Texture>` | 实际目标纹理 |
| `fTargetProxy` | `sk_sp<TextureProxy>` | 目标纹理代理 |

## 公共 API 函数

**析构函数**
```cpp
~Recording();
```
清理资源，将未执行的完成回调标记为失败。

**私有访问器**
```cpp
RecordingPriv priv();
```
提供访问内部实现的接口（通过友元类 `RecordingPriv`）。

## 内部实现细节

### 构造流程

`Recording` 由 `Recorder` 创建：
```cpp
Recording::Recording(uint32_t uniqueID,
                     uint32_t recorderID,
                     std::unique_ptr<LazyProxyData> targetProxyData,
                     TArray<sk_sp<RefCntedCallback>>&& finishedProcs)
        : fUniqueID(uniqueID)
        , fRecorderID(recorderID)
        , fRootTaskList(new TaskList)
        , fTargetProxyData(std::move(targetProxyData))
        , fFinishedProcs(std::move(finishedProcs)) {}
```

### 延迟代理实例化

**Non-volatile 代理**（一次性实例化）：
```cpp
bool RecordingPriv::instantiateNonVolatileLazyProxies(ResourceProvider* resourceProvider) {
    for (const auto& proxy : fRecording->fNonVolatileLazyProxies) {
        if (!proxy->lazyInstantiate(resourceProvider)) {
            return false;
        }
    }
    fRecording->fNonVolatileLazyProxies.clear(); // 清除，不再重复实例化
    return true;
}
```

**Volatile 代理**（可重复实例化和销毁）：
```cpp
bool RecordingPriv::instantiateVolatileLazyProxies(ResourceProvider* resourceProvider);
void RecordingPriv::deinstantiateVolatileLazyProxies();
```

### 目标纹理延迟绑定

`LazyProxyData` 支持将 Recording 重放到不同的目标表面：

**创建延迟代理**：
```cpp
Recording::LazyProxyData::LazyProxyData(const Caps* caps,
                                        SkISize dimensions,
                                        const TextureInfo& textureInfo) {
    auto onInstantiate = [this](ResourceProvider*) {
        return std::move(fTarget);
    };

    fTargetProxy = textureInfo.mipmapped() == Mipmapped::kYes
        ? TextureProxy::MakeLazy(caps, dimensions, textureInfo, ...)
        : TextureProxy::MakeFullyLazy(textureInfo, ...);
}
```

**实例化到具体目标**：
```cpp
const Texture* RecordingPriv::setupDeferredTarget(ResourceProvider* resourceProvider,
                                                  Surface* targetSurface,
                                                  SkIVector targetTranslation,
                                                  SkIRect targetClip) {
    // 验证 mipmap、尺寸、平移和裁剪兼容性
    if (!fRecording->fTargetProxyData->lazyInstantiate(resourceProvider,
                                                       surfaceTexture->refTexture())) {
        return nullptr;
    }
    return surfaceTexture->texture();
}
```

### 资源准备

```cpp
bool RecordingPriv::prepareResources(ResourceProvider* resourceProvider,
                                     ScratchResourceManager* scratchManager,
                                     sk_sp<const RuntimeEffectDictionary> rteDict) {
    Task::Status status = fRecording->fRootTaskList->prepareResources(...);
    if (status == Task::Status::kSuccess) {
        // 收集所有延迟代理
        fRecording->fRootTaskList->visitProxies([&](const TextureProxy* proxy) {
            if (proxy->isLazy()) {
                if (proxy->isVolatile()) {
                    fRecording->fVolatileLazyProxies.insert(sk_ref_sp(proxy));
                } else {
                    fRecording->fNonVolatileLazyProxies.insert(sk_ref_sp(proxy));
                }
            }
            return true;
        }, /*readsOnly=*/false);
    }
    return status != Task::Status::kFail;
}
```

### 命令添加到 CommandBuffer

```cpp
bool RecordingPriv::addCommands(Context* context,
                                CommandBuffer* commandBuffer,
                                const Texture* replayTarget,
                                SkIVector targetTranslation,
                                SkIRect targetClip) {
    // 添加额外资源引用
    for (const auto& resource : fRecording->fExtraResourceRefs) {
        commandBuffer->trackResource(resource);
    }

    // 添加任务命令
    if (fRecording->fRootTaskList->addCommands(context, commandBuffer, {...})
        == Task::Status::kFail) {
        return false;
    }

    // 转移完成回调
    for (int i = 0; i < fRecording->fFinishedProcs.size(); ++i) {
        commandBuffer->addFinishedProc(std::move(fRecording->fFinishedProcs[i]));
    }
    fRecording->fFinishedProcs.clear();

    return true;
}
```

### 完成回调管理

析构时标记失败：
```cpp
void RecordingPriv::setFailureResultForFinishedProcs() {
    for (int i = 0; i < fRecording->fFinishedProcs.size(); ++i) {
        fRecording->fFinishedProcs[i]->setFailureResult();
    }
    fRecording->fFinishedProcs.clear();
}
```

### 代理哈希函数

```cpp
std::size_t Recording::ProxyHash::operator()(const sk_sp<TextureProxy>& proxy) const {
    return SkGoodHash()(proxy.get());
}
```
使用指针地址作为哈希，确保同一代理对象在集合中唯一。

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `TaskList` | 命令任务列表管理 |
| `TextureProxy` | 纹理代理 |
| `Texture` | 实际纹理资源 |
| `Resource` | GPU 资源基类 |
| `ResourceProvider` | 资源提供者 |
| `CommandBuffer` | 命令缓冲区 |
| `RefCntedCallback` | 引用计数回调 |
| `Surface` | 渲染表面 |
| `Caps` | 硬件能力 |

**被依赖的模块**

- `Recorder`：生成 Recording
- `Context`：接收并执行 Recording
- `Surface`：作为 Recording 的目标

## 设计模式与设计决策

### 不可变对象模式

`Recording` 一旦创建就不可修改（除了内部状态管理），这确保了提交后的命令序列完整性。

### 延迟实例化模式

通过 `LazyProxyData` 和延迟代理集合，支持资源的延迟分配和多次重放，优化内存使用。

### 资源生命周期管理

通过智能指针和显式引用管理确保资源在命令执行期间有效。

### 两阶段提交模式

1. `prepareResources`：准备所有必需资源
2. `addCommands`：将命令添加到 CommandBuffer

这种分离使得资源准备可以在提交前完成，避免提交时的资源分配失败。

### Volatile/Non-volatile 区分

- **Non-volatile 代理**：Promise Image 等需要持久化的资源
- **Volatile 代理**：可重复使用的临时资源

这种区分优化了不同使用场景的资源管理策略。

### 失败安全设计

析构函数和 `setFailureResultForFinishedProcs` 确保即使 Recording 未正常执行，客户端也能收到失败通知。

### 目标纹理抽象

支持延迟绑定目标，使得同一 Recording 可以重放到不同表面，适用于多窗口渲染等场景。

## 性能考量

### 智能指针优化

使用 `sk_sp` 和 `std::unique_ptr` 管理资源生命周期，避免手动内存管理的开销和错误。

### 延迟实例化

通过延迟代理机制，避免不必要的资源分配，特别是对于可能不会被使用的纹理。

### 批量资源引用

`fExtraResourceRefs` 批量管理公共资源引用，避免在每个 Task 中重复引用。

### 哈希集合去重

使用 `std::unordered_set` 自动去重代理引用，避免重复实例化。

### 移动语义

构造函数接受右值引用（`finishedProcs`），避免回调数组的拷贝。

### 预分配 TaskList

在构造函数中立即创建 `TaskList`，避免首次使用时的分配延迟。

### GPU 测试工具

条件编译的 `GPU_TEST_UTILS` 提供调试接口，不影响发布版本性能。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/graphite/RecordingPriv.h` | 相关 | 私有访问接口 |
| `src/gpu/graphite/task/TaskList.h` | 依赖 | 任务列表实现 |
| `src/gpu/graphite/TextureProxy.h` | 依赖 | 纹理代理 |
| `src/gpu/graphite/Texture.h` | 依赖 | 纹理资源 |
| `src/gpu/graphite/Resource.h` | 依赖 | 资源基类 |
| `src/gpu/graphite/ResourceProvider.h` | 依赖 | 资源提供者 |
| `src/gpu/graphite/CommandBuffer.h` | 依赖 | 命令缓冲区 |
| `src/gpu/RefCntedCallback.h` | 依赖 | 回调管理 |
| `include/gpu/graphite/Context.h` | 使用方 | 执行 Recording |
| `include/gpu/graphite/Recorder.h` | 使用方 | 创建 Recording |
