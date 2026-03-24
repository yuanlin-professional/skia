# SkAudioPlayer

> 源文件: modules/audioplayer/SkAudioPlayer.h, modules/audioplayer/SkAudioPlayer.cpp

## 概述

`SkAudioPlayer` 是 Skia 提供的跨平台音频播放器抽象基类，为音频文件的加载、播放、暂停、停止、时间控制及音量调节提供统一接口。该类采用工厂方法模式和模板方法模式，将具体的音频解码和播放逻辑委托给平台相关的子类实现（如 Oboe、SFML、macOS AudioToolbox 等）。

主要功能包括：
- 从 `SkData` 对象加载音频数据
- 控制播放状态（播放、暂停、停止）
- 时间定位和归一化时间控制
- 播放速率和音量调节
- 统一的跨平台音频播放接口

## 架构位置

`SkAudioPlayer` 位于 Skia 的 modules/audioplayer 模块中，是音频播放功能的核心抽象层。它在架构中的位置：

```
Skia 框架
└── modules/
    └── audioplayer/
        ├── SkAudioPlayer.h/cpp        (抽象基类)
        ├── SkAudioPlayer_oboe.cpp     (Android Oboe 实现)
        ├── SkAudioPlayer_sfml.cpp     (SFML 跨平台实现)
        ├── SkAudioPlayer_mac.mm       (macOS 实现)
        └── SkAudioPlayer_none.cpp     (空实现)
```

该类不依赖 Skia 的图形渲染功能，仅依赖核心数据结构 `SkData`，可独立用于音频播放场景。

## 主要类与结构体

### SkAudioPlayer 类

抽象基类，定义音频播放器的公共接口。

**成员变量：**
```cpp
State   fState;      // 播放状态：播放/停止/暂停
float   fRate;       // 播放速率（0.0 - 1.0），默认 1.0
float   fVolume;     // 音量（0.0 - 1.0），默认 1.0
```

**嵌套枚举：**
```cpp
enum class State {
    kPlaying,    // 正在播放
    kStopped,    // 已停止
    kPaused,     // 已暂停
};
```

## 公共 API 函数

### 工厂方法
```cpp
static std::unique_ptr<SkAudioPlayer> Make(sk_sp<SkData>);
```
从音频数据创建播放器实例。如果格式不支持或加载失败，返回 `nullptr`。

### 时间控制
```cpp
double duration() const;              // 获取音频总时长（秒）
double time() const;                  // 获取当前播放位置（0 ~ duration）
double setTime(double);               // 设置播放位置，返回实际设置的时间
double normalizedTime() const;        // 获取归一化时间（0.0 ~ 1.0）
double setNormalizedTime(double);     // 设置归一化时间
```

`setTime` 实现了边界保护和有效性检查：
- 将时间钳制在 `[0, duration()]` 范围内
- 拒绝非有限值（NaN、Infinity）
- 仅在时间发生变化时调用虚函数 `onSetTime`

### 状态控制
```cpp
State state() const;                  // 获取当前状态
State setState(State);                // 设置状态，返回实际状态
void play();                          // 开始播放
void pause();                         // 暂停播放
void stop();                          // 停止播放
bool isPlaying/isPaused/isStopped();  // 状态查询
```

### 播放参数控制
```cpp
float volume() const;                 // 获取音量（0.0 ~ 1.0）
float setVolume(float);               // 设置音量，返回实际音量
float rate() const;                   // 获取播放速率
float setRate(float);                 // 设置播放速率，返回实际速率
```

所有 setter 方法都实现了相同的保护机制：
- 参数钳制到 `[0.0, 1.0]` 范围
- 拒绝非有限值
- 仅在值变化时调用对应的虚函数

## 内部实现细节

### 模板方法模式

`SkAudioPlayer` 使用模板方法模式，所有公共 API 都通过调用纯虚函数实现：

```cpp
// 公共方法调用虚函数
double duration() const { return this->onGetDuration(); }
State setState(State s) {
    if (s != fState) {
        fState = this->onSetState(s);
    }
    return fState;
}
```

**子类需要实现的纯虚函数：**
```cpp
virtual double onGetDuration() const = 0;
virtual double onGetTime() const = 0;
virtual double onSetTime(double) = 0;
virtual State onSetState(State) = 0;
virtual float onSetRate(float) = 0;
virtual float onSetVolume(float) = 0;
```

### 参数验证逻辑

所有 setter 方法都包含统一的参数验证流程：

```cpp
float SkAudioPlayer::setVolume(float v) {
    v = std::min(std::max(v, 0.f), 1.f);    // 钳制到有效范围
    if (!std::isfinite(v)) {                // 拒绝 NaN/Infinity
        v = fVolume;
    }
    if (v != fVolume) {                     // 仅在值变化时调用虚函数
        fVolume = this->onSetVolume(v);
    }
    return fVolume;
}
```

这种设计确保：
1. 即使子类实现有误，也不会因异常输入导致崩溃
2. 避免不必要的虚函数调用开销
3. 保证返回值始终在有效范围内

### 时间归一化

提供便捷的归一化时间接口，将时间映射到 `[0.0, 1.0]` 范围：

```cpp
double normalizedTime() const {
    return this->time() / this->duration();
}

double setNormalizedTime(double t) {
    this->setTime(t * this->duration());
    return this->normalizedTime();
}
```

这在构建 UI 进度条等场景中非常实用。

## 依赖关系

**外部依赖：**
- `include/core/SkData.h` - Skia 的不可变数据容器，用于传递音频数据
- `<memory>` - 使用 `std::unique_ptr` 管理对象生命周期
- `<algorithm>` - 使用 `std::min/max` 进行参数钳制
- `<cmath>` - 使用 `std::isfinite` 检查浮点数有效性

**被依赖：**
- 具体平台实现类（`SkAudioPlayer_oboe`, `SkAudioPlayer_sfml` 等）继承该基类
- Skottie 等动画模块可能使用该类播放背景音乐
- 示例程序和工具使用该类提供音频播放功能

## 设计模式与设计决策

### 1. 工厂方法模式
静态 `Make` 方法隐藏了具体子类的创建逻辑，调用者无需关心平台差异：
```cpp
auto player = SkAudioPlayer::Make(audioData);
if (player) {
    player->play();
}
```

### 2. 模板方法模式
基类定义算法骨架（参数验证、状态管理），子类实现具体步骤（平台音频 API 调用），实现代码复用和一致性保证。

### 3. 构造函数保护
禁止直接构造 `SkAudioPlayer` 对象，仅允许子类调用，强制使用工厂方法：
```cpp
protected:
    SkAudioPlayer() {}
```

### 4. 虚析构函数
提供虚析构函数确保通过基类指针删除对象时正确调用子类析构函数：
```cpp
virtual ~SkAudioPlayer();
```

### 5. 数值安全设计
所有浮点数输入都经过严格验证，防止 NaN/Infinity 引发未定义行为，这在音频处理中尤为重要，因为音频缓冲区出现无效值可能导致硬件损坏或用户听力损伤。

## 性能考量

### 1. 避免不必要的虚函数调用
所有 setter 方法在调用虚函数前先检查值是否变化：
```cpp
if (v != fVolume) {
    fVolume = this->onSetVolume(v);
}
```

### 2. 内联简单查询
简单的 getter 方法定义在类内，编译器可以内联优化：
```cpp
double duration() const { return this->onGetDuration(); }
float volume() const { return fVolume; }
```

### 3. 最小化内存占用
基类仅包含 3 个成员变量（共 12 字节，加上 vtable 指针为 16-20 字节），保持轻量级设计。

### 4. 状态缓存
将状态、速率、音量等信息缓存在基类中，避免频繁调用子类的虚函数获取这些信息。

### 5. 归一化时间计算
归一化时间通过简单的除法实现，无需额外存储，节省内存并保证数据一致性。

## 相关文件

**核心实现：**
- `modules/audioplayer/SkAudioPlayer.h` - 抽象基类头文件
- `modules/audioplayer/SkAudioPlayer.cpp` - 公共逻辑实现

**平台实现：**
- `modules/audioplayer/SkAudioPlayer_oboe.cpp` - Android Oboe 后端
- `modules/audioplayer/SkAudioPlayer_sfml.cpp` - SFML 跨平台后端
- `modules/audioplayer/SkAudioPlayer_mac.mm` - macOS AudioToolbox 后端
- `modules/audioplayer/SkAudioPlayer_none.cpp` - 空实现（不支持音频的平台）

**使用示例：**
- `modules/skottie/` - Skottie 动画模块可能使用该类播放音频
- `tools/viewer/` - Viewer 工具可能使用该类播放演示音频

**相关模块：**
- `include/core/SkData.h` - 音频数据容器
