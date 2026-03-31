#!/usr/bin/env python3
"""
Report Version Manager - 报告版本管理工具
支持版本追踪、变更记录、评审流程
"""

import json
import argparse
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class ReportVersionManager:
    def __init__(self, report_dir: str = "."):
        self.report_dir = Path(report_dir)
        self.metadata_file = self.report_dir / ".report_metadata.json"
        self.metadata = self._load_or_init_metadata()
    
    def _load_or_init_metadata(self) -> Dict:
        """加载或初始化元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "report_name": "未命名报告",
            "versions": [],
            "current_version": None,
            "contributors": [],
            "review_history": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_metadata(self):
        """保存元数据"""
        self.metadata["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def create_report(self, report_name: str, template: str = "standard") -> str:
        """创建新报告"""
        self.metadata["report_name"] = report_name
        self.metadata["current_version"] = "v0.1-draft"
        
        version_info = {
            "version": "v0.1-draft",
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "created_by": "system",
            "changelog": ["初始版本"],
            "sections": {
                "摘要": {"status": "todo", "content": ""},
                "背景": {"status": "todo", "content": ""},
                "分析": {"status": "todo", "content": ""},
                "结论": {"status": "todo", "content": ""},
                "附录": {"status": "todo", "content": ""}
            }
        }
        self.metadata["versions"].append(version_info)
        self._save_metadata()
        
        return f"✅ 报告 '{report_name}' 已创建，当前版本: v0.1-draft"
    
    def update_section(self, section: str, content: str, author: str = "user") -> str:
        """更新报告章节"""
        current = self.metadata["current_version"]
        for v in self.metadata["versions"]:
            if v["version"] == current:
                if section not in v["sections"]:
                    v["sections"][section] = {"status": "todo", "content": ""}
                v["sections"][section]["content"] = content
                v["sections"][section]["status"] = "in-progress"
                v["sections"][section]["updated_at"] = datetime.now().isoformat()
                v["sections"][section]["updated_by"] = author
                break
        
        self._save_metadata()
        return f"✅ 章节 '{section}' 已更新"
    
    def complete_section(self, section: str) -> str:
        """标记章节完成"""
        current = self.metadata["current_version"]
        for v in self.metadata["versions"]:
            if v["version"] == current:
                if section in v["sections"]:
                    v["sections"][section]["status"] = "completed"
                    v["sections"][section]["completed_at"] = datetime.now().isoformat()
                break
        self._save_metadata()
        return f"✅ 章节 '{section}' 已标记为完成"
    
    def create_version(self, new_version: str, changelog: List[str], author: str = "user") -> str:
        """创建新版本"""
        current = self.metadata["current_version"]
        
        # 找到当前版本的sections
        current_sections = {}
        for v in self.metadata["versions"]:
            if v["version"] == current:
                current_sections = v["sections"].copy()
                break
        
        version_info = {
            "version": new_version,
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "created_by": author,
            "changelog": changelog,
            "parent_version": current,
            "sections": current_sections
        }
        
        self.metadata["versions"].append(version_info)
        self.metadata["current_version"] = new_version
        
        if author not in self.metadata["contributors"]:
            self.metadata["contributors"].append(author)
        
        self._save_metadata()
        return f"✅ 新版本 '{new_version}' 已创建，基于 {current}"
    
    def change_status(self, version: str, status: str) -> str:
        """变更版本状态"""
        valid_statuses = ["draft", "in-review", "approved", "published", "archived"]
        if status not in valid_statuses:
            return f"❌ 无效状态，可选: {', '.join(valid_statuses)}"
        
        for v in self.metadata["versions"]:
            if v["version"] == version:
                old_status = v["status"]
                v["status"] = status
                v["status_changed_at"] = datetime.now().isoformat()
                self._save_metadata()
                return f"✅ 版本 '{version}' 状态: {old_status} → {status}"
        
        return f"❌ 版本 '{version}' 不存在"
    
    def add_reviewer(self, version: str, reviewer: str, comment: str = "") -> str:
        """添加评审意见"""
        review_entry = {
            "version": version,
            "reviewer": reviewer,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        self.metadata["review_history"].append(review_entry)
        self._save_metadata()
        return f"✅ 评审人 '{reviewer}' 已添加到 '{version}' 的评审队列"
    
    def approve_review(self, version: str, reviewer: str, approved: bool, comment: str = "") -> str:
        """评审意见"""
        for review in self.metadata["review_history"]:
            if review["version"] == version and review["reviewer"] == reviewer:
                review["status"] = "approved" if approved else "rejected"
                review["comment"] = comment
                review["reviewed_at"] = datetime.now().isoformat()
                break
        
        # 如果所有评审都通过，自动更新状态
        version_reviews = [r for r in self.metadata["review_history"] if r["version"] == version]
        if all(r["status"] == "approved" for r in version_reviews) and version_reviews:
            self.change_status(version, "approved")
        
        self._save_metadata()
        result = "通过" if approved else "不通过"
        return f"✅ 评审 '{reviewer}' 对 '{version}' 的意见: {result}"
    
    def get_status(self) -> str:
        """获取报告状态摘要"""
        lines = []
        lines.append(f"# 📊 报告状态摘要\n")
        lines.append(f"**报告名称**: {self.metadata['report_name']}\n")
        lines.append(f"**当前版本**: {self.metadata['current_version']}\n")
        lines.append(f"**创建时间**: {self.metadata['created_at'][:10]}\n")
        lines.append(f"**最后更新**: {self.metadata['last_updated'][:10]}\n\n")
        
        lines.append(f"## 👥 贡献者\n")
        for c in self.metadata["contributors"]:
            lines.append(f"- {c}")
        lines.append(f"\n")
        
        lines.append(f"## 📋 版本列表\n")
        lines.append(f"| 版本 | 状态 | 创建时间 | 创建者 |\n")
        lines.append(f"|------|------|----------|--------|\n")
        for v in self.metadata["versions"]:
            lines.append(f"| {v['version']} | {v['status']} | {v['created_at'][:10]} | {v['created_by']} |\n")
        lines.append(f"\n")
        
        # 当前版本的章节状态
        current = self.metadata["current_version"]
        lines.append(f"## 📝 当前版本章节状态 ({current})\n")
        lines.append(f"| 章节 | 状态 | 更新时间 |\n")
        lines.append(f"|------|------|----------|\n")
        for v in self.metadata["versions"]:
            if v["version"] == current:
                for sec, info in v["sections"].items():
                    status_icon = {"todo": "⬜", "in-progress": "🟨", "completed": "🟩"}.get(info["status"], "⬜")
                    updated = info.get("updated_at", "")[:10] if info.get("updated_at") else "-"
                    lines.append(f"| {status_icon} {sec} | {info['status']} | {updated} |\n")
                break
        
        # 待评审意见
        pending_reviews = [r for r in self.metadata["review_history"] if r["status"] == "pending"]
        if pending_reviews:
            lines.append(f"\n## ⏳ 待评审 ({len(pending_reviews)})\n")
            for r in pending_reviews:
                lines.append(f"- {r['version']}: 待 {r['reviewer']} 评审\n")
        
        return "".join(lines)
    
    def export_changelog(self) -> str:
        """导出版本变更日志"""
        lines = []
        lines.append(f"# 📜 {self.metadata['report_name']} - 变更日志\n\n")
        
        for v in reversed(self.metadata["versions"]):
            lines.append(f"## {v['version']} ({v['created_at'][:10]})\n")
            lines.append(f"**状态**: {v['status']}\n")
            lines.append(f"**创建者**: {v['created_by']}\n\n")
            lines.append(f"**变更内容**:\n")
            for change in v.get("changelog", []):
                lines.append(f"- {change}\n")
            lines.append(f"\n")
            
            # 显示父版本
            if v.get("parent_version"):
                lines.append(f"_基于 {v['parent_version']}_\n")
            lines.append(f"\n---\n\n")
        
        return "".join(lines)
    
    def generate_report_draft(self) -> str:
        """生成报告草稿框架"""
        current = self.metadata["current_version"]
        content = []
        
        for v in self.metadata["versions"]:
            if v["version"] == current:
                content.append(f"# {self.metadata['report_name']}\n\n")
                content.append(f"**版本**: {v['version']} | **状态**: {v['status']}\n\n")
                content.append(f"---\n\n")
                
                for sec, info in v["sections"].items():
                    status = info["status"]
                    placeholder = {
                        "todo": "【待撰写】",
                        "in-progress": "【撰写中...】",
                        "completed": ""
                    }.get(status, "")
                    
                    content.append(f"## {sec} {placeholder}\n\n")
                    if info.get("content"):
                        content.append(f"{info['content']}\n\n")
                    content.append(f"---\n\n")
                break
        
        return "".join(content)


def main():
    parser = argparse.ArgumentParser(description="报告版本管理工具")
    parser.add_argument("action", choices=["create", "update", "complete", "version", 
                                           "status", "changelog", "review", "export", "draft"],
                        help="操作类型")
    parser.add_argument("--dir", "-d", default=".", help="报告目录")
    parser.add_argument("--name", "-n", help="报告名称")
    parser.add_argument("--section", "-s", help="章节名称")
    parser.add_argument("--content", "-c", help="内容")
    parser.add_argument("--version", "-v", help="版本号")
    parser.add_argument("--changelog", help="变更日志（逗号分隔）", nargs="+")
    parser.add_argument("--author", default="user", help="作者")
    parser.add_argument("--status", choices=["draft", "in-review", "approved", "published", "archived"],
                        help="状态")
    parser.add_argument("--reviewer", help="评审人")
    parser.add_argument("--comment", help="评审意见")
    parser.add_argument("--approve", action="store_true", help="批准")
    parser.add_argument("--reject", action="store_true", help="否决")
    parser.add_argument("--output", "-o", help="输出文件")
    
    args = parser.parse_args()
    
    manager = ReportVersionManager(args.dir)
    
    result = ""
    if args.action == "create":
        if not args.name:
            print("❌ 需要指定报告名称 --name")
            return
        result = manager.create_report(args.name)
    
    elif args.action == "update":
        if not args.section:
            print("❌ 需要指定章节 --section")
            return
        result = manager.update_section(args.section, args.content or "", args.author)
    
    elif args.action == "complete":
        if not args.section:
            print("❌ 需要指定章节 --section")
            return
        result = manager.complete_section(args.section)
    
    elif args.action == "version":
        if not args.version:
            print("❌ 需要指定版本号 --version")
            return
        changelog = args.changelog or ["更新"]
        result = manager.create_version(args.version, changelog, args.author)
    
    elif args.action == "status":
        if args.status and args.version:
            result = manager.change_status(args.version, args.status)
        else:
            result = manager.get_status()
    
    elif args.action == "review":
        if args.reviewer:
            if args.approve or args.reject:
                result = manager.approve_review(args.version or manager.metadata["current_version"], 
                                              args.reviewer, not args.reject, args.comment or "")
            else:
                result = manager.add_reviewer(args.version or manager.metadata["current_version"],
                                              args.reviewer, args.comment or "")
        else:
            result = "❌ 需要指定评审人 --reviewer"
    
    elif args.action == "changelog":
        result = manager.export_changelog()
    
    elif args.action == "export":
        result = manager.export_changelog()
    
    elif args.action == "draft":
        result = manager.generate_report_draft()
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✅ 已保存到: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
