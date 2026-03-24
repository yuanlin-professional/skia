# SkFontConfigInterface_direct_factory

> 源文件: [src/ports/SkFontConfigInterface_direct_factory.cpp](../../../../src/ports/SkFontConfigInterface_direct_factory.cpp)

## 概述

本文件实现了 `SkFontConfigInterface` 的直接工厂方法 `GetSingletonDirectInterface()`，用于创建并返回一个基于 fontconfig 的字体配置接口单例实例。该单例在首次调用时被创建，随后的调用均返回同一实例。

## 架构位置

本文件位于 Skia 字体系统的端口 (ports) 层，是字体配置接口的工厂实现之一。它将 `SkFontConfigInterface` 抽象接口与具体的 `SkFontConfigInterfaceDirect` 实现连接起来，属于字体管理子系统的底层初始化组件。

```
SkFontConfigInterface (抽象接口)
  └── SkFontConfigInterfaceDirect (直接实现)
        └── GetSingletonDirectInterface() (本文件：工厂单例)
```

## 主要类与结构体

本文件不定义新的类或结构体，仅实现 `SkFontConfigInterface` 的一个静态成员函数。

### SkFontConfigInterface::GetSingletonDirectInterface()

- 返回类型: `SkFontConfigInterface*`
- 功能: 创建或返回 `SkFontConfigInterfaceDirect` 的唯一实例
- 线程安全性: 使用函数级静态变量（C++11 线程安全初始化）保证线程安全

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `SkFontConfigInterface* SkFontConfigInterface::GetSingletonDirectInterface()` | 获取 fontconfig 直接接口的全局单例指针 |

## 内部实现细节

- 使用 C++ 函数级静态变量实现单例模式：`static SkFontConfigInterface* singleton = new SkFontConfigInterfaceDirect(nullptr);`
- 传递 `nullptr` 作为 `SkFontConfigInterfaceDirect` 的构造参数，表示使用默认的 fontconfig 配置
- 单例在程序运行期间永不销毁（使用裸指针 `new`，无对应 `delete`），避免静态析构顺序问题

## 依赖关系

- **头文件依赖**: `src/ports/SkFontConfigInterface_direct.h` — 提供 `SkFontConfigInterfaceDirect` 类的声明
- **接口依赖**: `SkFontConfigInterface` — 基类，定义字体配置接口
- **平台依赖**: Linux/Unix 平台上的 fontconfig 库

## 设计模式与设计决策

1. **单例模式 (Singleton)**: 全局共享一个 fontconfig 接口实例，避免重复初始化开销。
2. **静态局部变量延迟初始化**: 利用 C++11 保证的线程安全静态初始化，无需额外同步机制。
3. **有意的内存泄漏**: 使用裸 `new` 而不释放，这是常见的单例设计选择，可避免程序退出时的静态析构顺序依赖问题。

## 性能考量

- 单例模式确保 fontconfig 接口只初始化一次，后续调用仅返回已缓存的指针
- 函数级静态变量初始化的线程安全由编译器保证，无需显式加锁
- `SkFontConfigInterfaceDirect` 的构造过程涉及解析系统 fontconfig 配置，这是一个相对昂贵的操作，单例模式将此成本分摊到首次调用
- 后续所有调用的开销仅为一次指针读取（编译器可能将静态变量的初始化检查优化为一次原子读取）
- 由于使用裸指针而非 `sk_sp`，不涉及任何引用计数的原子操作开销

## 使用场景

本函数在以下场景中被调用:
- Linux 平台上字体管理器 (`SkFontMgr_FontConfigInterface`) 的创建过程中
- 需要与系统 fontconfig 交互以查找、匹配和加载字体时
- 作为 `SkFontConfigInterface::RefGlobal()` 的默认实现后端

## 源代码

```cpp
SkFontConfigInterface* SkFontConfigInterface::GetSingletonDirectInterface() {
    static SkFontConfigInterface* singleton = new SkFontConfigInterfaceDirect(nullptr);
    return singleton;
}
```

此代码简洁地体现了"延迟初始化 + 线程安全单例"的惯用模式。`nullptr` 参数告诉
`SkFontConfigInterfaceDirect` 使用默认的 `FcConfig` 而非自定义配置。

## 相关文件

- `src/ports/SkFontConfigInterface_direct.h` — `SkFontConfigInterfaceDirect` 类声明
- `include/ports/SkFontConfigInterface.h` — `SkFontConfigInterface` 接口定义
- `src/ports/SkFontConfigInterface_direct.cpp` — `SkFontConfigInterfaceDirect` 实现
- `src/ports/SkFontMgr_FontConfigInterface.cpp` — 使用本单例的字体管理器
