# SkSL Setting - 编译期设置表达式

> 源文件:
> - `src/sksl/ir/SkSLSetting.h`
> - `src/sksl/ir/SkSLSetting.cpp`

## 概述

`Setting` 表示 SkSL IR 中的编译期常量设置,例如 `sk_Caps.integerSupport`。这些 IR 节点用于在组装模块时引用 GPU 能力标志(`ShaderCaps`),在实际编译时(当 `ShaderCaps` 可用时)被替换为相应的布尔字面量值。

`Setting` 节点实现了一种延迟求值机制:在模块编译阶段,GPU 能力信息尚未确定,因此使用 `Setting` 节点作为占位符;在最终编译阶段,这些节点被解析为具体的 `true` 或 `false` 字面量。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── Setting  <-- 本文件
            └── 引用 ShaderCaps 成员指针
```

`Setting` 是一种特殊的表达式类型,仅在内置模块代码中使用(通过 `AllowsPrivateIdentifiers` 保护)。

## 主要类与结构体

### `Setting`

继承自 `Expression`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fCapsPtr` | `CapsPtr` (即 `const bool ShaderCaps::*`) | 指向 ShaderCaps 中布尔成员的成员指针 |

`CapsPtr` 是 C++ 成员指针类型,指向 `ShaderCaps` 结构体中的某个 `bool` 成员。

## 公共 API 函数

### `Setting::Convert`

```cpp
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           const std::string_view& name);
```

从能力标志名称创建 Setting 表达式:
1. 验证当前程序类型允许私有标识符(仅内置代码可以使用 `sk_Caps`)
2. 在查找表中查找名称对应的成员指针
3. 调用 `Make()` 创建节点

### `Setting::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        CapsPtr capsPtr);
```

创建 Setting 节点,类型始终为 `bool`。

### `Setting::toLiteral`

```cpp
std::unique_ptr<Expression> toLiteral(const ShaderCaps& caps) const;
```

将 Setting 节点解析为实际的布尔字面量值。使用成员指针语法 `caps.*fCapsPtr` 获取值。

### `Setting::name`

```cpp
std::string_view name() const;
```

通过反向查找表获取此 Setting 的名称。

## 内部实现细节

### 能力标志查找表

使用 `THashMap` 存储字符串名称到 `CapsPtr` 的映射,通过 `SkNoDestructor` 实现延迟初始化的全局单例:

| 名称 | ShaderCaps 成员 |
|------|-----------------|
| `mustDoOpBetweenFloorAndAbs` | `fMustDoOpBetweenFloorAndAbs` |
| `mustGuardDivisionEvenAfterExplicitZeroCheck` | `fMustGuardDivisionEvenAfterExplicitZeroCheck` |
| `atan2ImplementedAsAtanYOverX` | `fAtan2ImplementedAsAtanYOverX` |
| `floatIs32Bits` | `fFloatIs32Bits` |
| `integerSupport` | `fIntegerSupport` |
| `builtinDeterminantSupport` | `fBuiltinDeterminantSupport` |
| `rewriteMatrixVectorMultiply` | `fRewriteMatrixVectorMultiply` |
| `PerlinNoiseRoundingFix` | `fPerlinNoiseRoundingFix` |

### 名称反向查找

`name()` 方法通过遍历整个查找表找到与 `fCapsPtr` 匹配的条目,效率不高但此方法仅用于描述/调试。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLExpression.h` | 基类 |
| `SkSLUtil.h` | `ShaderCaps` 结构体 |
| `SkSLLiteral.h` | `toLiteral()` 创建布尔字面量 |
| `SkSLBuiltinTypes.h` | `fBool` 类型 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLProgramSettings.h` | 程序类型检查(AllowsPrivateIdentifiers) |
| `SkTHash.h` | 查找表实现 |
| `SkNoDestructor.h` | 全局单例查找表 |

## 设计模式与设计决策

1. **延迟求值**: Setting 节点在模块编译时作为占位符,最终编译时解析为字面量,实现了两阶段编译的灵活性
2. **成员指针**: 使用 C++ 成员指针(`const bool ShaderCaps::*`)直接引用结构体成员,类型安全且高效
3. **访问控制**: 通过 `AllowsPrivateIdentifiers` 限制 `sk_Caps` 仅在内置代码中使用
4. **静态查找表**: 使用 `SkNoDestructor` 确保查找表在进程生命周期内存在,避免静态析构顺序问题

## 性能考量

- 查找表查找是 O(1) 哈希表操作
- `toLiteral()` 仅涉及一次成员指针解引用和字面量创建
- `name()` 的反向查找是 O(n) 遍历,但仅在调试/描述时使用
- 查找表使用 `SkNoDestructor` 包装,确保全局单例在进程退出时不被析构,避免静态析构顺序问题
- Setting 节点类型固定为 `bool`,不需要运行时类型检查

### 两阶段编译流程

Setting 节点的生命周期跨越两个编译阶段:

1. **模块编译阶段**: 内置模块(如 `sksl_shared.sksl`)被编译时,`ShaderCaps` 不可用。此时 `sk_Caps.integerSupport` 等表达式被创建为 `Setting` IR 节点。

2. **程序编译阶段**: 用户着色器代码被编译时,`ShaderCaps` 已知。此时模块中的 `Setting` 节点通过 `toLiteral()` 被替换为具体的 `true`/`false` 字面量,启用后续的常量折叠和死代码消除。

### 安全限制

`sk_Caps` 名称空间仅对"允许私有标识符"的程序类型可用。这包括内部模块代码,但不包括:
- Runtime Shader
- Runtime Color Filter
- Runtime Blender

这些公共 Runtime Effect 类型不能直接访问 GPU 能力标志,确保了跨平台的一致行为。

## 相关文件

- `src/sksl/SkSLUtil.h` -- `ShaderCaps` 结构体定义
- `src/sksl/ir/SkSLLiteral.h` -- 字面量(Setting 的解析结果)
- `src/sksl/SkSLProgramSettings.h` -- 程序设置和 `AllowsPrivateIdentifiers`
- `src/sksl/SkSLBuiltinTypes.h` -- 内置类型(`fBool`)
