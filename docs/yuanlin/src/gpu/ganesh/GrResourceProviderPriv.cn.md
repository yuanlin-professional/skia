# GrResourceProviderPriv

> 源文件
> - src/gpu/ganesh/GrResourceProviderPriv.h

## 概述

`GrResourceProviderPriv` 是 `GrResourceProvider` 的特权访问类,提供了只应在 Skia 内部使用的接口。这是一个纯粹的访问窗口类(privileged window class),不包含任何数据成员或虚函数,仅通过友元机制暴露 `GrResourceProvider` 的私有或受保护成员。该设计模式在 Skia 中广泛使用,用于在保持公共 API 简洁的同时,允许内部代码访问必要的实现细节。

## 架构位置

在 Skia GPU 架构中的位置:

```
GrResourceProvider (公共接口)
    └── GrResourceProviderPriv (特权接口)
        └── 提供内部访问能力
```

这是一个访问控制模式,不是独立的功能模块。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `GrResourceProviderPriv` | 无 | 特权访问窗口类 |

### 关键成员变量

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fResourceProvider` | `GrResourceProvider*` | 指向被访问的资源提供者 |

## 公共 API 函数

### 特权方法

```cpp
GrGpu* gpu();
```

获取底层 GPU 接口的访问权限。这是唯一暴露的特权方法。

### 访问控制

```cpp
// 禁止取地址
const GrResourceProviderPriv* operator&() const;
GrResourceProviderPriv* operator&();
```

这些运算符被声明但不实现,防止获取该类的指针,强制它只能作为临时对象使用。

## 内部实现细节

### 构造机制

**私有构造函数**:
```cpp
private:
    explicit GrResourceProviderPriv(GrResourceProvider* provider)
        : fResourceProvider(provider) {}
```

只能通过 `GrResourceProvider` 的 `priv()` 方法创建:
```cpp
inline GrResourceProviderPriv GrResourceProvider::priv() {
    return GrResourceProviderPriv(this);
}

inline const GrResourceProviderPriv GrResourceProvider::priv() const {
    return GrResourceProviderPriv(const_cast<GrResourceProvider*>(this));
}
```

### 访问限制

**禁止拷贝赋值**:
```cpp
GrResourceProviderPriv& operator=(const GrResourceProviderPriv&) = delete;
```

防止意外的赋值操作。

**友元声明**:
```cpp
friend class GrResourceProvider;
```

只有 `GrResourceProvider` 可以构造此类。

### 使用模式

典型用法:
```cpp
GrGpu* gpu = resourceProvider->priv().gpu();
```

特点:
- `priv()` 返回临时对象
- 立即调用 `gpu()` 获取结果
- 临时对象随即销毁
- 不能保存 priv 对象的引用或指针

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrResourceProvider` | 被访问的主类 |
| `GrGpu` | 返回的接口类型 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| Skia 内部代码 | 需要访问 GPU 接口时使用 |
| 测试代码 | 访问内部状态进行测试 |

## 设计模式与设计决策

### 设计模式

1. **Passkey 模式变体**:
   - 通过嵌套类限制访问
   - 比友元声明更明确

2. **临时对象模式**:
   - 强制使用临时对象
   - 通过禁止取地址实现

3. **Const 正确性**:
   - 提供 const 和非 const 版本
   - 保持类型安全

### 关键设计决策

**为何使用 Priv 模式**:

优点:
- 明确区分公共和内部接口
- 不污染公共头文件
- 编译器强制检查访问权限
- 文档化内部使用意图

vs 友元:
```cpp
// 不推荐:友元声明分散
class GrResourceProvider {
    friend class SomeInternalClass;
    friend class AnotherInternalClass;
    // ...
};

// 推荐:集中的 Priv 类
class GrResourceProvider {
    inline GrResourceProviderPriv priv();
};
```

**为何禁止取地址**:
```cpp
const GrResourceProviderPriv* operator&() const;
```

防止误用:
```cpp
// 被禁止:保存指针
auto* priv = &resourceProvider->priv();  // 编译错误

// 正确用法:临时对象
GrGpu* gpu = resourceProvider->priv().gpu();
```

**为何不包含数据成员**:
> This class is purely a privileged window into GrResourceProvider.
> It should never have additional data members or virtual methods.

原因:
- 保持零开销抽象
- 避免对象大小改变
- 简化语义(纯访问器)

**为何需要 const 版本**:
```cpp
inline const GrResourceProviderPriv GrResourceProvider::priv() const {
    return GrResourceProviderPriv(const_cast<GrResourceProvider*>(this));
}
```

- 允许从 const 对象访问 priv
- 内部需要修改时使用 const_cast
- 调用者仍然受到 const 保护

**为何返回值而非引用**:
```cpp
inline GrResourceProviderPriv GrResourceProvider::priv() {
    return GrResourceProviderPriv(this);  // 返回值
}
```

- 强制临时对象语义
- 防止保存引用
- 确保安全的访问模式

## 性能考量

### 零开销抽象

**编译器优化**:
```cpp
GrGpu* gpu = resourceProvider->priv().gpu();
```

编译后等价于:
```cpp
GrGpu* gpu = resourceProvider->gpu();  // 直接调用
```

- 内联展开
- 临时对象优化掉
- 无运行时开销

**类大小**:
- `GrResourceProviderPriv`: 仅一个指针大小
- 通常作为临时对象,栈分配
- 不增加内存开销

### 使用建议

**正确**:
```cpp
GrGpu* gpu = provider->priv().gpu();
```

**避免**:
```cpp
// 不必要的中间变量
auto priv = provider->priv();
GrGpu* gpu = priv.gpu();
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrResourceProvider.h` | 主类 | 被访问的资源提供者 |
| `src/gpu/ganesh/GrGpu.h` | 返回类型 | GPU 接口 |

**类似的 Priv 类**:
- `GrContextPriv`
- `GrSurfaceProxyPriv`
- `GrRenderTargetProxyPriv`
- `GrTextureProxyPriv`
- `SkImagePriv`
- `SkSurfacePriv`

这是 Skia 中广泛使用的模式。
