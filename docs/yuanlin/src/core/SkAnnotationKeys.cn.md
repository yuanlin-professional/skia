# SkAnnotationKeys

> 源文件
> - src/core/SkAnnotationKeys.h

## 概述

`SkAnnotationKeys` 是 Skia 图形库中用于定义标准注解键常量的工具类。它为画布注解系统提供统一的键字符串，确保注解生产者（应用层）和消费者（PDF/SVG 后端）使用一致的标识符。

## 架构位置

`SkAnnotationKeys` 位于注解系统的核心，作为键常量的中央定义点。它连接上层 API（`SkAnnotation` 函数）和底层实现（后端设备）。

```
Skia Core
  └── Annotation System
      ├── SkAnnotation.h (公共 API)
      ├── SkAnnotationKeys (键常量定义)
      │   └── 预定义标准键
      ├── SkCanvas::drawAnnotation() (传输层)
      └── 后端实现 (消费者)
          ├── SkPDFDevice
          └── SkSVGDevice
```

## 主要类与结构体

### SkAnnotationKeys

**继承关系**
- 无继承（独立工具类）

**类型**
- 纯静态类（只有静态方法）
- 无实例成员
- 无构造函数

**设计特点**
- 所有方法都是静态的
- 返回编译期字符串常量
- 作为命名空间使用

## 公共 API 函数

### URL_Key()

**签名**
```cpp
static const char* URL_Key();
```

**功能**
- 返回 URL 注解的标准键
- **返回值**: `"SkAnnotationKey_URL"`

**用途**
- 标识矩形区域与外部 URL 的关联
- 用于创建可点击链接

**使用示例**
```cpp
const char* key = SkAnnotationKeys::URL_Key();
canvas->drawAnnotation(rect, key, urlData);
```

### Define_Named_Dest_Key()

**签名**
```cpp
static const char* Define_Named_Dest_Key();
```

**功能**
- 返回定义命名目标的标准键
- **返回值**: `"SkAnnotationKey_Define_Named_Dest"`

**用途**
- 标识文档内部目标点的定义
- 创建书签和内部锚点

**使用示例**
```cpp
const char* key = SkAnnotationKeys::Define_Named_Dest_Key();
canvas->drawAnnotation(pointRect, key, nameData);
```

### Link_Named_Dest_Key()

**签名**
```cpp
static const char* Link_Named_Dest_Key();
```

**功能**
- 返回链接到命名目标的标准键
- **返回值**: `"SkAnnotationKey_Link_Named_Dest"`

**用途**
- 标识矩形区域与内部目标的链接
- 创建文档内部导航

**使用示例**
```cpp
const char* key = SkAnnotationKeys::Link_Named_Dest_Key();
canvas->drawAnnotation(rect, key, targetNameData);
```

## 内部实现细节

### 实现方式

所有方法都返回字符串字面量：
```cpp
const char* SkAnnotationKeys::URL_Key() {
    return "SkAnnotationKey_URL";
}
```

**设计选择原因**:

1. **编译期常量**
   - 字符串字面量在只读数据段
   - 零运行时开销
   - 全局唯一（地址相同）

2. **避免静态初始化**
   - 函数本地的字面量无初始化顺序问题
   - 不受静态初始化陷阱影响
   - 线程安全（只读数据）

3. **简单性**
   - 无需内存分配
   - 无析构问题
   - 调试时可读性好

### 键命名规范

所有键遵循统一命名模式：
```
"SkAnnotationKey_<功能描述>"
```

**约定**:
- 前缀 `SkAnnotationKey_` 标识 Skia 注解
- 使用下划线分隔单词
- 描述性命名（自解释）

### 扩展机制

虽然类是固定的，但系统支持自定义键：
```cpp
// 自定义注解类型
const char* customKey = "MyApp_CustomAnnotation";
canvas->drawAnnotation(rect, customKey, customData);
```

**后端处理**:
- 未知键会被忽略
- 后端根据键决定如何处理
- 无需修改 `SkAnnotationKeys` 类

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkTypes.h` | 基础类型定义 |

**说明**: 这是 Skia 中依赖最少的模块之一，只需基础类型。

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `src/core/SkAnnotation.cpp` | 使用键常量调用 `drawAnnotation` |
| `src/pdf/SkPDFDevice.cpp` | 识别和处理注解类型 |
| `src/svg/SkSVGDevice.cpp` | 处理 SVG 注解 |
| 应用层代码 | 直接或通过 `SkAnnotation` 使用 |

## 设计模式与设计决策

### 静态工具类模式
- **模式**: 只有静态方法的类
- **类似**: C++ 中模拟命名空间的常见手法
- **优势**: 清晰的组织和作用域

### 字符串常量池
- **实现**: 编译器自动优化相同字符串字面量
- **效果**: 所有 `URL_Key()` 调用返回相同地址
- **优势**: 指针比较代替字符串比较

### 开放-封闭原则
- **封闭**: 预定义键不可修改
- **开放**: 系统接受任意字符串键
- **平衡**: 标准化与灵活性兼顾

### 单一职责原则
- **职责**: 仅提供键字符串常量
- **不包含**: 注解逻辑、验证、处理
- **优势**: 清晰的边界和依赖

## 性能考量

### 性能特征

| 操作 | 开销 | 说明 |
|------|------|------|
| `URL_Key()` 调用 | ~1ns | 返回指针，可内联 |
| 字符串比较 | ~5-20ns | 后端识别键类型 |
| 内存占用 | 0 | 共享只读数据段 |

### 优化点

1. **内联优化**
   - 编译器可将函数内联为直接指针
   - Release 构建下几乎零开销

2. **指针比较**
   ```cpp
   // 快速路径：指针比较
   if (key == SkAnnotationKeys::URL_Key()) { /* ... */ }

   // 回退：字符串比较
   if (strcmp(key, SkAnnotationKeys::URL_Key()) == 0) { /* ... */ }
   ```

3. **编译期求值**
   - 字符串字面量在编译期确定
   - 无运行时初始化开销

### 对比其他方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| 字符串字面量函数（当前） | 简单、零开销 | 无类型安全 |
| `constexpr` 变量 | 编译期常量 | 静态初始化问题 |
| 枚举 + 映射表 | 类型安全 | 需要映射开销 |
| 宏定义 | 最简单 | 无命名空间、调试困难 |

**当前选择理由**: 权衡所有因素后的最优解。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkAnnotation.h` | 主要使用者 | 便利函数使用这些键 |
| `src/core/SkAnnotation.cpp` | 使用者 | 实现注解 API |
| `src/pdf/SkPDFDevice.h` | 消费者 | PDF 后端处理注解 |
| `src/svg/SkSVGDevice.h` | 消费者 | SVG 后端处理注解 |
| `include/core/SkCanvas.h` | 传输层 | `drawAnnotation` 方法 |
| `tests/AnnotationTest.cpp` | 测试 | 验证键常量正确性 |
