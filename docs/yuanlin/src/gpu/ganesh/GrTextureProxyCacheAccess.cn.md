# GrTextureProxyCacheAccess

> 源文件: src/gpu/ganesh/GrTextureProxyCacheAccess.h

## 概述

`GrTextureProxyCacheAccess` 是 `GrTextureProxy` 的缓存访问辅助类，专门用于管理纹理代理的 unique key。该类采用"友元访问器"（Friend Accessor）设计模式，为 `GrResourceCache` 和 `GrProxyProvider` 提供对纹理代理 unique key 的特权访问，同时对其他代码隐藏这些敏感操作。

Unique key 是 Skia GPU 资源缓存系统的核心机制，用于标识和查找可复用的资源。该类确保只有授权的缓存管理组件可以修改这些关键标识符。

## 架构位置

`GrTextureProxyCacheAccess` 位于 Skia GPU 资源缓存系统的访问控制层：

```
Skia GPU 资源缓存系统
├── GrResourceCache                    # 资源缓存（管理实际资源）
├── GrProxyProvider                    # 代理提供者（管理代理）
├── GrTextureProxy                     # 纹理代理
│   ├── fUniqueKey                     # Unique key（私有）
│   └── CacheAccess (本类)              # 特权访问接口
└── skgpu::UniqueKey                   # 唯一键类型
```

访问控制流程：
```
GrProxyProvider → proxy->cacheAccess().setUniqueKey(...)
                 (通过 cacheAccess() 访问特权方法)
```

## 主要类与结构体

### 继承关系

该类不使用继承，作为 `GrTextureProxy` 的嵌套友元类存在。

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fTextureProxy | GrTextureProxy* | 指向关联的纹理代理 |

### 关联类型

**skgpu::UniqueKey**：
- GPU 资源的唯一标识符
- 基于内容哈希生成
- 用于缓存查找和复用

## 公共 API 函数

### 设置 Unique Key

```cpp
void setUniqueKey(GrProxyProvider* proxyProvider,
                 const skgpu::UniqueKey& key)
```

**功能**：为纹理代理设置 unique key。

**参数**：
- `proxyProvider`: 代理提供者指针，用于管理 key 到 proxy 的映射
- `key`: 要设置的唯一键

**调用**：转发到 `GrTextureProxy::setUniqueKey()`

**使用场景**：
- 当创建或缓存纹理时
- 为可复用的资源分配标识符

### 清除 Unique Key

```cpp
void clearUniqueKey()
```

**功能**：清除纹理代理的 unique key。

**调用**：转发到 `GrTextureProxy::clearUniqueKey()`

**使用场景**：
- 当资源不再可复用时
- 当资源被移除出缓存时

## 内部实现细节

### 类定义结构

```cpp
class GrTextureProxy::CacheAccess {
private:
    void setUniqueKey(GrProxyProvider* proxyProvider,
                     const skgpu::UniqueKey& key);
    void clearUniqueKey();

    explicit CacheAccess(GrTextureProxy* textureProxy);
    CacheAccess& operator=(const CacheAccess&) = delete;

    // 禁止取地址
    const CacheAccess* operator&() const;
    CacheAccess* operator&();

    GrTextureProxy* fTextureProxy;

    friend class GrTextureProxy;  // 构造访问
    friend class GrProxyProvider; // 方法调用
};
```

### setUniqueKey 实现

```cpp
void setUniqueKey(GrProxyProvider* proxyProvider,
                 const skgpu::UniqueKey& key) {
    fTextureProxy->setUniqueKey(proxyProvider, key);
}
```

**实现特点**：
- 简单转发到纹理代理的私有方法
- 由于友元关系，可以访问私有方法
- 不进行额外的逻辑处理

### clearUniqueKey 实现

```cpp
void clearUniqueKey() {
    fTextureProxy->clearUniqueKey();
}
```

**实现特点**：
- 直接转发，无参数
- 清理代理的内部状态

### 构造函数

```cpp
explicit CacheAccess(GrTextureProxy* textureProxy)
    : fTextureProxy(textureProxy) {}
```

**特点**：
- 私有构造函数
- 只能通过 `GrTextureProxy::cacheAccess()` 创建
- `explicit` 防止隐式转换

### 访问控制

该类使用多层访问保护：

1. **私有构造函数**：外部无法直接创建
2. **友元声明**：
   - `GrTextureProxy`：可以构造实例
   - `GrProxyProvider`：可以调用方法
3. **禁止取地址**：防止持久化指针
4. **禁止赋值**：`operator=` 被删除

### 创建接口

在 `GrTextureProxy` 中定义：

```cpp
inline GrTextureProxy::CacheAccess
GrTextureProxy::cacheAccess() {
    return CacheAccess(this);
}

inline const GrTextureProxy::CacheAccess
GrTextureProxy::cacheAccess() const {
    return CacheAccess(const_cast<GrTextureProxy*>(this));
}
```

**返回值语义**：
- 返回临时对象，不是指针或引用
- 强制短期使用
- 编译器可优化

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|-----|---------|------|
| GrTextureProxy | 友元访问 | 被访问的主类 |
| skgpu::UniqueKey | 参数类型 | 唯一键类型 |
| GrProxyProvider | 参数类型 | 代理管理器 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|-----|---------|------|
| GrProxyProvider | 唯一用户 | 设置和清除 unique key |
| GrResourceCache | 间接使用 | 通过 GrProxyProvider 访问 |

## 设计模式与设计决策

### 友元访问器模式（Friend Accessor Pattern）

**目的**：
- 封装敏感操作（unique key 管理）
- 限制访问权限（只有 `GrProxyProvider`）
- 保持接口清晰

**实现方式**：
```cpp
class GrTextureProxy {
private:
    friend class GrProxyProvider;  // 直接友元不够精细

    // 更好的方式：
    class CacheAccess {
        friend class GrProxyProvider;  // 只能访问 CacheAccess
        void setUniqueKey(...);
    };
public:
    CacheAccess cacheAccess();
};
```

### 最小权限原则

`GrProxyProvider` 只能访问缓存相关操作，不能访问：
- 纹理的其他私有成员
- `GrTextureProxy` 的其他私有方法

### 禁止持久化策略

```cpp
// 禁止这样使用：
auto* access = &proxy->cacheAccess();  // 编译错误
access->setUniqueKey(...);

// 强制临时使用：
proxy->cacheAccess().setUniqueKey(...);  // 正确
```

**原因**：
- 防止长期持有访问器
- 避免生命周期管理问题
- 明确访问意图

### 对称性设计

提供 const 和非 const 版本：
```cpp
CacheAccess cacheAccess();
const CacheAccess cacheAccess() const;
```

虽然方法会修改状态，但 const 版本允许：
- 检查是否有 key
- 在 const 上下文中访问

### 类型安全

通过类型系统强制访问控制：
- 编译时检查权限
- 无运行时开销
- 无法绕过保护

## 性能考量

### 零开销抽象

- **内联**：所有方法都可以内联
- **无虚函数**：无虚函数表查找
- **栈分配**：临时对象在栈上
- **优化掉**：编译器可优化掉包装层

### 编译器优化

源代码：
```cpp
proxy->cacheAccess().setUniqueKey(provider, key);
```

优化后（概念上）：
```cpp
proxy->setUniqueKey(provider, key);
```

### 内存占用

- 类大小：单个指针（8 字节）
- 临时对象：栈分配，无堆操作
- 销毁成本：零（无析构操作）

### 调用开销

理想情况下，调用链：
```
外部 → cacheAccess() → setUniqueKey(转发) → 实际方法
```

编译器优化后：
```
外部 → 实际方法
```

完全内联，无额外开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrTextureProxy.h | 包含 | 纹理代理主类（必须先包含） |
| src/gpu/ganesh/GrProxyProvider.h | 友元用户 | 使用该类设置 unique key |
| src/gpu/ganesh/GrResourceCache.h | 间接用户 | 通过 ProxyProvider 使用 |
| src/gpu/ResourceKey.h | 类型 | UniqueKey 定义 |

## 使用示例

### 设置 Unique Key

```cpp
// 在 GrProxyProvider 中
sk_sp<GrTextureProxy>
GrProxyProvider::createProxyFromBitmap(const SkBitmap& bitmap) {
    // 创建代理
    sk_sp<GrTextureProxy> proxy = ...;

    // 生成 unique key
    skgpu::UniqueKey key;
    GrMakeKeyFromBitmap(&key, bitmap, ...);

    // 通过 cacheAccess 设置 key
    proxy->cacheAccess().setUniqueKey(this, key);

    return proxy;
}
```

### 清除 Unique Key

```cpp
// 在 GrProxyProvider 中
void GrProxyProvider::removeUniqueKeyFromProxy(GrTextureProxy* proxy) {
    if (proxy->getUniqueKey().isValid()) {
        // 从映射表中移除
        fUniquelyKeyedProxies.remove(proxy->getUniqueKey());

        // 清除代理的 key
        proxy->cacheAccess().clearUniqueKey();
    }
}
```

### 资源复用场景

```cpp
// 查找或创建纹理
sk_sp<GrTextureProxy>
GrProxyProvider::findOrCreateProxyByUniqueKey(
    const skgpu::UniqueKey& key) {

    // 先查找缓存
    sk_sp<GrTextureProxy> proxy = this->findProxyByUniqueKey(key);
    if (proxy) {
        return proxy;  // 复用已有代理
    }

    // 创建新代理
    proxy = this->createProxy(...);

    // 设置 key 以便后续复用
    proxy->cacheAccess().setUniqueKey(this, key);

    return proxy;
}
```

## 对比其他访问器类

### 与 GrTextureProxyPriv 的区别

| 特性 | GrTextureProxyCacheAccess | GrTextureProxyPriv |
|-----|--------------------------|-------------------|
| 用途 | 缓存管理（unique key） | 延迟上传管理 |
| 友元 | GrProxyProvider | （通用特权访问） |
| 方法 | setUniqueKey, clearUniqueKey | setDeferredUploader, scheduleUpload |
| 关注点 | 资源标识和查找 | 数据上传和同步 |

### 设计一致性

两者都遵循相同的设计模式：
- 私有构造函数
- 友元访问控制
- 禁止取地址
- 返回值语义
- 零开销抽象
