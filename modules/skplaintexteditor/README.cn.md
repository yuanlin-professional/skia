# 编辑器 (Editor) #

这是一个实验性的编辑器层，它抽象了 SkShaper 文本排版功能，以便于嵌入到应用程序中。编辑器层与操作系统无关。

    +--------------------------------+
    |Application                     |
    +-+----+-------------------------+
      |    |
      |    |
      |  +-v-------------------------+
      |  |Editor                     |
      |  +-+----+--------------------+
      |    |    |
      |    |    |
      |    |  +-v--------------------+
      |    |  |SkShaper              |
      |    |  +-+--------+-----------+
      |    |    |        |
      |    |    |        |
    +-v----v----v--+   +-v-----------+
    |Skia          |   |HarfBuzz, ICU|
    +--------------+   +-------------+

应用程序层必须与以下系统交互：

  * 窗口系统
  * 文件系统
  * 剪贴板
  * 键盘/鼠标输入

试用方法：

    tools/git-sync-deps
    bin/gn gen out/default
    ninja -C out/default editor

    out/default/editor resources/text/english.txt

    cat resources/text/*.txt > example.txt
    out/default/editor example.txt
