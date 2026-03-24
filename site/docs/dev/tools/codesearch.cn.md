
---
title: "代码搜索 (Code Search)"
linkTitle: "代码搜索 (Code Search)"

---


有多种方式可以搜索 Skia 代码库，各有优缺点。

[cs.skia.org](http://cs.skia.org) 重定向到
[Chromium 代码搜索](https://code.google.com/p/chromium/codesearch)，限定在 Chromium 代码树的 Skia 部分。你可以在斜杠后添加查询；例如 [cs.skia.org/foo](http://cs.skia.org/foo) 将在 Skia 代码树中搜索 "foo"。Chromium 代码搜索提供交叉引用。

对于 Google 员工，还可以使用内部代码搜索中的 [Skia 仓库](http://cs/#skia/)。除了主要的 [skia](http://cs/#skia/skia/) 仓库外，内部代码搜索还索引了 [buildbot](http://cs/#skia/buildbot/)、[common](http://cs/#skia/common/) 和 [skia_internal](https://cs/#skia/skia_internal/) 仓库。但交叉引用和代码分析不可用。

[skia](https://github.com/google/skia) 和 [skia-buildbot](https://github.com/google/skia-buildbot) 仓库的 GitHub 镜像适合调查历史记录和 blame，或探索发布分支和其他分支。但搜索功能相当有限，交叉引用不可用，而且在历史记录中原始提交者的用户名会被替换为该用户的 GitHub 用户名。

你还可以浏览 [googlesource.com 上的 Skia 仓库](https://skia.googlesource.com/)。所有提交首先出现在这里。

  代码搜索选项              |搜索    |交叉引用 |历史记录 |仓库                          |分支    |新鲜度
  --------------------|-------|-----|--------|------------------------------|---------|---------------
  [cs.skia.org][1]    |正则表达式 | 是 |是     |skia [buildbot][5]            |main     |上次 DEPS 滚动
  [内部搜索][2]       |正则表达式 | 否 |是     |skia buildbot common internal |main     |数小时
  [GitHub][3]         |基础    | 否  |是     |skia buildbot                 |全部      |一小时
  [googlesource][4]   |无     | 否  |是     |全部                           |全部      |不适用

[1]: http://cs.skia.org/             "Chromium code search"
[2]: http://cs/#skia/                "Internal Code Search"
[3]: https://github.com/google/skia  "GitHub mirror of skia"
[4]: https://skia.googlesource.com/  "Primary Skia repos on googlesource.com"
[5]: https://cs.chromium.org/chromium/skia/buildbot/

客户端代码搜索
------------------

有一个 [Google 内部工具](https://goto.google.com/skia-client-search)，可以更方便地搜索 Skia 客户端的仓库，例如 Chromium、Android 和 Mozilla。如果你使用它并有建议，请告知 kjlubick。
