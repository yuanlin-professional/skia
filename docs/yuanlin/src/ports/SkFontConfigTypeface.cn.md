# SkFontConfigTypeface

> 源文件: [src/ports/SkFontConfigTypeface.h](../../../../src/ports/SkFontConfigTypeface.h)

## 概述

本头文件定义了 `SkTypeface_FCI` 类，它是 Linux 平台上通过 FontConfig 接口 (`SkFontConfigInterface`) 发现的字体面的代理实现。`SkTypeface_FCI` 继承自 `SkTypeface_proxy`，将实际的字体操作委托给底层的真实 typeface，同时保存 FontConfig 的字体身份标识 (`FontIdentity`) 和字体族名称，用于字体匹配和序列化。

## 架构位置

```
SkTypeface (基类)
  └── SkTypeface_proxy (代理基类)
        └── SkTypeface_FCI (本文件: FontConfig 代理)
              ├── realTypeface (实际的 SkTypeface_FreeType 等)
              └── SkFontConfigInterface (字体发现)
                    └── FontIdentity (字体文件路径、TTC 索引等)
```

在 Linux 字体管理流程中:
1. `SkFontConfigInterface` 负责通过 fontconfig 查找匹配的字体文件
2. 找到的字体通过底层引擎（如 FreeType）加载为 `realTypeface`
3. `SkTypeface_FCI` 包装 `realTypeface`，附加 FontConfig 身份信息

## 主要类与结构体

### SkTypeface_FCI

继承 `SkTypeface_proxy`，FontConfig 字体的代理 typeface。

**公共静态工厂方法:**

```cpp
static SkTypeface_FCI* Create(sk_sp<SkTypeface> realTypeface,
                               sk_sp<SkFontConfigInterface> fci,
                               const FontIdentity& fi,
                               SkString familyName,
                               const SkFontStyle& style,
                               bool isFixedPitch)
```

返回 `nullptr` 如果 `realTypeface` 或 `fci` 为空。

**公共方法:**

| 方法 | 说明 |
|------|------|
| `getIdentity()` | 返回 FontConfig 字体身份标识 (文件路径、TTC 索引) |
| `onMakeClone(args)` | 克隆: 先克隆底层 typeface，再用相同的 FCI 信息包装 |

**Protected 方法:**

| 方法 | 说明 |
|------|------|
| `onGetFontDescriptor(desc, serialize)` | 填充字体描述符 |
| `onOpenStream(ttcIndex)` | 打开字体数据流 |
| `onGetFamilyName(familyName)` | 返回存储的族名 |
| `onGetFontStyle()` | 委托给基类 `SkTypeface` |
| `onGetFixedPitch()` | 委托给基类 `SkTypeface` |

**私有成员:**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFCI` | `sk_sp<SkFontConfigInterface>` | FontConfig 接口引用 |
| `fIdentity` | `FontIdentity` | 字体身份标识 (文件路径、TTC 索引等) |
| `fFamilyName` | `SkString` | 字体族名称 |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `static SkTypeface_FCI* Create(...)` | 工厂方法创建 FCI typeface |
| `const FontIdentity& getIdentity() const` | 获取 FontConfig 身份标识 |
| `sk_sp<SkTypeface> onMakeClone(const SkFontArguments&) const` | 克隆并应用新参数 |

## 内部实现细节

### 构造函数

```cpp
SkTypeface_FCI(sk_sp<SkTypeface> realTypeface,
               sk_sp<SkFontConfigInterface> fci,
               const FontIdentity& fi,
               SkString familyName,
               const SkFontStyle& style,
               bool isFixedPitch)
    : SkTypeface_proxy(std::move(realTypeface), style, isFixedPitch)
    , fFCI(std::move(fci))
    , fIdentity(fi)
    , fFamilyName(std::move(familyName))
```

- 将 `realTypeface` 传递给 `SkTypeface_proxy` 基类
- 保存 FontConfig 接口和身份信息的副本
- 使用 `std::move` 优化字符串和引用计数对象的传递

### onMakeClone - 克隆实现

```cpp
sk_sp<SkTypeface> onMakeClone(const SkFontArguments& args) const override {
    sk_sp<SkTypeface> realTypeface = SkTypeface_proxy::onMakeClone(args);
    if (!realTypeface) return nullptr;
    return sk_sp<SkTypeface>(SkTypeface_FCI::Create(
            std::move(realTypeface), fFCI, fIdentity, fFamilyName,
            this->fontStyle(), this->isFixedPitch()));
}
```

1. 先通过代理基类克隆底层 typeface（应用新的变体参数）
2. 用相同的 FCI 信息包装克隆出的 typeface
3. 保持 FontConfig 身份标识不变

### Create 工厂方法的空值检查

```cpp
if (!realTypeface || !fci) {
    return nullptr;
}
```

防止在无效输入时创建代理对象。

### onGetFontStyle / onGetFixedPitch

这两个方法显式委托给 `SkTypeface` 基类而非 `SkTypeface_proxy`，确保返回的是构造时指定的样式和等宽属性（来自 FontConfig），而不是底层 typeface 的属性。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkFontStyle.h` | 字体样式 |
| `include/core/SkRefCnt.h` | 引用计数 |
| `include/core/SkStream.h` | 数据流 |
| `include/ports/SkFontConfigInterface.h` | FontConfig 接口和 FontIdentity |
| `src/core/SkFontDescriptor.h` | 字体描述符 |
| `src/ports/SkTypeface_proxy.h` | 代理 typeface 基类 |

## 设计模式与设计决策

1. **代理模式 (Proxy)**: `SkTypeface_FCI` 是 `realTypeface` 的代理，将大部分操作委托给底层实现
2. **装饰器模式 (Decorator)**: 在底层 typeface 之上附加 FontConfig 身份信息
3. **工厂方法 + 空值守卫**: `Create()` 静态方法在参数无效时返回 nullptr
4. **身份保留**: 克隆时保持 FontConfig 身份标识不变，确保字体匹配的稳定性
5. **样式覆盖**: `onGetFontStyle()` 和 `onGetFixedPitch()` 返回 FontConfig 指定的属性，而非底层字体的实际属性

## 性能考量

- 代理模式增加了一层间接调用，但开销极小（虚函数调用级别）
- `sk_sp` 引用计数确保 FontConfig 接口和底层 typeface 的安全共享
- 克隆操作需要创建新的代理对象，但字体数据共享，内存开销小
- FontIdentity 包含文件路径字符串，拷贝时有少量分配开销

## 相关文件

- `include/ports/SkFontConfigInterface.h` — FontConfig 接口定义
- `src/ports/SkTypeface_proxy.h` — 代理 typeface 基类
- `src/ports/SkFontConfigInterface_direct.h` / `.cpp` — FontConfig 直接实现
- `src/ports/SkFontConfigInterface_direct_factory.cpp` — 单例工厂
- `src/ports/SkTypeface_FreeType.h` — 通常作为 realTypeface 的类型
