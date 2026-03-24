# RecorderPriv - Graphite Recorder 内部访问接口

> 源文件: `src/gpu/graphite/RecorderPriv.h`

## 概述

`RecorderPriv` 是 Skia Graphite 中 `Recorder` 类的内部特权访问类。`Recorder` 是 Graphite 的核心录制组件，负责录制绘图命令并生成 `Recording` 对象。`RecorderPriv` 为 Skia 内部组件（如 `Device`、`DrawTask` 等）提供了对 Recorder 子系统的访问，包括资源管理、缓冲区管理、文本渲染、着色器编译等功能。

该文件还定义了辅助函数 `AsGraphiteRecorder()`，用于将通用 `SkRecorder` 安全转换为 Graphite `Recorder`。

## 架构位置

```
Context (上下文)
  └── Recorder (录制器 - 公共 API)
        └── RecorderPriv (内部访问窗口)
              ├── SharedContext → Caps, ShaderCodeDictionary, RendererProvider
              ├── ResourceProvider → ProxyCache, ResourceCache
              ├── DrawBufferManager (绘制缓冲区管理)
              ├── UploadBufferManager (上传缓冲区管理)
              ├── FloatStorageManager (浮点存储管理)
              ├── AtlasProvider (图集提供者)
              ├── TokenTracker (令牌追踪器)
              ├── StrikeCache (字形缓存)
              └── TextBlobRedrawCoordinator (文本重绘协调器)
```

`Recorder` 在多线程架构中扮演"线程本地"角色——每个线程拥有自己的 Recorder，它们共享同一个 `SharedContext`。

## 主要类与结构体

### `RecorderPriv`

遵循 Skia 标准 Priv 类模式，无额外数据成员或虚方法。通过 `Recorder::priv()` 方法获取。

## 公共 API 函数

### 任务与设备管理

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `add(sk_sp<Task>)` | `void` | 添加任务到录制器 |
| `flushTrackedDevices(const char*)` | `void` | 刷新所有已跟踪设备 |
| `flushTrackedDevices(const TextureProxy*)` | `void` | 刷新依赖特定纹理代理的设备 |

### 管线数据构建

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `popOrCreateKeyAndDataBuilder()` | `unique_ptr<KeyAndDataBuilder>` | 获取或创建键值数据构建器（对象池模式） |
| `pushKeyAndDataBuilder(...)` | `void` | 归还键值数据构建器到池中 |

### 共享上下文访问

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `caps()` | `const Caps*` | GPU 能力查询 |
| `resourceProvider()` | `ResourceProvider*` | 资源提供者 |
| `runtimeEffectDictionary()` | `sk_sp<RuntimeEffectDictionary>` | 运行时效果字典 |
| `shaderCodeDictionary()` | `ShaderCodeDictionary*` | 着色器代码字典（const 和非 const） |
| `rendererProvider()` | `const RendererProvider*` | 渲染器提供者 |
| `isProtected()` | `Protected` | 是否受保护内容 |

### 缓冲区与存储管理

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `rootUploadList()` | `UploadList*` | 根上传列表 |
| `drawBufferManager()` | `DrawBufferManager*` | 绘制缓冲区管理器 |
| `uploadBufferManager()` | `UploadBufferManager*` | 上传缓冲区管理器 |
| `floatStorageManager()` | `FloatStorageManager*` | 浮点存储管理器 |
| `refFloatStorageManager()` | `sk_sp<FloatStorageManager>` | 浮点存储管理器（引用计数版本） |

### 文本与图集

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `atlasProvider()` | `AtlasProvider*` | 图集提供者 |
| `tokenTracker()` | `TokenTracker*` | 令牌追踪器 |
| `strikeCache()` | `StrikeCache*` | 字形 Strike 缓存 |
| `textBlobCache()` | `TextBlobRedrawCoordinator*` | TextBlob 重绘协调器 |
| `proxyCache()` | `ProxyCache*` | 纹理代理缓存 |

### 纹理代理管理

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `addPendingRead(const TextureProxy*)` | `void` | 添加待读取的纹理代理引用 |
| `CreateCachedProxy(Recorder*, const SkBitmap&, string_view)` | `sk_sp<TextureProxy>` | 创建缓存的纹理代理（静态方法） |

### 状态与调试

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `uniqueID()` | `uint32_t` | Recorder 唯一标识 |
| `nextRecordingID()` | `uint32_t` | 下一个 Recording ID（仅 SK_DEBUG） |
| `getResourceCacheLimit()` | `size_t` | 资源缓存限制 |

### 测试专用（GPU_TEST_UTILS）

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `deviceIsRegistered(Device*)` | `bool` | 设备是否已注册 |
| `resourceCache()` | `ResourceCache*` | 资源缓存 |
| `sharedContext()` | `SharedContext*` | 共享上下文 |
| `setContext(Context*)` | `void` | 设置 Context 反向指针 |
| `context()` | `Context*` | 获取 Context |
| `issueFlushToken()` | `void` | 发出刷新令牌 |

## 内部实现细节

### AsGraphiteRecorder 辅助函数

```cpp
inline Recorder* AsGraphiteRecorder(SkRecorder* recorder) {
    if (!recorder) return nullptr;
    if (recorder->type() != SkRecorder::Type::kGraphite) return nullptr;
    return static_cast<Recorder*>(recorder);
}
```

该函数实现了从通用 `SkRecorder` 到 Graphite `Recorder` 的安全向下转换（downcasting），使用类型标签而非 `dynamic_cast`，避免 RTTI 开销。

### Priv 双版本访问

```cpp
inline RecorderPriv Recorder::priv() { return RecorderPriv(this); }
inline const RecorderPriv Recorder::priv() const {
    return RecorderPriv(const_cast<Recorder*>(this));
}
```

提供 const 和非 const 两种访问路径，确保 const 正确性传播。

### 设备刷新机制

两个 `flushTrackedDevices()` 重载分别用于：
1. 全量刷新（带调试任务转储标记）
2. 依赖驱动的选择性刷新（仅刷新依赖指定纹理代理的设备）

这种选择性刷新减少了不必要的同步点。

### KeyAndDataBuilder 对象池

`popOrCreateKeyAndDataBuilder()` / `pushKeyAndDataBuilder()` 实现了简单的对象池模式，避免频繁分配和释放管线键值构建器对象。

## 依赖关系

- **include/core/SkRecorder.h**: 通用 Recorder 基类
- **include/gpu/graphite/Recorder.h**: Graphite Recorder 公共 API
- **src/gpu/graphite/PipelineData.h**: 管线数据构建（KeyAndDataBuilder）
- **src/gpu/graphite/ResourceProvider.h**: 资源提供与缓存
- **src/gpu/graphite/SharedContext.h**: 共享上下文
- **src/gpu/graphite/DebugUtils.h**: 调试工具（SK_DUMP_TASKS_CODE）

前向声明: `AtlasProvider`, `Caps`, `Context`, `Device`, `DrawBufferManager`, `ProxyCache`, `RendererProvider`, `ResourceCache`, `RuntimeEffectDictionary`, `ShaderCodeDictionary`, `Task`, `TextureProxy`, `UploadBufferManager`, `UploadList`

## 设计模式与设计决策

### Priv 类模式

标准 Skia Priv 模式实现。所有子系统访问器均为内联的单步解引用，保证零开销。

### 多 Recorder 并行架构

Recorder 设计为线程独立的录制单元，每个 Recorder 持有自己的缓冲区管理器、上传管理器等资源。多个 Recorder 通过 `SharedContext` 共享全局状态（Caps、字典、渲染器）。这种架构允许多线程并行录制而无需锁竞争。

### 选择性设备刷新

基于纹理代理依赖的选择性刷新是性能优化的关键决策，避免了每次纹理操作都触发所有设备的全量刷新。

## 性能考量

- 所有子系统访问器均为内联函数，编译器可完全消除间接调用
- `AsGraphiteRecorder()` 使用类型标签而非 RTTI，避免虚表查找
- `KeyAndDataBuilder` 对象池减少堆分配
- 选择性设备刷新减少不必要的 GPU 同步
- `uniqueID()` 为直接成员访问，常量时间

## 相关文件

- `include/gpu/graphite/Recorder.h` - Recorder 公共 API
- `src/gpu/graphite/Recorder.cpp` - Recorder 实现
- `src/gpu/graphite/RecordingPriv.h` - Recording 内部访问
- `src/gpu/graphite/SharedContext.h` - 共享上下文
- `src/gpu/graphite/Device.h` - Graphite Device
- `src/gpu/graphite/DrawBufferManager.h` - 绘制缓冲区管理
- `src/gpu/graphite/AtlasProvider.h` - 图集提供者
