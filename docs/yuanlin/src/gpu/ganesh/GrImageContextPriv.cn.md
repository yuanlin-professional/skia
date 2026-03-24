# GrImageContextPriv

> 源文件: src/gpu/ganesh/GrImageContextPriv.h

## 概述

`GrImageContextPriv` 是 `GrImageContext` 的特权访问器类,为 Skia 内部代码提供对图像上下文内部功能的访问。它继承自 `GrBaseContextPriv`,扩展了基础上下文的特权接口,同时添加了图像上下文特有的内部操作。

该类遵循 Skia 的 "Priv" 命名约定,表示仅供内部使用的接口。它是一个纯特权窗口类,不包含额外的数据成员或虚函数,所有操作都是对底层 `GrImageContext` 的代理访问。

## 架构位置

`GrImageContextPriv` 位于上下文访问控制层:

```
GrContext_Base (基础上下文)
    └── GrImageContext (图像上下文)
            └── GrImageContextPriv (特权访问器)
                    └── 继承自 GrBaseContextPriv
```

在 Ganesh 架构中的位置:
- 作为 `GrImageContext` 的伴生类
- 为内部代码提供受控访问
- 支持 Promise Image 的创建

## 主要类与结构体

### 继承关系

```
GrBaseContextPriv
    └── GrImageContextPriv
```

### 关键成员变量

无额外成员变量,仅继承自 `GrBaseContextPriv`:

| 继承成员 | 类型 | 说明 |
|---------|------|------|
| `fContext` | `GrContext_Base*` | 指向基础上下文的指针 |

## 公共 API 函数

### 上下文访问

```cpp
// 获取图像上下文指针
GrImageContext* context();
const GrImageContext* context() const;
```

### 状态查询

```cpp
// 检查上下文是否已被放弃
bool abandoned();
```

### 工厂方法

```cpp
// 为 Promise Image 创建图像上下文
// tsp: 线程安全代理
static sk_sp<GrImageContext> MakeForPromiseImage(
    sk_sp<GrContextThreadSafeProxy> tsp);
```

### 调试接口

```cpp
// 获取单一所有者指针(仅调试模式)
SkDEBUGCODE(skgpu::SingleOwner* singleOwner() const;)
```

## 内部实现细节

### 上下文转换

```cpp
GrImageContext* context() {
    // 从基类指针向下转型
    return static_cast<GrImageContext*>(fContext);
}

const GrImageContext* context() const {
    return static_cast<const GrImageContext*>(fContext);
}
```

- 安全的向下转型
- 基于构造时的类型保证

### abandoned() 实现

```cpp
bool abandoned() {
    return this->context()->abandoned();
}
```

- 简单的代理调用
- 检查上下文是否因错误被放弃

### MakeForPromiseImage 实现

```cpp
static sk_sp<GrImageContext> MakeForPromiseImage(
    sk_sp<GrContextThreadSafeProxy> tsp) {
    return GrImageContext::MakeForPromiseImage(std::move(tsp));
}
```

- 调用 `GrImageContext` 的私有工厂方法
- 用于创建 Promise Image 的特殊上下文
- Promise Image: 延迟加载的纹理

### singleOwner() 实现

```cpp
SkDEBUGCODE(
    skgpu::SingleOwner* singleOwner() const {
        return this->context()->singleOwner();
    }
)
```

- 仅调试模式存在
- 用于线程安全检查
- 验证单线程访问约束

### 构造函数

```cpp
protected:
    explicit GrImageContextPriv(GrImageContext* iContext)
        : GrBaseContextPriv(iContext) {}
```

- 受保护构造函数
- 仅 `GrImageContext` 可以创建
- 传递给基类构造函数

### 禁止拷贝和取地址

```cpp
private:
    GrImageContextPriv(const GrImageContextPriv&) = delete;
    GrImageContextPriv& operator=(const GrImageContextPriv&) = delete;

    const GrImageContextPriv* operator&() const;
    GrImageContextPriv* operator&();
```

- 防止拷贝和赋值
- 禁止取地址避免指针逃逸
- 确保只能通过 `priv()` 获取

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrImageContext` | 被访问的上下文类 |
| `GrBaseContextPriv` | 基类特权访问器 |
| `GrContextThreadSafeProxy` | 线程安全代理 |
| `skgpu::SingleOwner` | 单一所有者调试工具 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `GrImageContext` | 提供 `priv()` 方法 |
| Skia 内部代码 | 通过 `priv()` 访问内部功能 |
| Promise Image 系统 | 使用 `MakeForPromiseImage()` |

## 设计模式与设计决策

### 设计模式

1. **特权访问器模式 (Privileged Accessor)**
   - 为内部代码提供特权接口
   - 不暴露给公共 API
   - 通过 `priv()` 方法获取

2. **代理模式 (Proxy)**
   - 代理对 `GrImageContext` 的访问
   - 转发调用到实际上下文
   - 提供类型安全的转换

3. **不可拷贝模式 (Non-Copyable)**
   - 删除拷贝构造和赋值
   - 防止访问器对象被复制
   - 保持访问控制的严格性

### 关键设计决策

1. **为何继承 GrBaseContextPriv?**
   - 复用基础上下文的特权接口
   - 保持接口层次的一致性
   - 简化代码复用

2. **为何是纯特权窗口类?**
   - 不增加额外的数据成员
   - 保持零开销抽象
   - 避免对象大小膨胀

3. **MakeForPromiseImage 的特权性**
   - Promise Image 是内部实现细节
   - 普通用户不应直接创建
   - 通过 `priv()` 限制访问

4. **SingleOwner 仅调试模式**
   - 线程安全检查仅在开发时需要
   - Release 版本避免运行时开销
   - 使用 `SkDEBUGCODE` 条件编译

5. **禁止取地址的必要性**
   - 防止 `GrImageContextPriv*` 指针泄露
   - 确保只能通过 `priv()` 获取
   - 维护访问控制

6. **abandoned() 的便利性**
   - 简化错误处理检查
   - 统一的上下文状态查询
   - 避免直接访问内部状态

## 性能考量

### 零开销抽象

- 无额外数据成员
- 内联方法调用
- 编译器优化后等同于直接访问

### 静态转型

```cpp
static_cast<GrImageContext*>(fContext)
```

- 零运行时开销
- 基于构造时的类型保证
- 避免动态类型检查

### 条件编译

```cpp
SkDEBUGCODE(...)
```

- 调试代码仅在 Debug 模式存在
- Release 版本完全移除
- 无分支开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/gpu/ganesh/GrImageContext.h` | 宿主 | 定义被访问的上下文类 |
| `src/gpu/ganesh/GrBaseContextPriv.h` | 基类 | 基础上下文特权访问器 |
| `include/gpu/ganesh/GrContextThreadSafeProxy.h` | 依赖 | 线程安全代理 |
| `src/gpu/ganesh/GrImageContext.cpp` | 实现 | 上下文实现文件 |
