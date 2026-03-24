# SkRecordPattern

> 源文件: src/core/SkRecordPattern.h

## 概述

`SkRecordPattern` 提供了一套强大的模式匹配框架,用于在 `SkRecord` 中搜索特定的命令序列模式。该模块定义了各种匹配器(Matcher)和模式(Pattern)组合子,使得优化 pass 可以声明式地描述需要匹配的命令模式,并在匹配成功时提取相关数据。这是 `SkRecordOpts` 优化系统的基础设施。

## 架构位置

`SkRecordPattern` 位于 Skia 录制系统的优化支持层:
- 被 `SkRecordOpts` 用于实现各种优化 pass
- 在 `SkRecord` 上运行模式搜索
- 提供类型安全的命令序列匹配
- 支持贪婪匹配和组合匹配
- 使得优化逻辑清晰且易于维护

## 主要类与结构体

### 匹配器(Matchers)

#### Is<T>

**功能:** 匹配类型为 `T` 的命令,并存储指向该命令的指针。

**成员:**
- `type* fPtr`: 匹配的命令指针

**方法:**
- `type* get()`: 获取存储的指针
- `bool operator()(T* ptr)`: 匹配成功,存储指针并返回 true
- `bool operator()(U*)`: 类型不匹配,返回 false

**示例:**
```cpp
Is<Save> save;
if (record->mutate(i, save)) {
    // save.get() 指向 Save 命令
}
```

#### IsDraw

**功能:** 匹配任何绘制命令,并存储其 paint 指针(可能为 nullptr)。

**成员:**
- `SkPaint* fPaint`: 匹配命令的 paint

**匹配逻辑:**
- `kDrawWithPaint_Tag`: 有 paint 的绘制命令,提取 paint
- `kDraw_Tag` (仅此标签): 无 paint 的绘制命令,fPaint 设为 nullptr
- 否则: 非绘制命令,返回 false

**辅助方法:**
- `AsPtr(Optional<T>& x)`: 从 Optional 提取指针
- `AsPtr(T& x)`: 从引用获取地址

#### IsSingleDraw

**功能:** 匹配单次绘制命令(排除 MultiDraw 标签)。

**差异:** 与 `IsDraw` 类似,但排除:
- `DrawAtlas`
- `DrawVertices`
- `DrawMesh`
- `DrawPoints`
- `DrawEdgeAAImageSet`

**原因:** 这些命令可能绘制多个重叠的图元,应用某些优化(如合并 SaveLayer 透明度)会改变自混合行为。

#### Not<Matcher>

**功能:** 逻辑非,匹配 `Matcher` 不匹配的命令。

**特点:** 不存储数据。

**示例:**
```cpp
Not<Is<Save>> notSave;
```

#### Or<First, Rest...>

**功能:** 逻辑或,匹配多个 Matcher 中的任意一个。

**实现:** 递归模板,逐个尝试 matcher。

**特点:** 不存储数据。

**示例:**
```cpp
Or<Is<Save>, Is<SaveLayer>, Is<Restore>> saveOrRestore;
```

#### Greedy<Matcher>

**功能:** 贪婪匹配,尽可能多地连续匹配 `Matcher`。

**特点:**
- 可以匹配 0 次或多次
- 不存储数据
- 在 `Pattern` 中特殊处理

**示例:**
```cpp
Greedy<IsDraw> manyDraws;  // 匹配 0 或多个绘制命令
```

### 模式(Pattern)

#### Pattern<...Matchers>

**功能:** 顺序匹配一系列 Matcher。

**模板参数:** 可变数量的 Matcher 类型

**关键方法:**

##### match

```cpp
int match(SkRecord* record, int i)
```

**功能:** 从索引 `i` 开始尝试匹配。

**返回值:**
- 成功: 返回匹配结束位置的下一个索引
- 失败: 返回 0

**实现:** 递归匹配每个 Matcher。

##### search

```cpp
bool search(SkRecord* record, int* begin, int* end)
```

**功能:** 从 `*end` 开始搜索第一个匹配的区间。

**参数:**
- `begin`: 输出匹配开始位置
- `end`: 输入搜索起始位置,输出匹配结束位置

**返回值:**
- `true`: 找到匹配,`[*begin, *end)` 为匹配区间
- `false`: 未找到匹配

**算法:**
```cpp
for (*begin = *end; *begin < record->count(); ++(*begin)) {
    *end = this->match(record, *begin);
    if (*end != 0) {
        return true;
    }
}
return false;
```

##### 数据提取

```cpp
template <typename T> T* first()
template <typename T> T* second()
template <typename T> T* third()
template <typename T> T* fourth()
```

**功能:** 从匹配的 Matcher 中提取存储的数据。

**实现:** 递归委托到 `fRest` 的对应方法。

**示例:**
```cpp
Pattern<Is<SaveLayer>, IsDraw, Is<Restore>> pattern;
if (pattern.search(&record, &begin, &end)) {
    SaveLayer* saveLayer = pattern.first<SaveLayer>();
    SkPaint* drawPaint = pattern.second<SkPaint>();
    // ...
}
```

## 公共 API 函数

### Pattern<> (空模式)

**功能:** 递归终止,直接返回传入的索引。

```cpp
int match(SkRecord*, int i) { return i; }
```

### matchFirst 方法

#### 普通 Matcher 版本

```cpp
template <typename T>
int matchFirst(T* first, SkRecord* record, int i)
```

**逻辑:**
- 如果 `i < record->count()` 且 `record->mutate(i, *first)` 成功
- 返回 `i + 1`
- 否则返回 0

#### Greedy Matcher 版本

```cpp
template <typename T>
int matchFirst(Greedy<T>* first, SkRecord* record, int i)
```

**逻辑:**
- 循环匹配直到失败或到达末尾
- 返回匹配停止的位置(可能是 `i` 如果一次都不匹配)
- 如果到达末尾返回 0(特殊处理)

**关键:** Greedy 匹配器会尽可能多地消耗命令。

## 内部实现细节

### 递归模板展开

Pattern 使用递归模板实现:
- `Pattern<First, Rest...>` 处理第一个 Matcher
- `fRest` 是 `Pattern<Rest...>` 处理剩余 Matcher
- `Pattern<>` 终止递归

### 类型安全的数据提取

通过模板方法 `first<T>()`、`second<T>()` 等提取数据:
- 编译期类型检查
- 避免运行时类型转换
- 清晰的 API

### Greedy 的特殊处理

Greedy 匹配器通过重载 `matchFirst` 实现:
- 普通匹配器: 匹配一次
- Greedy 匹配器: 循环匹配直到失败

这允许表达式如:
```cpp
Pattern<Is<Save>, Greedy<IsDraw>, Is<Restore>>
// 匹配: Save 后跟任意数量的绘制命令,再跟 Restore
```

### search 的线性扫描

`search` 方法简单地从 `*end` 开始逐个位置尝试匹配:
- 时间复杂度: O(n * m),n 是记录长度,m 是模式长度
- 实际性能: 大多数位置快速失败(第一个 matcher 不匹配)

### 数据提取的链式委托

```cpp
template <typename T> T* second() {
    return fRest.template first<T>();
}
```

- `second` 委托给 `fRest` 的 `first`
- `third` 委托给 `fRest` 的 `second`
- 编译期解析,无运行时开销

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkRecord` | 被搜索的记录 |
| `SkRecords` | 命令类型和标签 |
| `SkTLogic` | 模板元编程工具 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkRecordOpts` | 使用模式匹配实现优化 |

## 设计模式与设计决策

### 1. 组合子模式(Combinator Pattern)
小的 Matcher 可以组合成复杂的 Pattern,声明式描述匹配逻辑。

### 2. 访问者模式(Visitor Pattern)
Matcher 的 `operator()` 实现了类型安全的访问者。

### 3. 策略模式(Strategy Pattern)
不同的 Matcher 实现不同的匹配策略。

### 4. 模板元编程(Template Metaprogramming)
使用递归模板和 SFINAE 实现编译期多态。

### 5. 延迟求值(Lazy Evaluation)
只在 `search` 找到匹配时才提取数据。

### 6. 零成本抽象(Zero-Cost Abstraction)
所有组合和委托都在编译期解析,无运行时开销。

### 7. 类型安全(Type Safety)
通过模板参数确保类型正确,避免运行时类型转换。

## 性能考量

### 1. 编译期优化
- 所有模板递归在编译期完成
- 生成的代码接近手写循环的效率

### 2. 内联友好
- 所有方法都很小,适合内联
- 标记为 `SK_ALWAYS_INLINE` 强制内联关键路径

### 3. 快速失败
- 第一个 Matcher 不匹配时立即返回
- 大多数搜索很快失败

### 4. 无动态分配
- 所有状态存储在栈上
- Pattern 对象可以重用

### 5. 缓存友好
- 线性扫描 SkRecord,良好的空间局部性

### 6. 标签过滤
- 使用位运算快速检查命令标签
- 避免不必要的类型检查

### 7. Greedy 效率
- Greedy 匹配器连续扫描,无回溯
- 适合表达 "0 或多个" 的模式

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkRecord.h` | 被搜索的记录 |
| `src/core/SkRecords.h` | 命令类型和标签 |
| `src/core/SkRecordOpts.h` | 使用模式匹配的优化 |
| `include/private/base/SkTLogic.h` | 模板元编程工具 |
