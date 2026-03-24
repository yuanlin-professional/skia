# SingleOwner

> 源文件: `include/private/base/SingleOwner.h`

## 概述
SingleOwner 是一个调试工具类,用于运行时验证对象只被单个线程访问,检测多线程并发访问导致的竞态条件。它通过记录当前访问者的线程 ID,在调试模式下检测违反单线程访问约定的行为。

## 架构位置
该类位于 Skia GPU 子系统(skgpu 命名空间)的调试工具层。主要用于 GPU 上下文、资源缓存等需要单线程访问保证的对象,在调试构建中提供运行时并发访问检测。

## 主要类与结构体

### SingleOwner
线程访问检测类,记录并验证访问者的线程身份。

**继承关系**: 无基类 → skgpu::SingleOwner

**关键成员变量** (仅在 SK_DEBUG 模式下存在):
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fMutex | SkMutex | 保护线程 ID 和重入计数的互斥锁 |
| fOwner | SkThreadID | 当前拥有访问权的线程 ID |
| fReentranceCount | int | 重入计数,支持同一线程的递归访问 |

### AutoEnforce
RAII 辅助类,通过作用域自动管理访问检测的进入和退出。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fFile | const char* | 调用位置的文件名 |
| fLine | int | 调用位置的行号 |
| fSO | SingleOwner* | 关联的 SingleOwner 对象指针 |

## 公共 API

### 宏定义

#### `SKGPU_ASSERT_SINGLE_OWNER(obj)`
- **功能**: 在当前作用域内断言对对象 obj 的单线程访问
- **参数**: `obj` - 指向 SingleOwner 对象的指针
- **实现**: 创建一个 AutoEnforce 局部变量,在构造时检查,在析构时退出
- **使用位置**: 在需要保护的函数开头调用
- **调试模式**: 执行检查
- **发布模式**: 编译为空操作

### SingleOwner 类方法

#### `SingleOwner()`
- **功能**: 构造一个未被任何线程拥有的 SingleOwner 对象
- **初始状态**:
  - `fOwner = kIllegalThreadID` (未拥有状态)
  - `fReentranceCount = 0`

### AutoEnforce 类方法

#### `AutoEnforce(SingleOwner* so, const char* file, int line)`
- **功能**: 构造时标记当前线程进入保护区域
- **参数**:
  - `so` - SingleOwner 对象指针
  - `file` - 调用位置的文件名(__FILE__)
  - `line` - 调用位置的行号(__LINE__)
- **行为**: 调用 `so->enter(file, line)` 进行检查

#### `~AutoEnforce()`
- **功能**: 析构时标记当前线程退出保护区域
- **行为**: 调用 `fSO->exit(fFile, fLine)`

## 内部实现细节

### enter 方法
```cpp
void enter(const char* file, int line)
```
- **加锁**: 使用 `SkAutoMutexExclusive` 保护共享状态
- **检查线程**: 验证 `fOwner == self || fOwner == kIllegalThreadID`
- **断言失败**: 如果当前线程不是所有者且对象已被其他线程拥有,触发断言
- **更新状态**:
  - 增加 `fReentranceCount`
  - 设置 `fOwner = self`
- **支持重入**: 同一线程可以多次进入(递归调用)

### exit 方法
```cpp
void exit(const char* file, int line)
```
- **加锁**: 保护共享状态
- **检查所有者**: 验证当前线程是否为所有者
- **更新状态**:
  - 减少 `fReentranceCount`
  - 如果计数归零,将 `fOwner` 重置为 `kIllegalThreadID`
- **释放所有权**: 允许其他线程访问

### 条件编译
```cpp
#if defined(SK_DEBUG)
    // 完整实现
#else
    #define SKGPU_ASSERT_SINGLE_OWNER(obj)
    class SingleOwner {}; // 空实现
#endif
```
- **调试模式**: 提供完整的检测逻辑
- **发布模式**: 编译为空操作,零开销

### 线程 ID 常量
使用 `kIllegalThreadID` 表示未被任何线程拥有的状态,这是一个无效的线程 ID 值。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkDebug.h | 调试宏定义 |
| include/private/base/SkAssert.h | SkASSERTF 断言宏 |
| include/private/base/SkMutex.h | 互斥锁,保护共享状态 |
| include/private/base/SkThreadAnnotations.h | SK_GUARDED_BY 注解 |
| include/private/base/SkThreadID.h | SkThreadID 和 SkGetThreadID |

### 被依赖的模块
- GrDirectContext (GPU 上下文)
- GrResourceCache (资源缓存)
- GrGpuResource (GPU 资源基类)
- 任何需要单线程访问保证的 GPU 对象

## 设计模式与设计决策

### RAII 模式
通过 AutoEnforce 实现自动的进入/退出管理:
- 构造时检查并获取访问权
- 析构时释放访问权
- 异常安全,即使抛出异常也能正确退出

### 宏封装
`SKGPU_ASSERT_SINGLE_OWNER` 宏隐藏实现细节:
- 自动传递 __FILE__ 和 __LINE__
- 在发布模式下完全消失
- 简化使用接口

### 重入支持
通过计数器支持同一线程的递归访问:
- 允许同一对象在调用栈上多次标记
- 仅在最外层退出时释放所有权
- 避免误报递归调用

### 调试专用
仅在调试模式下启用:
- 发布版本零开销
- 不影响最终用户性能
- 帮助开发者及早发现并发问题

## 性能考量

### 发布模式零开销
- 宏展开为空语句
- 类定义为空结构体
- 编译器完全优化掉所有调用
- 对发布版本性能无影响

### 调试模式开销
每次 ASSERT 调用的开销:
- 一次互斥锁加锁/解锁
- 线程 ID 获取和比较
- 计数器的递增/递减
- 可接受的调试开销

### 互斥锁保护
使用 `SkAutoMutexExclusive` 确保线程安全:
- 防止多线程竞争导致的检测遗漏
- 保证 fOwner 和 fReentranceCount 的一致性

## 使用场景

### GPU 上下文保护
```cpp
class GrDirectContext {
    skgpu::SingleOwner fSingleOwner;

public:
    void flush() {
        SKGPU_ASSERT_SINGLE_OWNER(&fSingleOwner);
        // 执行 flush 操作
    }

    void submit() {
        SKGPU_ASSERT_SINGLE_OWNER(&fSingleOwner);
        // 提交命令
    }
};
```

### 资源缓存访问
```cpp
class GrResourceCache {
    skgpu::SingleOwner* fSingleOwner;  // 从上下文传入

public:
    void purgeResources() {
        SKGPU_ASSERT_SINGLE_OWNER(fSingleOwner);
        // 清理资源
    }
};
```

### 递归调用场景
```cpp
void outerFunction() {
    SKGPU_ASSERT_SINGLE_OWNER(&fSingleOwner);
    // ... 一些操作
    innerFunction();  // 递归调用,不会触发断言
}

void innerFunction() {
    SKGPU_ASSERT_SINGLE_OWNER(&fSingleOwner);
    // ... 内部操作
}
```

### 检测并发访问错误
```cpp
// 错误示例:多线程并发访问
void threadA() {
    context->flush();  // 线程 A 访问
}

void threadB() {
    context->flush();  // 线程 B 同时访问 -> 触发断言!
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkThreadID.h | 提供线程 ID 获取功能 |
| include/private/base/SkMutex.h | 提供互斥锁 |
| src/gpu/GrDirectContext.cpp | 使用 SingleOwner 保护上下文 |
| src/gpu/GrResourceCache.cpp | 使用 SingleOwner 保护缓存 |

## 注意事项

### 仅用于调试
- 不能依赖此机制保证线程安全
- 仅用于检测错误的并发访问假设
- 实际的线程安全需要通过设计保证

### 单线程访问约定
- 检测的是违反单线程访问约定
- 不是一个线程安全的互斥锁
- 如果对象设计为单线程访问,则无需额外同步

### 指针传递
通常通过指针共享 SingleOwner:
```cpp
// 子对象共享父对象的 SingleOwner
GrResourceCache cache(&context->fSingleOwner);
```

### 性能分析
进行性能分析时建议禁用:
- 调试构建中互斥锁会扭曲性能数据
- 使用 RelWithDebInfo 构建或定义 NDEBUG

### 与 ThreadSanitizer 的关系
- SingleOwner 检测单线程访问约定的违反
- ThreadSanitizer 检测数据竞争
- 两者互补,SingleOwner 更轻量且针对特定场景
