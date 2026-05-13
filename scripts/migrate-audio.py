#!/usr/bin/env python3
"""一次性迁移脚本: 把 Apple Music 媒体库里的歌曲 + 元数据 + 歌词 + 封面
   提取到 ~/music-site/ 的 public/ 目录, 并生成 content/albums 的 markdown."""

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from mutagen.mp4 import MP4

SRC_ROOT = Path.home() / "Music/Music/Media.localized/Music/Jiangjingyi"
SITE_ROOT = Path.home() / "music-site"
PUBLIC = SITE_ROOT / "public"
CONTENT = SITE_ROOT / "src/content/albums"


@dataclass
class AlbumDef:
    slug: str
    src_dir: str
    title: str
    subtitle: str = ""
    description: str = ""
    bg_color: str = "#0b0a08"
    accent_color: str = "#c9a35a"
    tracks: list = field(default_factory=list)


ALBUMS = [
    AlbumDef(
        slug="lumen-ad-revelationem",
        src_dir="Lumen ad Revelationem_A Candlemas Liturgical Drama — The Song of Simeon",
        title="Lumen ad Revelationem",
        subtitle="A Candlemas Liturgical Drama — The Song of Simeon",
        description=(
            "圣烛节礼仪剧。以路加福音 2:25-35 西默盎之歌为内核，\n"
            "以中世纪礼仪剧形制承载现代电子化的圣咏。"
        ),
        bg_color="#1a2a2a",
        accent_color="#c9a35a",
    ),
    AlbumDef(
        slug="la-colomba-grigia-ep",
        src_dir="La Colomba Grigia (The Grey Dove) - EP",
        title="La Colomba Grigia",
        subtitle="The Grey Dove — EP",
        description=(
            "灰鸽。一组四首歌的变奏，从格里高利圣咏到游吟诗人民谣。\n"
            "Four variations on a single lament, from Gregorian chant to troubadour ballad."
        ),
        bg_color="#1a1a2a",
        accent_color="#9aa6c9",
    ),
]


def slugify(text: str, maxlen: int = 40) -> str:
    # 剥前导曲目编号 "01 "
    text = re.sub(r"^\d+\s*", "", text)
    # 中文标点 + 西文特殊字符全清空
    text = re.sub(r"[—–_:：;；,，.。!！?？\"'()（）\[\]【】<>《》&|/\\*?]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    text = text.strip("-").lower()
    return text[:maxlen].strip("-")


def convert_wav(src: Path, dst: Path) -> None:
    print(f"  afconvert WAV→M4A: {src.name}")
    subprocess.run(
        [
            "afconvert",
            "-f", "m4af",
            "-d", "aac",
            "-b", "192000",
            "-q", "127",
            "--soundcheck-generate",
            str(src),
            str(dst),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def copy_m4a(src: Path, dst: Path) -> None:
    print(f"  copy M4A: {src.name}")
    shutil.copy2(src, dst)


def extract_cover(mp4: MP4, dest: Path) -> bool:
    covers = mp4.tags.get("covr", []) if mp4.tags else []
    if not covers:
        return False
    cover_data = bytes(covers[0])
    dest.write_bytes(cover_data)
    return True


def extract_lyrics(mp4: MP4) -> str:
    if not mp4.tags:
        return ""
    lyr = mp4.tags.get("\xa9lyr", [])
    if not lyr:
        return ""
    return lyr[0] if isinstance(lyr, list) else str(lyr)


def split_lyric_lines(raw: str) -> list[str]:
    """歌词原文行切分: 用换行符分,过滤掉空行,但保留 [Intro ...] 节标记和中英双行。"""
    if "\r\n" in raw:
        lines = raw.split("\r\n")
    elif "\n" in raw:
        lines = raw.split("\n")
    else:
        # 极端情况: 单行无换行符,按句号/分号粗切
        lines = re.split(r"(?<=[。；;.])\s+", raw)
    return [ln.strip() for ln in lines if ln.strip()]


def gen_even_lrc(lines: list[str], duration: float, song_title: str, artist: str) -> str:
    """按时长平均分配时间戳,生成 LRC 文件内容。"""
    out = [
        f"[ti:{song_title}]",
        f"[ar:{artist}]",
    ]
    if not lines:
        return "\n".join(out) + "\n"
    # 给开头留 1 秒,结尾留 2 秒
    start = 1.0
    end = max(start + 1.0, duration - 2.0)
    span = end - start
    step = span / max(len(lines), 1)
    for i, line in enumerate(lines):
        t = start + i * step
        mm = int(t // 60)
        ss = t - mm * 60
        out.append(f"[{mm:02d}:{ss:05.2f}]{line}")
    return "\n".join(out) + "\n"


def main() -> int:
    if not SRC_ROOT.exists():
        print(f"ERROR: source dir 不存在: {SRC_ROOT}", file=sys.stderr)
        return 1

    summary = []

    for album in ALBUMS:
        print(f"\n=== {album.title} ({album.slug}) ===")
        src_dir = SRC_ROOT / album.src_dir
        if not src_dir.exists():
            print(f"  SKIP: {src_dir} 不存在")
            continue

        audio_out = PUBLIC / "audio" / album.slug
        lrc_out = PUBLIC / "lrc" / album.slug
        audio_out.mkdir(parents=True, exist_ok=True)
        lrc_out.mkdir(parents=True, exist_ok=True)

        # 收集所有音频文件(m4a + wav),按文件名排序
        files = sorted(
            [p for p in src_dir.iterdir() if p.suffix.lower() in (".m4a", ".wav")],
            key=lambda p: p.name,
        )

        cover_saved = False
        cover_filename = f"{album.slug}.jpg"
        cover_dest = PUBLIC / "covers" / cover_filename

        for idx, src in enumerate(files, start=1):
            track_slug = slugify(src.stem, 50)
            track_filename = f"{idx:02d}-{track_slug}.m4a"
            audio_dest = audio_out / track_filename

            # 拷贝或转码
            if src.suffix.lower() == ".m4a":
                copy_m4a(src, audio_dest)
                meta_src = src  # 元数据在原 m4a 里
            else:
                convert_wav(src, audio_dest)
                meta_src = src  # WAV 不带元数据, 但 m4a 同名文件可能有
                # 不到了就跳过

            # 读元数据(M4A only)
            try:
                mp4 = MP4(meta_src) if meta_src.suffix.lower() == ".m4a" else None
            except Exception:
                mp4 = None

            track_title = src.stem
            duration = 0.0
            lyrics_raw = ""

            if mp4 is not None and mp4.tags is not None:
                if "\xa9nam" in mp4.tags:
                    track_title = mp4.tags["\xa9nam"][0]
                duration = float(mp4.info.length)
                lyrics_raw = extract_lyrics(mp4)

                # 第一张能拿到的 cover 存到 covers/
                if not cover_saved:
                    if extract_cover(mp4, cover_dest):
                        cover_saved = True
                        print(f"  cover saved → {cover_dest.name}")
            else:
                # WAV: 用 ffprobe 也行,但简单起见用 afinfo
                try:
                    out = subprocess.run(
                        ["afinfo", str(src)],
                        capture_output=True, text=True, check=True,
                    ).stdout
                    m = re.search(r"estimated duration:\s*([\d.]+)\s*sec", out)
                    if m:
                        duration = float(m.group(1))
                except Exception:
                    duration = 180.0  # fallback

            # 清理 track_title 前缀的 "01 " 数字
            clean_title = re.sub(r"^\d+\s*", "", track_title)
            clean_title = clean_title.replace("_", ":")

            # 生成 LRC
            lyric_lines = split_lyric_lines(lyrics_raw) if lyrics_raw else ["(暂无歌词)"]
            lrc_text = gen_even_lrc(lyric_lines, duration, clean_title, "JiangJingyi")
            lrc_dest = lrc_out / f"{idx:02d}-{track_slug}.lrc"
            lrc_dest.write_text(lrc_text, encoding="utf-8")

            album.tracks.append({
                "idx": idx,
                "title": clean_title,
                "audio_path": f"/audio/{album.slug}/{track_filename}",
                "lrc_path": f"/lrc/{album.slug}/{idx:02d}-{track_slug}.lrc",
                "duration": int(duration),
            })

            print(f"  [{idx}] {clean_title}  ({int(duration)}s, {len(lyric_lines)} lines)")

        # 写 markdown
        md_path = CONTENT / f"{album.slug}.md"
        tracks_yaml = "\n".join(
            f"  - title: \"{t['title']}\"\n"
            f"    audio: {t['audio_path']}\n"
            f"    lrc: {t['lrc_path']}\n"
            f"    duration: {t['duration']}"
            for t in album.tracks
        )
        md = f"""---
title: "{album.title}"
subtitle: "{album.subtitle}"
year: 2026
cover: /covers/{cover_filename if cover_saved else 'lumen-placeholder.svg'}
bgColor: "{album.bg_color}"
accentColor: "{album.accent_color}"
description: |
  {album.description.replace(chr(10), chr(10) + '  ')}
artist: JiangJingyi
producedBy: SUNO
songs:
{tracks_yaml}
---

这里以后可以写专辑的 liner notes、创作背景、神学背景等。
Markdown 自由发挥。
"""
        md_path.write_text(md, encoding="utf-8")
        summary.append((album.slug, len(album.tracks)))
        print(f"  → {md_path.name} ({len(album.tracks)} tracks)")

    print("\n=== Summary ===")
    for slug, n in summary:
        print(f"  {slug}: {n} tracks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
