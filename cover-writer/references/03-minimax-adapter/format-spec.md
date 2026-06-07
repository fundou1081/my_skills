# minimax-music 格式规范

## 1. lyrics 格式

### 段落标记
| 标记 | 含义 | minimax 行为 |
|---|---|---|
| `[verse]` | 主歌 | 旋律平稳, 叙事 |
| `[chorus]` | 副歌/高潮 | 旋律上扬, 情绪爆发 |
| `[bridge]` | 桥段 | 转折, 通常短 |
| `[intro]` | 前奏 | 引入, 纯器乐或人声哼唱 |
| `[outro]` | 尾奏 | 渐弱, 收束 |

### 规则
1. 段落标记独占一行
2. 段落之间用空行分隔 (可选, 但建议)
3. 每段歌词每行一句, 一句一行
4. 标点用中文标点 (, 。 ? !)
5. 句长不限, 但**单行不宜超过 30 字**

### 示例 (完整)
```
[intro]

[verse]
要踏过末班地铁 身披霓虹碎影堆
再各自困顿在加班的惊雷
认定你我都绝非写字楼里泛泛之辈
是无名的城市萍水

[chorus]
猜测这城有多深 没人懂
末班的归人 没有姓名
玻璃窗映着我的脸 谁也不认识
我把心事写成便签 贴在便利店门口

[bridge]
猜这窗有多冷 又一夜无眠

[chorus]
这城有多深 没人懂
末班的归人 没有姓名

[outro]
我把心事写成便签 贴在便利店门口
```

## 2. description 格式

### 模板
```
<曲风1> + <曲风2> (可选), <配器>, <节奏>, <人声>, <情感>, <时长>
```

### 示例
- "EDM, 强劲 drop, 合成器, 快节奏, 男声, 都市孤独感, 5 分钟"
- "古风 + 交响, 笛箫 + 弦乐, 慢板, 女声, 思念"
- "Lo-fi, 低保真钢琴, 慵懒人声, 适合学习"

### 必含元素
- **曲风** (电子/古典/民乐/...)
- **配器** (至少 1-2 件)
- **节奏** (BPM 或 慢板/快板)
- **人声** (男/女/合唱)

### 可选元素
- 情感 (孤独/思念/燃)
- 时长 (3-5 分钟)
- 特殊效果 (reverb / autotune)

## 3. model 选择

- `music-2.6` (默认, 最新)
- `music-2.5` (稳定)

## 4. 输出文件

- 格式: MP3
- 采样率: 44100 Hz
- 比特率: 256 kbps
- 大小: 通常 3-5 MB

## 5. 错误处理

| 错误 | 原因 | 解决 |
|---|---|---|
| `MINIMAX_API_KEY not found` | API key 未配置 | 检查 `~/.openclaw/agents/main/agent/auth-profiles.json` |
| `No audio data returned` | API 返回空 | 重试, 或换 model |
| `Connection timeout` | 网络问题 | 重试 |

## 6. 完整调用示例

```python
import sys
sys.path.insert(0, '/path/to/minimax-music-generate/scripts')
from music import generate_music

lyrics = """[intro]

[verse]
要踏过末班地铁 身披霓虹碎影堆
...

[chorus]
...
"""

description = "古风 + EDM, 笛箫 + 合成器, 快板, 男女合唱, 都市孤独, 5 分钟"

output = generate_music(
    lyrics=lyrics,
    description=description,
    output_path="/tmp/cover_v1.mp3",
    model="music-2.6"
)
print(f"✅ {output}")
```
