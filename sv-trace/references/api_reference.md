# API Reference — sv-trace 1.0.0

完整 API 签名 + 所有 dataclass 字段。本文档供 agent 详细查表用 — 大部分调用场景 SKILL.md 主体已覆盖。

## Public API (从 `signal_tracer` 直接 import)

```python
from signal_tracer import (
    # 函数式 (单文件)
    trace_signal,
    trace_signal_from_file,

    # 类式 (多文件)
    SignalTracer,
    SignalTracerFromFile,

    # 数据模型
    TraceResult, TraceType, ScopeKind,
    DriverTrace, LoadTrace,
    ScopeInfo, SignalInfo,
    TraceSummary, ContextBundle,

    # Evidence (M5.1)
    SyntaxNodeSnapshot,
    CodeEvidence, build_evidence,

    # 内部 (advanced, M5.1 fix)
    _set_source_manager,

    # 版本
    __version__,
)
```

## `trace_signal(signal_name, sv_code, file_path='') -> TraceResult`

单文件一次性 trace。

| 参数 | 类型 | 说明 |
|------|------|------|
| `signal_name` | str | 目标信号名 |
| `sv_code` | str | 完整 SV 源码 |
| `file_path` | str | 文件名 (用于 evidence 报错时显示, 不读盘) |

**返回**: `TraceResult` (有 `.drivers` 和 `.loads` 属性)

## `SignalTracer` 类

```python
class SignalTracer:
    def __init__(self):
        # self._files: Dict[file_path, sv_code]  # M5.1h: in-memory 存, evidence 读回用
        # self._comp: pyslang.Compilation
        # self._tree: SyntaxTree (v10 root, v11 syntax.SyntaxTree)
        # self._drivers: Dict[signal_name, List[DriverTrace]]
        # self._loads:   Dict[signal_name, List[LoadTrace]]
        # self._ports:   PortResolver (M4.1)
        ...

    def add_file(self, file_path: str, sv_code: str) -> None: ...
    def add_files(self, files: Dict[str, str]) -> None: ...
    def build(self) -> None: ...  # 必须先 build 才能 trace

    # === 4-步匹配 trace ===
    def trace(self, signal: str, verify: bool = True) -> TraceResult: ...
    def trace_drivers(self, signal: str, verify: bool = True) -> List[DriverTrace]: ...
    def trace_loads(self, signal: str, verify: bool = True) -> List[LoadTrace]: ...
    def trace_verified(self, signal: str) -> TraceResult: ...

    # === 链追踪 ===
    def get_driver_chain(self, signal: str, max_depth: int = 10, verify: bool = True) -> List[str]: ...
    def get_load_chain(self, signal: str, max_depth: int = 10, verify: bool = True) -> List[str]: ...

    # === 链 dump (M5.1f) ===
    def dump_driver_chain(self, signal: str, max_depth: int = 10, *, summary_only: bool = False) -> Union[dict, dict-summary]: ...
    def dump_load_chain(self, signal: str, max_depth: int = 10, *, summary_only: bool = False) -> Union[dict, dict-summary]: ...

    # === 多驱动 (M1.5 + M5.1b + M5.1g) ===
    def find_multi_drivers(self, verify: bool = True) -> Dict[str, List[DriverTrace]]: ...
    def dump_multi_drivers(self, summary_only: bool = False) -> Union[dict, dict-summary]: ...

    # === 计数 ===
    def get_driver_count(self, signal: str) -> int: ...
    def get_load_count(self, signal: str) -> int: ...
```

## `TraceResult` 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `signal_name` | str | 查询的目标信号名 |
| `drivers` | List[DriverTrace] | 所有 driver 列表 |
| `loads` | List[LoadTrace] | 所有 load 列表 |
| `trace_type` | TraceType | 枚举: DRIVER, LOAD, BOTH |
| `source_file` | str | 查询时给的源文件名 |
| `matched_path` | str | 实际匹配的层次路径 (4 步匹配中哪一步) |
| `to_contexts(self, file_content=None)` | method | 转 ContextBundle 列表 |
| `to_context(self, ...)` | method | 单个 trace → ContextBundle |
| `get_driver_chain(self, max_depth=10)` | method | 链 (嵌套) |

## `DriverTrace` / `LoadTrace` 字段

`LoadTrace` 字段同 `DriverTrace` 但语义是"读取"。

| 字段 | 类型 | 说明 |
|------|------|------|
| `signal_name` | str | 目标信号名 |
| `source_expr` | str | 完整驱动/读取表达式 |
| `source_signals` | List[str] | 表达式中读到的信号 |
| `file` | str | 完整路径 |
| `line` | int | 行号 |
| `column` | int | 列号 (可选) |
| `scope_text` | str | 完整 always_ff/always_comb/assign 块 |
| `scope_kind` | ScopeKind | ALWAYS_FF / ALWAYS_COMB / CONTINUOUS_ASSIGN / INITIAL |
| `clock` | Optional[str] | 提取的时钟 (e.g. "clk") |
| `reset` | Optional[str] | 提取的复位 (e.g. "rst_n") |
| `condition_stack` | List[str] | 嵌套条件 (e.g. `['!rst_n', 'data_in[7]']`) |
| `hierarchical_path` | str | 模块实例路径 (e.g. "top.u_mid") |
| `is_continuous` | bool | 是否 assign (vs always) |
| `to_context(self, ...)` | method | 转 ContextBundle (M5.1) |
| `_evidence_override` | CodeEvidence | 内部 (M5.1h 填充, 让 to_context 跳过 disk I/O) |

## `ScopeKind` 枚举

```python
class ScopeKind(enum.Enum):
    ALWAYS_FF         # 时序 (e.g. always_ff @(posedge clk))
    ALWAYS_COMB       # 组合 (e.g. always_comb)
    ALWAYS            # 普通 always (按 clock/reset 自动归类)
    CONTINUOUS_ASSIGN # wire assign
    INITIAL           # initial 块 (一般不用)
    FUNCTION          # function 内部赋值
    TASK              # task 内部赋值
```

## `ContextBundle` 字段 (M2)

```python
@dataclass(frozen=True)
class ContextBundle:
    signal_name: str
    source_expr: str
    source_signals: Tuple[str, ...]
    file: str
    line: int
    scope_text: str
    scope_kind: ScopeKind
    clock: Optional[str]
    reset: Optional[str]
    condition_stack: Tuple[str, ...]
    hierarchical_path: str
    code_evidence: Optional[CodeEvidence]  # M5.1 填充时才有
    credibility_score: float               # 0-1
    is_verified: bool                      # True iff credibility >= 0.8

    def summary(self) -> str: ...          # 一行可读
    def to_dict(self) -> dict: ...         # 完整 JSON-serializable
    def to_evidence_string(self) -> str: ...  # M5.1 LLM-friendly
```

## `CodeEvidence` (M5.1)

```python
@dataclass(frozen=True)
class CodeEvidence:
    file: str
    line: int
    source_expr: str
    signal_name: str
    file_content: Optional[str]  # 传 file_content 才能 verify
    file_readable: bool
    snippet: Optional[str]              # 取 line 上下 2 行
    matches_source_expr: bool           # 文本里真找到 source_expr
    matches_signal_name: bool           # 文本里真找到 signal_name
    credibility_score: float            # 0-1

    def to_evidence_string(self) -> str: ...  # 多行 LLM 友好
    def to_dict(self) -> dict: ...
```

**credibility_score 算法**:
- `file_readable` (+0.2)
- `snippet_present` (+0.2)  ← line 存在
- `matches_source_expr` (+0.4)
- `matches_signal_name` (+0.2)
- **VERIFIED** iff `>= 0.8`

详见 [evidence_guide.md](evidence_guide.md)。

## `build_evidence(file, line, source_expr, signal_name, file_content=None) -> CodeEvidence`

手动构造 evidence (单文件场景)。

## `TraceSummary` (M5.1f chain dump 顶层)

```python
@dataclass(frozen=True)
class TraceSummary:
    total_hops: int
    avg_credibility: float
    min_credibility: float
    max_credibility: float
    cross_files: bool       # 链上跨多个文件
    has_cycle: bool         # 链上检测到环
```

## `_set_source_manager(sm)` (M5.1h fix, advanced)

内部函数: 把 pyslang 的 SourceManager 同步给 `build_evidence_via_syntax`, 防止 evidence 走 syntax 路径时拿不到 file content。

**正常用户不用调**。只在 evidence 显示 "snippet: (syntax path)" 但你想要 line-based snippet 时调。

## 错误码 / 异常

| 异常 | 触发 | 解决 |
|------|------|------|
| `ImportError: cannot import name 'SyntaxTree' from 'pyslang'` | pyslang 11+ 安装但项目未升级 | 升级 sv-trace >= 1.0.0 (有 try/fallback) |
| `ValueError: must call build() before trace()` | 忘了 build | 在 trace 前 `t.build()` |
| 安静 return empty | signal 名拼错 / 在不相关 module | 用后缀匹配 `t.trace('count')` 看返回 |
