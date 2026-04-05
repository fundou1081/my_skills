# MiniMax Office Skills

> 生产级 AI 办公文档引擎，MIT 开源协议
> https://github.com/MiniMax-AI/skills

## 简介

解决 AI 生成办公文档"能打开但无法交付"的痛点，直接操作底层 XML，而非依赖高层封装库，确保公式、透视表、宏等高级内容不丢失。

## 四个组件

| 组件 | 说明 | 典型场景 |
|------|------|---------|
| **MiniMax-docx** | Word 文档引擎，保留嵌套表格、多级目录、修订追踪 | 法律合同、多语言排版 |
| **MiniMax-xlsx** | Excel 引擎，保留数据透视表、动态公式、VBA 宏 | 金融报表、数据分析 |
| **MiniMax-pdf** | PDF 生成，15 种专业封面模式 | 企业报告、合规文档 |
| **PPTX-generator** | PPT 演示文稿生成与排版控制 | 自动化演示生成 |

## 安装

**不克隆项目**，直接按需安装各组件：

```bash
# docx
pip install minimax-docx

# xlsx
pip install minimax-xlsx

# pdf
pip install minimax-pdf

# pptx
pip install pptx-generator
```

> 具体安装命令以 GitHub 仓库最新 README 为准。

## 使用示例

### 生成 Word 文档

```python
from minimax_docx import Document

doc = Document()
doc.add_heading("报告标题", level=1)
doc.add_paragraph("正文内容...")
doc.save("report.docx")
```

### 生成 Excel（含公式）

```python
from minimax_xlsx import Workbook

wb = Workbook()
ws = wb.add_sheet("数据")
ws.write("A1", "数值")
ws.write("B1", "结果")
ws.write_formula("B2", "=SUM(A2:A10)")
wb.save("data.xlsx")
```

### 生成 PDF

```python
from minimax_pdf import PDF

pdf = PDF()
pdf.add_cover(title="年度报告", style=1)
pdf.add_page("内容页...")
pdf.render("report.pdf")
```

### 生成 PPT

```python
from pptx_generator import Presentation

prs = Presentation()
prs.add_slide(title="封面", content="标题内容")
prs.add_slide(title="第二页", content="要点列表")
prs.save("report.pptx")
```

## 技术要点

- **Word/Excel/PPT**：基于 .NET OpenXML SDK / PptxGenJS + XML 直操作
- **PDF**：基于 ReportLab + Playwright 渲染
- **多语言**：内置中日韩排版指南

## 注意事项

- 确认 Python 版本要求（建议 3.9+）
- 部分组件可能需要 .NET 运行时
- 详细 API 文档见 GitHub 仓库
