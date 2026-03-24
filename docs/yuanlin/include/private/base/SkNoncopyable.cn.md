# SkNoncopyable 不可拷贝基类

> 源文件: `include/private/base/SkNoncopyable.h`

## 概述
SkNoncopyable 是一个标记为已废弃 (DEPRECATED) 的基类,用于禁止派生类的拷贝操作。该类通过删除拷贝构造函数和拷贝赋值运算符实现不可拷贝语义,同时允许移动操作。现代 C++ 代码推荐直接在类中删除拷贝函数,而非继承此基类。

## 架构位置
位于 Skia 基础工具层 (private/base),是一个通用的 CRTP (Curiously Recurring Template Pattern) 风格基类,但实际上不使用模板。历史遗留代码中许多类继承自此类。

## 主要类与结构体

### SkNoncopyable

**继承关系**: 无基类

**职责**:
- 禁止拷贝构造和拷贝赋值
- 允许移动构造和移动赋值
- 提供显式的不可拷贝语义标记

**特殊成员函数**:
| 函数 | 实现 | 说明 |
|------|------|------|
| 默认构造函数 | `= default` | 允许默认构造 |
| 拷贝构造函数 | `= delete` | 禁止拷贝 |
| 拷贝赋值运算符 | `= delete` | 禁止拷贝赋值 |
| 移动构造函数 | `= default` | 允许移动 |
| 移动赋值运算符 | `= default` | 允许移动 |

**导出标记**: 使用 `SK_API` 宏标记,支持跨模块使用

## 设计细节

### 删除拷贝操作
```cpp
private:
    SkNoncopyable(const SkNoncopyable&) = delete;
    SkNoncopyable& operator=(const SkNoncopyable&) = delete;
```
- 声明为 `private` 增强意图表达 (虽然 `= delete` 已足够)
- 编译期阻止拷贝尝试
- 提供清晰的编译错误信息

### 允许移动操作
```cpp
SkNoncopyable(SkNoncopyable&&) = default;
SkNoncopyable& operator =(SkNoncopyable&&) = default;
```
- 显式默认化移动操作
- 允许派生类支持移动语义
- 符合现代 C++ 的 Rule of Five

### 公开默认构造
```cpp
public:
    SkNoncopyable() = default;
```
允许派生类正常构造,不引入额外开销。

## 使用模式

### 传统用法 (已废弃)
```cpp
class MyResource : public SkNoncopyable {
public:
    MyResource() { ... }
    ~MyResource() { ... }

    // 自动获得不可拷贝特性
};

MyResource r1;
MyResource r2 = r1;  // 编译错误: 拷贝被禁止
MyResource r3 = std::move(r1);  // OK: 允许移动
```

### 推荐的现代替代方案
```cpp
class MyResource {
public:
    MyResource() = default;
    ~MyResource() = default;

    // 显式删除拷贝操作
    MyResource(const MyResource&) = delete;
    MyResource& operator=(const MyResource&) = delete;

    // 显式允许移动操作 (可选)
    MyResource(MyResource&&) = default;
    MyResource& operator=(MyResource&&) = default;
};
```

## 为何标记为废弃

### 现代 C++ 的更好实践
1. **直接性**: 直接在类中声明意图更清晰
2. **可见性**: 不需要查看基类定义就能理解接口
3. **灵活性**: 可以选择性地允许移动或完全禁止
4. **避免继承开销**: 虽然空基类优化通常生效,但还是有微小开销

### Rule of Five/Zero
现代 C++ 倾向于:
- **Rule of Zero**: 让编译器生成所有特殊成员函数
- **Rule of Five**: 如需自定义,显式声明所有五个特殊成员函数

`SkNoncopyable` 处于两者之间,不够明确。

### 编译器生成的移动操作
如果不继承 `SkNoncopyable`,仅删除拷贝操作:
```cpp
class MyClass {
    MyClass(const MyClass&) = delete;
    MyClass& operator=(const MyClass&) = delete;
    // 编译器不会自动生成移动操作
};
```
需要显式默认化或实现移动操作。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkAPI.h` | SK_API 导出宏 |

### 被依赖的模块
历史遗留代码中的许多类:
- `SkCanvas` (部分版本)
- `SkSurface`
- 资源管理类
- 缓存类

## 迁移指南

### 从 SkNoncopyable 迁移
**旧代码**:
```cpp
class MyClass : public SkNoncopyable {
    // ...
};
```

**新代码**:
```cpp
class MyClass {
public:
    MyClass(const MyClass&) = delete;
    MyClass& operator=(const MyClass&) = delete;
    MyClass(MyClass&&) = default;
    MyClass& operator=(MyClass&&) = default;

    // ...
};
```

### 如果不需要移动
```cpp
class MyClass {
public:
    MyClass(const MyClass&) = delete;
    MyClass& operator=(const MyClass&) = delete;
    MyClass(MyClass&&) = delete;
    MyClass& operator=(MyClass&&) = delete;

    // ...
};
```

### 使用宏 (团队一致性)
某些项目定义宏简化声明:
```cpp
#define SK_DISALLOW_COPY_AND_ASSIGN(TypeName) \
    TypeName(const TypeName&) = delete;       \
    TypeName& operator=(const TypeName&) = delete

class MyClass {
    SK_DISALLOW_COPY_AND_ASSIGN(MyClass);
    // ...
};
```

## 性能考量

### 空基类优化 (Empty Base Optimization)
```cpp
class Derived : public SkNoncopyable {
    int data;
};

sizeof(Derived) == sizeof(int);  // 通常为 true
```
编译器通常优化掉空基类的存储开销,但仍有微小影响:
- RTTI 信息增加
- 虚表指针 (如果基类有虚函数)

### 移动操作性能
`= default` 的移动操作通常与手写版本性能相同,编译器可充分优化。

## 历史背景

### 起源
- 源自 2006 年的 Android Open Source Project
- 当时 C++11 尚未普及,`= delete` 不可用
- 通过私有未实现的拷贝函数实现不可拷贝

### 演进
```cpp
// C++03 风格
class SkNoncopyable {
    SkNoncopyable(const SkNoncopyable&);  // 未实现
    void operator=(const SkNoncopyable&); // 未实现
};

// C++11 风格 (当前)
class SkNoncopyable {
    SkNoncopyable(const SkNoncopyable&) = delete;
    SkNoncopyable& operator=(const SkNoncopyable&) = delete;
};
```

### 为何保留
虽然标记为废弃,但仍保留在代码库中:
- 大量历史代码依赖
- 逐步迁移中
- ABI 兼容性考量

## 相关概念

### boost::noncopyable
`SkNoncopyable` 的设计受 Boost 库的 `boost::noncopyable` 启发,提供类似功能。

### std::unique_ptr 作为替代
对于资源管理类,`std::unique_ptr` 成员可隐式提供不可拷贝语义:
```cpp
class MyClass {
    std::unique_ptr<Resource> resource;
    // 自动获得不可拷贝特性
};
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkAPI.h` | 提供导出宏 |
| 各种 Skia 类 | 历史上的派生类 |

## 总结
`SkNoncopyable` 是 Skia 历史遗留的工具类,在现代 C++ 中已不推荐使用。新代码应直接在类定义中显式删除拷贝操作,提供更清晰的接口和更好的可维护性。该类的保留主要是为了向后兼容性。
