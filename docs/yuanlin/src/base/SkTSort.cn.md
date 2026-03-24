# SkTSort

> 源文件: src/base/SkTSort.h

## 概述

`SkTSort` 是 Skia 中提供高效排序算法的模板库,实现了内省排序(Introsort)作为主要排序算法,并包含堆排序(Heapsort)和插入排序(Insertion Sort)作为辅助算法。内省排序结合了快速排序、堆排序和插入排序的优点,在最坏情况下也能保证 O(n log n) 的时间复杂度,同时在一般情况下保持快速排序的高性能。

模块提供了灵活的模板接口,支持自定义比较函数,适用于任意可比较的类型。所有排序算法都是原地排序,不需要额外的内存分配,且对自定义 `swap` 函数提供特化支持。

## 架构位置

```
src/base/
├── SkTSort.h            // 排序算法模板实现
├── SkMathPriv.h         // 数学工具(SkNextLog2)
└── (其他基础工具)
    ↓
src/core/
├── SkPath.cpp           // 路径点排序
├── SkCanvas.cpp         // 绘制顺序排序
└── (各种需要排序的模块)
```

该模块是基础算法层的核心组件,为 Skia 内部提供高效的通用排序能力。

## 主要类与结构体

**无类定义**,模块仅提供模板函数。

## 公共 API 函数

### 内省排序(推荐)

| 函数签名 | 功能说明 |
|---------|---------|
| `template <typename T, typename C> void SkTQSort(T* begin, T* end, const C& lessThan)` | 使用自定义比较器排序 |
| `template <typename T> void SkTQSort(T* begin, T* end)` | 使用 `operator<` 排序 |
| `template <typename T> void SkTQSort(T** begin, T** end)` | 指针数组排序,比较指向的对象 |

### 堆排序

| 函数签名 | 功能说明 |
|---------|---------|
| `template <typename T, typename C> void SkTHeapSort(T array[], size_t count, const C& lessThan)` | 使用堆排序算法 |
| `template <typename T> void SkTHeapSort(T array[], size_t count)` | 使用 `operator<` 的堆排序 |

### 插入排序

| 函数签名 | 功能说明 |
|---------|---------|
| `template <typename T, typename C> void SkTInsertionSort(T* left, int count, const C& lessThan)` | 使用插入排序(适合小数组) |

## 内部实现细节

### 内省排序(Introsort)算法

内省排序是快速排序的改进版本,通过递归深度限制避免最坏情况:

```cpp
void SkTIntroSort(int depth, T* left, int count, const C& lessThan) {
    for (;;) {
        if (count <= 32) {
            SkTInsertionSort(left, count, lessThan);  // 小数组用插入排序
            return;
        }

        if (depth == 0) {
            SkTHeapSort(left, count, lessThan);  // 深度耗尽用堆排序
            return;
        }
        --depth;

        // 快速排序分区
        T* pivot = SkTQSort_Partition(left, count, middle, lessThan);
        int pivotCount = pivot - left;

        SkTIntroSort(depth, left, pivotCount, lessThan);  // 递归左侧
        left += pivotCount + 1;
        count -= pivotCount + 1;  // 循环处理右侧
    }
}
```

**算法特点**:
1. **小数组优化**: 元素数 ≤ 32 时使用插入排序
2. **深度限制**: 最大递归深度为 2 × ⌈log₂(n-1)⌉
3. **避免最坏情况**: 深度耗尽时切换到堆排序
4. **尾递归优化**: 右侧分区使用循环而非递归

### 快速排序分区

```cpp
template <typename T, typename C>
T* SkTQSort_Partition(T* left, int count, T* pivot, const C& lessThan) {
    T pivotValue = *pivot;
    swap(*pivot, *(left + count - 1));  // 移动枢轴到末尾
    T* newPivot = left;

    while (left < right) {
        if (lessThan(*left, pivotValue)) {
            swap(*left, *newPivot);
            newPivot += 1;
        }
        left += 1;
    }
    swap(*newPivot, *(left + count - 1));  // 枢轴归位
    return newPivot;
}
```

**分区策略**:
- 选择中点作为枢轴
- Hoare 分区方案变体
- 返回枢轴最终位置

### 堆排序算法

堆排序包含两个阶段:
1. **建堆**: 自底向上调整成最大堆
2. **排序**: 反复将最大元素移到末尾并调整堆

**上浮调整**(SiftUp):
```cpp
void SkTHeapSort_SiftUp(T array[], size_t root, size_t bottom, const C& lessThan) {
    T x = array[root-1];
    // 先下沉到叶子节点
    size_t j = root << 1;
    while (j <= bottom) {
        if (j < bottom && lessThan(array[j-1], array[j])) ++j;
        array[root-1] = array[j-1];
        root = j;
        j = root << 1;
    }
    // 再上浮到正确位置
    j = root >> 1;
    while (j >= start && lessThan(array[j-1], x)) {
        array[root-1] = array[j-1];
        root = j;
        j = root >> 1;
    }
    array[root-1] = x;
}
```

这是一种优化的堆调整策略,适合小值元素。

**下沉调整**(SiftDown):
```cpp
void SkTHeapSort_SiftDown(T array[], size_t root, size_t bottom, const C& lessThan) {
    T x = array[root-1];
    size_t child = root << 1;
    while (child <= bottom) {
        if (child < bottom && lessThan(array[child-1], array[child])) {
            ++child;  // 选择较大的子节点
        }
        if (lessThan(x, array[child-1])) {
            array[root-1] = array[child-1];
            root = child;
            child = root << 1;
        } else {
            break;
        }
    }
    array[root-1] = x;
}
```

### 插入排序算法

```cpp
template <typename T, typename C>
void SkTInsertionSort(T* left, int count, const C& lessThan) {
    T* right = left + count - 1;
    for (T* next = left + 1; next <= right; ++next) {
        if (!lessThan(*next, *(next - 1))) {
            continue;  // 已经有序
        }
        T insert = std::move(*next);
        T* hole = next;
        do {
            *hole = std::move(*(hole - 1));
            --hole;
        } while (left < hole && lessThan(insert, *(hole - 1)));
        *hole = std::move(insert);
    }
}
```

**优化点**:
- 提前检查是否已有序
- 使用移动语义代替交换
- 从前向后扫描插入位置

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| include/private/base/SkTo.h | SkToInt 类型转换 |
| src/base/SkMathPriv.h | SkNextLog2 计算对数 |
| utility | std::swap, std::move |

**被依赖的模块:**

| 模块 | 使用场景 |
|------|---------|
| src/base/SkTDPQueue.h | 优先级队列排序 |
| src/core/SkPath.cpp | 路径点排序 |
| src/gpu/ | GPU 资源排序 |
| src/pathops/ | 路径操作中的几何排序 |

## 设计模式与设计决策

### 混合排序策略

内省排序结合三种算法的优点:
- **快速排序**: 平均情况最快
- **堆排序**: 最坏情况保证
- **插入排序**: 小数组高效

这种混合策略实现了"渐进最优"的排序算法。

### 模板特化技术

为指针数组提供特化版本:
```cpp
template <typename T>
void SkTQSort(T** begin, T** end) {
    SkTQSort(begin, end, [](const T* a, const T* b) { return *a < *b; });
}
```

这使得指针数组排序更加直观。

### 比较器抽象

使用泛型比较器而非固定的 `operator<`:
- 支持自定义排序逻辑
- 支持反向排序
- 支持多字段排序

### swap 特化支持

算法使用 ADL(Argument-Dependent Lookup)查找 `swap`:
```cpp
using std::swap;
swap(array[i], array[j]);  // 优先使用自定义 swap
```

这允许为自定义类型提供高效的 swap 实现。

## 性能考量

### 时间复杂度

| 算法 | 最好情况 | 平均情况 | 最坏情况 |
|------|---------|---------|---------|
| Introsort | O(n log n) | O(n log n) | O(n log n) |
| Heapsort | O(n log n) | O(n log n) | O(n log n) |
| Insertion Sort | O(n) | O(n²) | O(n²) |

### 空间复杂度

- **Introsort**: O(log n) 递归栈空间
- **Heapsort**: O(1) 原地排序
- **Insertion Sort**: O(1) 原地排序

### 性能特征

**Introsort 优势**:
- 平均情况接近快速排序性能
- 最坏情况有保证(不会退化到 O(n²))
- 小数组自动切换到插入排序
- 缓存友好的内存访问模式

**阈值选择**:
- **32**: 小数组切换到插入排序的阈值
- **2 × ⌈log₂(n-1)⌉**: 最大递归深度

这些值是基于实验和理论分析的权衡结果。

### 性能优化技术

1. **尾递归消除**: 右侧分区使用循环
2. **位运算**: 使用移位计算 2 的倍数
3. **移动语义**: 插入排序使用 `std::move` 而非 `swap`
4. **早期退出**: 插入排序检测已有序情况
5. **中点枢轴**: 减少快速排序的最坏情况概率

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| src/base/SkMathPriv.h | 提供 SkNextLog2 函数 |
| include/private/base/SkTo.h | 类型转换工具 |
| src/base/SkTDPQueue.h | 使用排序功能 |
| src/base/SkTSearch.h | 配套的搜索功能 |

## 使用示例

```cpp
#include "src/base/SkTSort.h"

// 示例 1: 基本整数数组排序
int numbers[] = {5, 2, 8, 1, 9};
SkTQSort(numbers, numbers + 5);
// 结果: [1, 2, 5, 8, 9]

// 示例 2: 使用自定义比较器(降序)
SkTQSort(numbers, numbers + 5, [](int a, int b) { return a > b; });
// 结果: [9, 8, 5, 2, 1]

// 示例 3: 结构体排序
struct Person {
    const char* name;
    int age;
};

Person people[] = {
    {"Alice", 30},
    {"Bob", 25},
    {"Charlie", 35}
};

// 按年龄排序
SkTQSort(people, people + 3, [](const Person& a, const Person& b) {
    return a.age < b.age;
});

// 示例 4: 指针数组排序
int values[] = {5, 2, 8};
int* ptrs[] = {&values[0], &values[1], &values[2]};
SkTQSort(ptrs, ptrs + 3);  // 比较指向的值,不是指针地址

// 示例 5: 多字段排序
struct Point {
    int x, y;
};

Point points[] = {{1, 2}, {1, 1}, {0, 3}};
SkTQSort(points, points + 3, [](const Point& a, const Point& b) {
    return a.x < b.x || (a.x == b.x && a.y < b.y);
});
// 结果: (0,3), (1,1), (1,2)

// 示例 6: 使用堆排序(当需要稳定的 O(n log n) 时)
int data[] = {5, 2, 8, 1, 9};
SkTHeapSort(data, 5);

// 示例 7: 小数组使用插入排序
int small[] = {3, 1, 2};
SkTInsertionSort(small, 3, [](int a, int b) { return a < b; });

// 示例 8: 自定义 swap 优化
struct BigObject {
    char data[1024];
    int key;

    friend void swap(BigObject& a, BigObject& b) {
        using std::swap;
        swap(a.key, b.key);  // 只交换关键字段
        // data 不交换,如果逻辑允许
    }
};

BigObject objects[100];
// ... 初始化
SkTQSort(objects, objects + 100, [](const BigObject& a, const BigObject& b) {
    return a.key < b.key;
});

// 示例 9: 部分排序(排序子数组)
int array[] = {9, 5, 2, 8, 1, 7};
SkTQSort(array + 1, array + 4);  // 仅排序索引 1-3
// 结果: [9, 2, 5, 8, 1, 7]

// 示例 10: 稳定性测试
struct Item {
    int key;
    int index;  // 原始索引
};

Item items[] = {{1, 0}, {2, 1}, {1, 2}, {2, 3}};
SkTQSort(items, items + 4, [](const Item& a, const Item& b) {
    return a.key < b.key;
});
// 注意: SkTQSort 不保证稳定性,相同 key 的元素顺序可能改变
```

## 注意事项

1. **不稳定排序**: Introsort 和 Heapsort 都不是稳定排序,相同元素的相对顺序可能改变
2. **比较器要求**: 比较器必须定义严格弱序(strict weak ordering)
3. **迭代器类型**: 只支持指针(随机访问迭代器),不支持链表等序列容器
4. **范围约定**: `[begin, end)` 左闭右开区间
5. **自定义 swap**: 确保自定义 swap 函数正确实现
6. **线程安全**: 排序本身是线程安全的(无全局状态),但被排序的数组需要独占访问
7. **异常安全**: 如果比较器或 swap 抛异常,数组可能处于部分排序状态

## 与 std::sort 对比

| 特性 | SkTQSort | std::sort |
|------|---------|-----------|
| 算法 | Introsort | Introsort 或类似 |
| 时间复杂度 | O(n log n) | O(n log n) |
| 稳定性 | 不稳定 | 不稳定 |
| 标准库 | 否 | 是 |
| 自定义 swap | 支持 ADL | 支持 ADL |
| 小数组阈值 | 32 | 通常 16-32 |

**选择建议**:
- 一般情况优先使用 `std::sort`
- Skia 内部代码使用 `SkTQSort` 保持一致性
- 需要稳定排序时使用 `std::stable_sort`

## 最佳实践

1. **比较器选择**: 简单类型用 lambda,复杂类型定义 `operator<`
2. **预估大小**: 如果可能,预先分配足够空间避免在排序过程中重新分配
3. **小数组**: 对于极小数组(< 10),插入排序可能更快
4. **部分排序**: 如果只需要前 k 个元素,考虑 `std::partial_sort`
5. **范围检查**: 确保 begin 和 end 有效且 begin <= end
6. **性能测试**: 对关键路径进行性能测试,选择最优算法

## 算法应用场景

1. **图形渲染**: 按深度排序绘制对象
2. **碰撞检测**: 排序边界框加速检测
3. **路径操作**: 交点排序和合并
4. **资源管理**: 按优先级或使用频率排序
5. **事件处理**: 按时间戳排序事件队列
6. **数据分析**: 统计和中位数计算

## 扩展阅读

- Introsort 算法论文(David Musser, 1997)
- 快速排序优化技术
- 堆排序原理与应用
- 插入排序的适用场景
- 排序算法稳定性分析
