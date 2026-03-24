
---
title: "下载隔离文件 (Isolates)"
linkTitle: "下载隔离文件 (Isolates)"

---


运行测试产生的中间和最终构建产物都存储在
[Isolate](https://github.com/luci/luci-py/blob/main/appengine/isolate/doc/Design.md) 中，
可以下载到桌面进行检查和调试。

首先安装客户端：

     git clone https://github.com/luci/client-py.git

将检出位置添加到你的 $PATH 中。

要下载测试的隔离文件，首先访问构建状态页面并找到 "isolated output" 链接：

<img src="../Status.png" style="margin-left:30px" width=576 height=271 >


点击该链接找到隔离输出的哈希值：


<img src="../Isolate.png" style="margin-left:30px" width=451 height=301 >

然后运行 `isolateserver.py`，将 --isolated 设置为该哈希值：

    $ isolateserver.py \
      download \
      --isolate-server=https://isolateserver.appspot.com \
      --isolated=5b85b7c382ee2a34530e33c7db20a07515ff9481 \
      --target=./download/

