# GrImageContext

> 源文件: `include/private/gpu/ganesh/GrImageContext.h`

## 概述
GrImageContext 是 GrContextThreadSafeProxy 的轻量级视图类,主要用于 SkImage 对象持有 GPU 上下文引用。它提供了向 GrDirectContext 下转型的后门机制,是 Skia 正在逐步弃用的过渡性类,未来将被完全替换为直接使用 ThreadSafeProxy。

## 架构位置
该类位于 Skia GPU 后端 Ganesh 子系统的上下文层级中,处于 GrContext_Base 派生类的位置。它是一个过渡性的抽象层,介于线程安全代理和完整的录制/直接上下文之间,主要服务于 SkImage 的 GPU 后端实现。

## 主要类与结构体

### GrImageContext
一个轻量级的上下文视图类,包装 ThreadSafeProxy 并提供有限的上下文功能。

**继承关系**: SkRefCnt → GrContext_Base → GrImageContext

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fSingleOwner | mutable skgpu::SingleOwner | 调试构建中用于检测不当线程访问的守卫 |

## 公共 API 函数

### `~GrImageContext() override`
- **功能**: 虚析构函数,清理上下文资源
- **参数**: 无
- **返回值**: 无

### `GrImageContextPriv priv()`
- **功能**: 获取私有 API 访问器(非常量版本)
- **参数**: 无
- **返回值**: GrImageContextPriv 对象,提供对非公开函数的访问

### `const GrImageContextPriv priv() const`
- **功能**: 获取私有 API 访问器(常量版本)
- **参数**: 无
- **返回值**: 常量 GrImageContextPriv 对象

## 内部实现细节

### 上下文继承层级
```
SkRefCnt
  └─ GrContext_Base
      └─ GrImageContext
          └─ GrRecordingContext (通常的派生方向)
              └─ GrDirectContext
```

GrImageContext 位于继承树的中间,提供了一个最小化的 GPU 上下文接口。

### 线程安全守卫
成员变量 `fSingleOwner` 在调试构建中启用:
- 检测上下文是否在错误的线程被访问
- 防止多线程并发访问同一上下文导致的数据竞争
- 守卫被传递给 GrDrawingManager、GrSurfaceDrawContext、GrResourceProvider 和 SkGpuDevice

### Promise Image 特殊支持
提供了静态工厂方法 `MakeForPromiseImage`:
```cpp
static sk_sp<GrImageContext> MakeForPromiseImage(sk_sp<GrContextThreadSafeProxy>);
```

这个方法创建一个"占位"上下文,用于 Promise Image(延迟纹理获取的图像):
- 没有真实的 GPU 能力
- 只是 ThreadSafeProxy 的简单包装
- 允许 SkImage 持有必要的上下文引用

### 上下文放弃机制
```cpp
SK_API virtual void abandonContext();
SK_API virtual bool abandoned();
```

这些虚方法允许子类实现上下文放弃逻辑:
- `abandonContext()`: 主动放弃 GPU 资源,不进行清理
- `abandoned()`: 查询上下文是否已被放弃

### 类型转换辅助
```cpp
GrImageContext* asImageContext() override { return this; }
```

覆盖基类的虚方法,提供安全的向下转型机制,避免使用危险的 dynamic_cast。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkRefCnt | 引用计数基类 |
| SingleOwner | 线程安全检查工具 |
| GrContext_Base | 基类,提供上下文基础框架 |
| GrContextThreadSafeProxy | 线程安全的上下文代理,核心包装对象 |

### 被依赖的模块
- SkImage: GPU 后端实现使用此类持有上下文
- GrRecordingContext: 派生类,提供录制能力
- GrDirectContext: 最终派生类,提供完整的 GPU 操作能力
- Promise Image 相关实现

## 设计模式与设计决策

### 适配器模式
GrImageContext 作为 GrContextThreadSafeProxy 和传统上下文接口之间的适配器:
- 包装线程安全代理
- 提供上下文接口
- 桥接新旧 API 设计

### 过渡性设计
根据注释,这是一个临时性的设计:
> "Once we remove the backdoors, this goes away and SkImages just hold ThreadSafeProxies."

设计意图是最终移除此类,让 SkImage 直接持有 ThreadSafeProxy,减少一层抽象。

### 权限控制(Friend 模式)
通过 GrImageContextPriv 友元类控制对内部功能的访问:
- 公共 API 保持最小化
- 内部实现细节通过 priv() 访问
- 平衡了封装性和内部使用便利性

### 虚继承和多态
大量使用虚函数支持多态:
- 允许向上转型到基类指针
- 支持运行时类型识别
- 实现上下文层级的统一接口

## 性能考量

### 轻量级设计
GrImageContext 本身非常轻量:
- 主要成员是一个继承的智能指针(fThreadSafeProxy)
- 调试守卫在发布构建中无开销
- 作为视图类,不持有重量级资源

### 虚函数调用开销
类中使用了虚函数,引入了虚函数表查找的小额开销:
- 通常可以忽略不计
- 现代 CPU 的分支预测可以很好地处理
- 相比 GPU 操作的开销微不足道

### 线程安全检查开销
SingleOwner 守卫只在调试构建中启用:
- 发布构建无性能影响
- 帮助在开发阶段发现线程安全问题
- 是一个典型的"调试时安全,发布时高效"的设计

### Promise Image 优化
为 Promise Image 提供的专门工厂方法允许延迟纹理创建:
- 图像可以在工作线程创建
- 纹理在真正绘制时才获取
- 减少了主线程和 GPU 线程的阻塞

## 设计演进方向
根据代码注释,未来的设计方向包括:
1. 移除 SkImage 向 GrDirectContext 下转型的后门
2. 让 SkImage 直接持有 GrContextThreadSafeProxy
3. 移除 GrImageContext 这个中间层
4. 可能将 SingleOwner 下移到 GrRecordingContext

这反映了 Skia 团队正在简化上下文层级结构,减少不必要的抽象层。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/gpu/ganesh/GrContext_Base.h | 基类定义 |
| include/gpu/GrContextThreadSafeProxy.h | 包装的线程安全代理 |
| include/private/gpu/ganesh/GrImageContextPriv.h | 私有 API 访问器 |
| include/gpu/GrRecordingContext.h | 派生类,添加录制能力 |
| include/gpu/GrDirectContext.h | 最终派生类,完整上下文 |
| src/image/SkImage_Gpu.h | 使用此类的 GPU 图像实现 |
| include/private/base/SingleOwner.h | 线程安全守卫 |
