#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Commercial Video Producer - Skill Synchronization & Auto-Persistence Tool
=============================================================================
This tool enables zero-friction, one-command synchronization of newly discovered
video production techniques, bug fixes, material parameters, and pipeline upgrades
to both the local Antigravity Agent Skill and the GitHub remote repository.

Usage:
    python sync_skill.py -m "feat: add support for brushed anodized aluminum"
    python sync_skill.py -m "fix: resolve edge reflection artifact in shot 2" --evolution "问题描述 | 解决根因与技术突破"
"""

import sys
import os
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Configure Windows console to UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Define standard workspace directories
WORKSPACE_DIR = Path(r"d:\视频")
SKILL_REPO_DIR = WORKSPACE_DIR / "ai-commercial-video-producer"
DEPLOYED_SCRIPTS_DIR = WORKSPACE_DIR / "部署的脚本"
AGENT_SKILL_DIR = WORKSPACE_DIR / ".agents" / "skills" / "ai-video-producer"
EVOLUTION_DOC = SKILL_REPO_DIR / "references" / "OPTIMIZATION_EVOLUTION.md"


def ensure_sync_between_dirs():
    """Ensure core production scripts and docs are mirrored between deployed scripts and skill packages."""
    print("🔄 [1/4] 检查并同步生产脚本与文档镜像...")
    
    # 1. Sync generate_commercial_video.py
    src_engine = DEPLOYED_SCRIPTS_DIR / "generate_commercial_video.py"
    target_engine_repo = SKILL_REPO_DIR / "scripts" / "generate_commercial_video.py"
    target_engine_agent = AGENT_SKILL_DIR / "scripts" / "generate_commercial_video.py"
    
    if src_engine.exists():
        # Compare mtime/size
        target_engine_repo.parent.mkdir(parents=True, exist_ok=True)
        target_engine_agent.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_engine, target_engine_repo)
        shutil.copy2(src_engine, target_engine_agent)
        print("  ✓ 核心生产引擎 generate_commercial_video.py 镜像已对齐")
        
    # 2. Sync SKILL.md and references between repo and local agent skill
    if (SKILL_REPO_DIR / "SKILL.md").exists():
        shutil.copy2(SKILL_REPO_DIR / "SKILL.md", AGENT_SKILL_DIR / "SKILL.md")
        
    for sub in ["references", "examples"]:
        src_sub = SKILL_REPO_DIR / sub
        dst_sub = AGENT_SKILL_DIR / sub
        if src_sub.exists():
            dst_sub.mkdir(parents=True, exist_ok=True)
            for f in src_sub.glob("*.md"):
                shutil.copy2(f, dst_sub / f.name)
    print("  ✓ 本地智能体技能库 .agents/skills/ai-video-producer 同步完毕")


def append_evolution_record(evolution_text: str):
    """Append a structured evolution record into OPTIMIZATION_EVOLUTION.md if provided."""
    if not evolution_text or not EVOLUTION_DOC.exists():
        return
        
    print("📝 [2/4] 追加实战调优演进记录...")
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    entry = f"\n\n---\n\n## 📅 实战增量演进 ({date_str})\n\n{evolution_text.strip()}\n"
    
    with open(EVOLUTION_DOC, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"  ✓ 演进实录已更新至 {EVOLUTION_DOC.name}")


def git_commit_and_push(commit_msg: str):
    """Perform git add, commit, and push to GitHub remote."""
    print("🚀 [3/4] 提交并推送至 GitHub 开源仓库 (cnproduct/ai-commercial-video-producer)...")
    
    # Check git status
    st_res = subprocess.run(["git", "status", "--porcelain"], cwd=str(SKILL_REPO_DIR), capture_output=True, text=True)
    if not st_res.stdout.strip():
        print("  ℹ️ 技能包无新增修改内容，无需提交。")
        return True
        
    # Git add
    subprocess.run(["git", "add", "."], cwd=str(SKILL_REPO_DIR), check=True)
    
    # Git commit
    full_commit_msg = commit_msg if commit_msg else f"chore: automated skill evolution sync ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    c_res = subprocess.run(["git", "commit", "-m", full_commit_msg], cwd=str(SKILL_REPO_DIR), capture_output=True, text=True)
    print(f"  ✓ 提交成功: {full_commit_msg}")
    
    # Git push
    p_res = subprocess.run(["git", "push", "origin", "main"], cwd=str(SKILL_REPO_DIR), capture_output=True, text=True)
    if p_res.returncode == 0:
        print("  ✓ 成功推送到 GitHub 远程仓库 (origin/main)！")
        return True
    else:
        print(f"  ⚠️ 推送遇到警告: {p_res.stderr.strip()}")
        # Check if push failed due to credentials or network
        if "Authentication failed" in p_res.stderr or "Permission" in p_res.stderr:
            print("  [!] 提示: 请检查本地 Git 凭据管理器或网络连通性。")
            return False
        return False


def main():
    parser = argparse.ArgumentParser(description="AI Commercial Video Producer - Skill Synchronization & Auto-Persistence")
    parser.add_argument("-m", "--message", type=str, required=True, help="提交说明 (如: fix: 解决边缘反光噪点 / feat: 新增陶瓷釉面光影)")
    parser.add_argument("--evolution", type=str, default=None, help="追加到 OPTIMIZATION_EVOLUTION.md 的技术攻坚摘要")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("⚡ AI 商业视频生产工坊 · 技能沉淀与 GitHub 自动化同步启动")
    print(f"   提交说明: {args.message}")
    print("=" * 70)
    
    try:
        ensure_sync_between_dirs()
        if args.evolution:
            append_evolution_record(args.evolution)
            # Re-mirror after modifying evolution doc
            ensure_sync_between_dirs()
            
        success = git_commit_and_push(args.message)
        print("=" * 70)
        if success:
            print("🎉 [4/4] 技能包与 GitHub 仓库全链路沉淀同步圆满完成！")
            print("   👉 仓库地址: https://github.com/cnproduct/ai-commercial-video-producer")
        else:
            print("⚠️ 局部同步完成，推送请检查网络环境。")
        print("=" * 70)
    except Exception as e:
        print(f"❌ 自动化同步出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
