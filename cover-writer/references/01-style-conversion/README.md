# 01. 曲风转换 (Style Conversion)

> **子功能**: 把原曲改成新曲风, 歌词基本不变, 核心是改 description。

## 触发条件
- 用户说"改编成 ___ 风格"
- 用户说"把 X 改成 Y 风格"
- 用户给出目标曲风 (电子/交响/民调...)

## 8 大目标风格 (子分类)

详见: [style-mapping.md](style-mapping.md)

| 类型 | 子风格 |
|---|---|
| **电子** | EDM, Synthwave, Lo-fi, Dubstep, House, Techno, Trance |
| **古典** | 交响, 弦乐四重奏, 钢琴独奏, 室内乐, 巴洛克 |
| **民乐** | 民调, 古筝, 二胡, 笛箫, 琵琶, 民族合唱 |
| **西方** | 爵士, 雷鬼, 拉丁, Bossa Nova, 蓝草, 凯尔特 |
| **摇滚** | 摇滚, 朋克, 重金属, 后摇, 垃圾摇滚 |
| **流行变体** | 抒情 Ballad, R&B, 灵魂 Soul, 放克, 迪斯科 |
| **东方** | 中国风, 和风, 印度风, 阿拉伯风, 突厥风 |
| **现代** | 民谣 Acoustic, 城市民谣, Indie, Dream Pop, Shoegaze |

## 工作流

详见: [workflow.md](workflow.md)

## 输出

- 改编版 description (新曲风描述)
- 微调后的歌词 (适配新曲风)
- minimax-music 输入格式

## 跟其他子功能关系

- 02-structure-variation: 可叠加 (例如: 改编 + 加快)
- 03-minimax-adapter: 消费本子功能输出
