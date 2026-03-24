# UniquePaintParamsID

> 源文件: src/gpu/graphite/UniquePaintParamsID.h

## 概述

`UniquePaintParamsID` 是 Skia Graphite 架构中表示绘制参数唯一标识符的轻量级类型。该类型用于标识 `PaintParamsKey`（绘制参数键）在 `ShaderCodeDictionary` 中的唯一索引，实现绘制参数的去重和快速查找。它是 Graphite 着色器编译和管线缓存系统的关键组件。

## 架构位置

```
Graphite 绘制参数系统：
  ├── PaintParams（绘制参数）
  ├── PaintParamsKey（参数键）
  ├── UniquePaintParamsID（唯一标识）★
  └── ShaderCodeDictionary（着色器字典）
```

## 主要类与结构体

### UniquePaintParamsID 类

```cpp
class UniquePaintParamsID {
public:
    static constexpr UniquePaintParamsID InvalidID() {
        return UniquePaintParamsID(kInvalidID);
    }

    constexpr UniquePaintParamsID() : fID(kInvalidID) {}
    explicit constexpr UniquePaintParamsID(uint32_t id) : fID(id) {}

    bool operator==(const UniquePaintParamsID&) const = default;
    bool operator!=(const UniquePaintParamsID&) const = default;

    bool isValid() const { return fID != kInvalidID; }
    uint32_t asUInt() const { return fID; }

private:
    static constexpr uint32_t kInvalidID = 0;
    uint32_t fID;
};
```

## 公共 API 函数

### 构造函数

```cpp
constexpr UniquePaintParamsID();  // 创建无效 ID
explicit constexpr UniquePaintParamsID(uint32_t id);  // 从整数创建
```

### InvalidID 工厂函数

```cpp
static constexpr UniquePaintParamsID InvalidID();
```

返回表示无效的 ID（值为 0）。

### isValid

```cpp
bool isValid() const;
```

检查 ID 是否有效（非 0）。

### asUInt

```cpp
uint32_t asUInt() const;
```

获取底层的整数值。

### 比较运算符

```cpp
bool operator==(const UniquePaintParamsID&) const;
bool operator!=(const UniquePaintParamsID&) const;
```

支持相等性比较。

## 内部实现细节

### 内存布局

```cpp
class UniquePaintParamsID {
    uint32_t fID;  // 仅4字节
};
```

### 无效 ID 约定

ID 0 保留为无效值：
```cpp
static constexpr uint32_t kInvalidID = 0;
```

### 类型安全

使用类包装而非裸 `uint32_t`，避免与其他整数混淆。

## 依赖关系

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `PaintParamsKey` | 标识参数键 |
| `ShaderCodeDictionary` | 索引着色器节点树 |
| `GraphicsPipelineDesc` | 管线描述符 |
| `Recorder` | 绘制参数查找 |

## 设计模式与设计决策

### 值对象

不可变的值类型，支持拷贝和比较。

### 类型安全封装

避免使用裸整数，防止类型混淆。

### constexpr 支持

所有操作都是 `constexpr`，支持编译时计算。

### 关键设计决策

1. **4字节大小**: 最小化内存占用
2. **无效值为0**: 简化默认构造和检查
3. **显式构造**: 防止隐式转换
4. **值语义**: 可按值传递，无虚函数

## 性能考量

### 内存效率

- 仅4字节，可内联存储
- 无虚函数表指针

### 比较效率

- 整数比较，O(1) 复杂度
- 可直接用作哈希键

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/PaintParamsKey.h` | 绘制参数键 |
| `src/gpu/graphite/ShaderCodeDictionary.h` | 着色器字典 |
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 管线描述符 |
