# ContextPriv - Graphite Context 内部访问接口

> 源文件: `src/gpu/graphite/ContextPriv.h`

## 概述

`ContextPriv` 是 Skia Graphite 渲染后端中 `Context` 类的内部特权访问类（Privileged Access Class）。它为 Skia 内部代码提供了访问 `Context` 私有成员的能力，同时将这些接口与公共 API 隔离开来。该文件还定义了 `ContextCtorAccessor` 类，用于允许后端工厂函数调用 `Context` 的私有构造函数。

## 架构位置

`ContextPriv` 位于 Graphite GPU 后端的核心层，是连接公共 `Context` API 与内部子系统的桥梁。

```
Context (公共 API)
  └── ContextPriv (内部特权窗口)
        ├── SharedContext (共享上下文，包含 Caps/字典/渲染器等)
        ├── ResourceProvider (资源提供者)
        ├── QueueManager (队列管理器)
        └── skcpu::ContextImpl (CPU 上下文实现)
```

## 主要类与结构体

### `ContextPriv`

内部特权访问类，不包含额外数据成员或虚函数，仅作为 `Context` 私有成员的透传窗口。

- **设计原则**: 该类永远不应有自己的数据成员或虚方法
- **访问控制**: 构造函数和拷贝由 `Context` 友元控制
- **地址防护**: 重载了取地址运算符，防止外部获取对象指针

### `ContextCtorAccessor`

构造器访问跳板类，允许后端 `ContextFactory` 函数通过此类调用 `Context` 的私有构造函数。

- 解决了不同命名空间中的工厂函数无法直接友元声明的问题

## 公共 API 函数

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `caps()` | `const Caps*` | 获取 GPU 能力查询对象 |
| `shaderCodeDictionary()` | `ShaderCodeDictionary*` | 获取着色器代码字典（const 和非 const 重载） |
| `globalCache()` | `GlobalCache*` | 获取全局缓存（仅测试模式） |
| `rendererProvider()` | `const RendererProvider*` | 获取渲染器提供者 |
| `resourceProvider()` | `ResourceProvider*` | 获取资源提供者 |
| `sharedContext()` | `SharedContext*` | 获取共享上下文 |
| `cpuContext()` | `const skcpu::ContextImpl*` | 获取 CPU 上下文实现 |
| `startCapture()` | `void` | 开始 GPU 捕获（仅测试模式） |
| `stopCapture()` | `void` | 停止 GPU 捕获（仅测试模式） |
| `deregisterRecorder()` | `void` | 注销 Recorder（仅测试模式） |
| `readPixels()` | `bool` | 从纹理代理读取像素（仅测试模式） |

`ContextCtorAccessor::MakeContext()` 是静态工厂方法，接受 `SharedContext`、`QueueManager` 和 `ContextOptions` 创建 `Context` 实例。

## 内部实现细节

### Priv 模式访问机制

`Context::priv()` 方法返回 `ContextPriv` 对象，分为 const 和非 const 两个版本：

```cpp
inline ContextPriv Context::priv() { return ContextPriv(this); }
inline const ContextPriv Context::priv() const {
    return ContextPriv(const_cast<Context *>(this));
}
```

const 版本使用 `const_cast` 构造 `ContextPriv`，因为 `ContextPriv` 方法本身通过返回类型控制 const 正确性。

### 条件编译

`GPU_TEST_UTILS` 宏保护的方法仅在测试配置下可用，包括 GPU 捕获、Recorder 注销和像素读取功能。

## 依赖关系

- **include/core/SkRefCnt.h**: 引用计数智能指针
- **include/gpu/graphite/Context.h**: 公共 Context 类定义
- **src/gpu/graphite/QueueManager.h**: GPU 命令队列管理
- **src/gpu/graphite/SharedContext.h**: 多 Recorder 共享的上下文状态

前向声明的类型: `Caps`, `GlobalCache`, `Recorder`, `RendererProvider`, `ResourceProvider`, `ShaderCodeDictionary`, `TextureProxy`, `PathRendererStrategy`, `ContextOptions`, `SkPixmap`, `SkImageInfo`

## 设计模式与设计决策

### Priv 类模式（Pimpl 变体）

这是 Skia 中广泛使用的设计模式。与传统的 Pimpl 模式不同，Priv 类不拥有任何数据，仅持有指向宿主对象的指针。这种模式实现了：

1. **编译隔离**: 内部头文件不需要被公共头文件包含
2. **API 分层**: 公共 API 和内部 API 清晰分离
3. **零运行时开销**: 编译器可将 Priv 类完全内联

### 工厂跳板模式

`ContextCtorAccessor` 解决了 C++ 友元声明的命名空间限制问题。后端工厂函数（如 Vulkan、Metal 等）位于不同命名空间中，无法直接在 `Context.h` 中声明为友元。

## 性能考量

- `ContextPriv` 是零开销抽象，所有方法均为内联函数
- 不引入额外的间接调用或虚函数开销
- 取地址运算符被重载为删除，防止意外存储对象引用导致悬挂指针

## 相关文件

- `include/gpu/graphite/Context.h` - Context 公共 API 定义
- `src/gpu/graphite/SharedContext.h` - 共享上下文实现
- `src/gpu/graphite/QueueManager.h` - 队列管理器
- `src/gpu/graphite/Caps.h` - GPU 能力查询
- `src/gpu/graphite/ResourceProvider.h` - 资源提供者
- `src/gpu/graphite/ShaderCodeDictionary.h` - 着色器代码字典
