# Evidence Guide (M5.1) — credibility_score 算法 + 何时信 / 不信

## 背景

**问题**: 在 v1.0 之前, `trace_signal` 只返回元数据 (`source_expr`, `line`)。LLM/人拿到这些字段后只能"信不信由你"。

**M5.1 fix**: 每个 trace 都带一段 `CodeEvidence`, 把 `line` 真的去文件里读出来, 然后验证:
- `source_expr` 真在该 line 周围?
- `signal_name` 真在该 line 周围?
- 验证得分 `credibility_score` (0-1) 和 `is_verified` (>= 0.8) 标记。

LLM/人 拿到 evidence 后, **可决定要不要信这个 trace**。

## 算法

```
credibility_score = 0.0
if file_readable:           +0.2
if snippet_present:         +0.2
if matches_source_expr:     +0.4
if matches_signal_name:     +0.2
total = sum
is_verified = (total >= 0.8)
```

| 字段 | 阈值 | 含义 |
|------|------|------|
| `file_readable` | 任意 | 文件存在 + 权限读 |
| `snippet_present` | line 1..N | line 号在文件范围内 |
| `matches_source_expr` | 字面量子串 | 文本里**真找到** `source_expr` (line ±2) |
| `matches_signal_name` | 字面量子串 | 文本里**真找到** `signal_name` (line ±2) |

注意 `source_expr` 匹配是**字面量子串**, 不是 AST 匹配。

## 三种 evidence 路径

sv-trace 内部有 3 种拿 snippet 的方式 (按优先级):

1. **file-based** (最准): 读磁盘文件, 精确取 `line` 上下 2 行
   - 条件: `file` 路径存在, `file_content` 也提供 (or in-memory `_files`)
2. **syntax-based** (M5.1h, 跨文件准): 从 pyslang SyntaxTree 冻结的 `SyntaxNodeSnapshot` 拿
   - 条件: file 不可读, 但 syntax tree 已 build
3. **line-only** (回退): 只给 `line` 不给 snippet
   - 条件: 上面两种都失败

`SyntaxNodeSnapshot` 关键: pyslang SyntaxTree 内部有 buffer, 复用会乱。snapshot 冻结文本防 bug。

## 何时信 / 不信

### ✅ 可信 (>= 0.8, is_verified=True)

```python
result = trace_signal('count', sv, 'counter.sv')
for ctx in result.to_contexts(file_content=sv):
    d = ctx.to_dict()
    if d['is_verified']:
        # 文件存在 + line 对 + source_expr 在 + signal_name 在
        # 放心用
        print(f"  ✓ {d['source_expr']} @ {d['file']}:{d['line']}")
```

### ⚠ 部分可信 (0.5-0.8)

通常是 `file_readable` 或 `matches_source_expr` 缺:
- `file_readable=False` → 文件被删了/路径错, 但 trace 仍能用 (用了 syntax fallback)
- `matches_source_expr=False` → pyslang 文本格式与源码略不同 (见下)

**决策**: 看具体 evidence_string 决定。

### ❌ 不可信 (< 0.5)

多个字段 fail。**不要用这个 trace 当事实**, 给 LLM 也注明 "evidence 弱"。

## 已知 false-negative 案例

`matches_source_expr` 是字面量匹配。pyslang 解析后表达式会**标准化**, 与源码略不同:

| 源码 | pyslang 文本 | 命中? |
|------|-------------|------|
| `count + data_in` | `count Add data_in` | ❌ (空格, + vs Add) |
| `count[3:0]` | `count[3:0]` | ✅ |
| `{a, b}` | `{ a, b }` | ❌ (空格) |
| `a inside {X, Y}` | `a inside { X, Y }` | ❌ |

**应对**: 不要全信 `matches_source_expr=False` = 真的不对。**看 `matches_signal_name=True` + line 对** 就基本能信。

未来: M5.2 想做 normalized 匹配 (用 pyslang token 而不是 raw text)。

## 多文件项目: in-memory evidence

`SignalTracer` 自动 in-memory 存所有 `add_file()` 的代码 (在 `self._files`)。

**好处**:
- `trace_verified()` 不读盘 (快, 跨环境)
- 避免用户漏传 `file_content`
- 内部 evidence 默认走 in-memory

```python
t = SignalTracer()
t.add_file('top.sv', top_code)   # 存进 self._files
t.add_file('sub.sv', sub_code)
t.build()
result = t.trace_verified('top.u_sub.signal')  # 自动用 self._files
# → 每个 driver 都有 evidence, 不需要 file_content 参数
```

## 用 evidence 喂 LLM 的最佳实践

```python
# 1. 跑 trace (默认 verify=True)
result = trace_signal('count', sv, 'counter.sv')

# 2. 过滤 verified 的
verified = [ctx for ctx in result.to_contexts(file_content=sv) if ctx.is_verified]

# 3. 给 LLM 喂 verified + 一段说明
prompt = f"""
信号 `count` 的 drivers:
{chr(10).join(f"- {ctx.summary()}" for ctx in verified)}

注: 所有 trace 都经过 credibility 验证, is_verified=True。
"""
```

**不要**把所有 drivers 都喂 — LLM 会被 0.5 分的假 trace 误导。
