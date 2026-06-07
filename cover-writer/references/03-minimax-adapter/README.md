# 03. minimax 适配 (minimax-music Adapter)

> **子功能**: 把改编曲输出转成 minimax-music 可消费的格式。

## 触发条件
- 改编完成后, 准备喂给 minimax-music

## 输出格式

minimax-music 接受:
1. **lyrics**: 字符串, 包含 [verse] [chorus] [bridge] 等段落标记
2. **description** (prompt): 字符串, 描述音乐风格
3. **model**: 默认 `music-2.6`

## 歌词格式

段落标记:
- `[verse]` - 主歌
- `[chorus]` - 副歌/高潮
- `[bridge]` - 桥段
- `[intro]` - 前奏
- `[outro]` - 尾奏

**示例**:
```
[verse]
要踏过末班地铁 身披霓虹碎影堆
再各自困顿在加班的惊雷
...

[chorus]
这城有多深 没人懂
末班的归人 没有姓名
...
```

详见: [format-spec.md](format-spec.md)

## 调用方式

通过 minimax-music skill:
```python
from music import generate_music
generate_music(
    lyrics=lyrics_str,
    description=description_str,
    output_path="/tmp/cover_v1.mp3",
    model="music-2.6"
)
```

或命令行:
```bash
python3 minimax-music-generate/scripts/music.py "$lyrics" -d "$description" -o output.mp3
```

## 跟其他子功能关系

- 消费 01 (曲风转换) 输出的 description
- 消费 02 (结构变奏) 输出的新歌词结构
- 调用 minimax-music 生成 MP3
