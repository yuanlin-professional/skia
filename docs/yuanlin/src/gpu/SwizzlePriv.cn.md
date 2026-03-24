# SwizzlePriv

> 源文件: src/gpu/SwizzlePriv.h

## 概述

`SwizzlePriv` 是一个极简的辅助头文件，提供了对 `Swizzle` 类私有构造函数的受控访问。它包含一个单一的工具类 `SwizzleCtorAccessor`，允许需要直接从 16 位键值构造 `Swizzle` 对象的内部模块绕过公共 API 的限制。

这是 Skia 中常见的"私有访问器"设计模式的典型应用，用于在保持封装性的同时，为特定的受信任模块提供特权访问。该文件仅 26 行代码（包括注释和空行），体现了 Skia 在设计上的精简和专注。

## 架构位置

```
skia/
└── src/gpu/
    ├── Swizzle.h         # Swizzle 主类定义
    ├── Swizzle.cpp       # Swizzle 实现
    └── SwizzlePriv.h     # 本模块：私有构造访问器
```

`SwizzlePriv.h` 位于 `src/gpu/` 目录，与 `Swizzle.h` 在同一层级。它不暴露给公共 API（位于 `include/` 目录），仅供 Skia GPU 内部模块使用。

## 主要类与结构体

### SwizzleCtorAccessor 类

**继承关系**: 无继承

**关键成员**:

| 类型 | 名称 | 说明 |
|------|------|------|
| static method | `Make(uint16_t key)` | 从 16 位键值创建 `Swizzle` 对象 |

**访问权限**:
- 该类被 `Swizzle` 声明为友元（`friend class SwizzleCtorAccessor;`）
- 因此可以调用 `Swizzle` 的私有构造函数 `explicit constexpr Swizzle(uint16_t key)`

## 公共 API 函数

### Make 方法

```cpp
static Swizzle Make(uint16_t key)
```

**功能**: 从紧凑的 16 位键值直接构造 `Swizzle` 对象
**参数**: `key` - 编码了 4 个通道索引的 16 位整数（每通道 4 位）
**返回**: 新构造的 `Swizzle` 对象
**用途**:
- 反序列化 swizzle（从缓存或网络加载）
- 从预计算的键值表创建 swizzle
- 性能敏感代码路径中避免字符串解析

**示例**:
```cpp
// 直接从键值创建，等价于 Swizzle("bgra")
uint16_t bgraKey = 0x3012;  // a=3, b=0, g=1, r=2
Swizzle s = SwizzleCtorAccessor::Make(bgraKey);
```

## 内部实现细节

### 友元访问机制

`Swizzle` 类的私有构造函数：
```cpp
explicit constexpr Swizzle(uint16_t key) : fKey(key) {}
```

该构造函数标记为 `private`，防止外部直接使用，但通过友元声明允许 `SwizzleCtorAccessor` 访问：
```cpp
// In Swizzle.h
class Swizzle {
private:
    friend class SwizzleCtorAccessor;
    explicit constexpr Swizzle(uint16_t key) : fKey(key) {}
    // ...
};
```

### 访问器模式的优势

相比其他实现方式的优势：

| 实现方式 | 缺点 | SwizzlePriv 的优势 |
|---------|------|-------------------|
| 公共构造函数 | 破坏封装，用户可能传入非法键值 | 保持公共 API 干净 |
| 全局友元函数 | 污染全局命名空间 | 局部化在辅助类中 |
| 继承访问 | 引入不必要的继承层次 | 无继承开销 |
| 宏或模板技巧 | 增加代码复杂度 | 简洁明了 |

### 键值格式

16 位键值的位布局（与 `Swizzle.h` 中的格式一致）：
```
位 [15:12]: 第 3 个输出通道 (a) 的源索引
位 [11:8]:  第 2 个输出通道 (b) 的源索引
位 [7:4]:   第 1 个输出通道 (g) 的源索引
位 [3:0]:   第 0 个输出通道 (r) 的源索引

索引含义:
0 = 'r', 1 = 'g', 2 = 'b', 3 = 'a', 4 = '0', 5 = '1'
```

**示例计算** (手动构造 "rgb1"):
```cpp
uint16_t rgb1 = (5 << 12) | (2 << 8) | (1 << 4) | (0 << 0);
// = 0x5210
Swizzle s = SwizzleCtorAccessor::Make(rgb1);
assert(s == Swizzle::RGB1());
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `src/gpu/Swizzle.h` | 提供 `Swizzle` 类定义 |
| `<cstdint>` | `uint16_t` 类型定义 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| 纹理格式转换模块 | 从硬件格式描述符生成 swizzle |
| Shader 代码生成 | 在编译时从键值表生成 swizzle |
| 缓存和序列化 | 读取/写入紧凑格式的 swizzle |
| 性能敏感路径 | 避免字符串解析的运行时开销 |

## 设计模式与设计决策

### 设计模式

1. **私有访问器模式 (Private Accessor Pattern)**: 核心设计模式
2. **友元注入模式 (Friend Injection)**: 通过友元提供受控的私有访问
3. **静态工厂模式 (Static Factory)**: `Make` 方法是静态工厂函数

### 设计决策

**为什么不直接公开构造函数？**
- **类型安全**: 用户可能传入非法的键值（如使用了 6-15 的通道索引）
- **API 清晰度**: 公共 API 鼓励使用语义明确的字符串构造函数
- **未来扩展**: 如果键值格式变化，可在访问器中添加验证或转换逻辑

**为什么不使用友元函数？**
- **命名空间**: 类方法比全局函数更易管理
- **可发现性**: IDE 自动补全能找到 `SwizzleCtorAccessor::Make`
- **一致性**: Skia 中类似场景多使用 `*Priv` 类

**为什么不使用 public static 方法？**
- 如果 `Swizzle::MakeFromKey()` 是公共方法，仍然需要访问私有构造函数
- 访问器类提供了额外的间接层，强调"这是内部使用"的语义

**为什么文件这么小？**
- **单一职责**: 该模块只做一件事——提供私有构造访问
- **头文件实现**: 所有代码都在头文件中，无需 .cpp 文件
- **编译时求值**: `Make` 方法可能被内联和编译时计算

### 命名约定

Skia 中的 `*Priv.h` 文件通常表示：
- 内部实现细节
- 受控的私有访问
- 不稳定的 API（可能随版本变化）

类似文件示例：
- `SkCanvasPriv.h`
- `SkPathPriv.h`
- `SkRectPriv.h`

## 性能考量

### 编译时优化

由于 `Make` 方法调用的 `Swizzle` 构造函数是 `constexpr`，整个调用链可在编译时计算：

```cpp
// 编译时计算
constexpr uint16_t key = 0x3012;
constexpr Swizzle s = SwizzleCtorAccessor::Make(key);
// s 的值在编译时已确定
```

### 运行时性能

**内联**:
- `Make` 是简单的单行函数，编译器通常会内联
- 无虚函数调用或间接跳转开销

**内存访问**:
- 仅涉及一个 16 位整数的拷贝
- 无堆分配或指针追踪

**性能比较**:

| 构造方式 | 运行时开销 | 编译时可用 |
|---------|-----------|-----------|
| `Swizzle("rgba")` | 字符串解析 + 位操作 | 是 (constexpr) |
| `SwizzleCtorAccessor::Make(0x3210)` | 单次整数拷贝 | 是 (constexpr) |
| 差异 | ~10-20 条指令 vs ~1 条指令 | - |

### 使用建议

**何时使用 SwizzleCtorAccessor**:
- 从预计算的查找表创建 swizzle
- 反序列化场景（读取二进制格式）
- 性能关键路径（避免字符串解析）

**何时使用公共 API**:
- 可读性优先的代码
- 配置或初始化代码
- 字符串构造已是 constexpr 的场景

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/Swizzle.h` | 依赖 | 提供 `Swizzle` 类和友元声明 |
| `src/gpu/Swizzle.cpp` | 间接 | 实现 `Swizzle` 的非 constexpr 方法 |
| GPU 纹理格式代码 | 使用 | 从硬件格式生成 swizzle |
| Shader 生成器 | 使用 | 在 shader 代码中嵌入 swizzle |

## 使用示例

### 示例 1: 从查找表创建 Swizzle

```cpp
// 纹理格式到 swizzle 的映射表
static constexpr uint16_t kFormatSwizzles[] = {
    0x3210,  // RGBA -> rgba
    0x3012,  // BGRA -> bgra
    0x0003,  // RG -> ra00
    // ...
};

Swizzle getSwizzleForFormat(TextureFormat fmt) {
    return SwizzleCtorAccessor::Make(kFormatSwizzles[fmt]);
}
```

### 示例 2: 序列化和反序列化

```cpp
// 序列化
void serializeSwizzle(const Swizzle& s, OutputStream& out) {
    uint16_t key = s.asKey();
    out.write(&key, sizeof(key));
}

// 反序列化
Swizzle deserializeSwizzle(InputStream& in) {
    uint16_t key;
    in.read(&key, sizeof(key));
    return SwizzleCtorAccessor::Make(key);
}
```

### 示例 3: 性能敏感路径

```cpp
// 假设已知需要的 swizzle 键值
inline Swizzle getOutputSwizzle() {
    // 避免 constexpr 字符串解析的潜在开销
    static const uint16_t kOutputSwizzleKey = 0x3210;
    return SwizzleCtorAccessor::Make(kOutputSwizzleKey);
}
```

## 代码审查要点

在代码审查中遇到 `SwizzleCtorAccessor::Make` 时，应检查：

1. **是否必要**: 能否使用公共 API（如 `Swizzle("rgba")`）？
2. **键值正确性**: 16 位键值是否符合 swizzle 格式规范？
3. **常量表达式**: 能否标记为 `constexpr` 以便编译时计算？
4. **注释**: 是否添加注释说明键值的含义（如 `0x3012 = "bgra"`）？

## 总结

`SwizzlePriv.h` 是一个极其精简但设计精良的模块，展示了如何在 C++ 中：
- 平衡封装性和灵活性
- 提供受控的私有访问
- 保持公共 API 的简洁性
- 支持性能敏感的内部实现

尽管只有 26 行代码，它在 Skia GPU 渲染管线中扮演着重要的支持角色，使得纹理格式处理和 shader 生成等模块能够高效地操作 swizzle 对象。
