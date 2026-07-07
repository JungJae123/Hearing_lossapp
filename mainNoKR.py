# -*- coding: utf-8 -*-
"""
EarCare - Hearing Self-Check Kit (Kivy)

[Test on your Windows computer first]
    pip install kivy numpy
    python main.py

[What changed in this version]
- Removed the small Back/Forward buttons from the Results screen (those
  were the "two odd squares" -- Results already has Save/Test Again)
- New Age screen before Calibration: enter your age (or skip it) so the
  Results screen can add a comparison against the typical average for
  your age group ("above average" / "about average" / "below average")
"""

from kivy.config import Config
Config.set("input", "mouse", "mouse,disable_multitouch")

import json
import os
import tempfile
import wave
from datetime import datetime

import numpy as np

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


# =========================================================
# Font registration
# =========================================================
def _register_cjk_font():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "fonts", "NotoSansKR-Regular.ttf"),
        "C:/Windows/Fonts/malgun.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            LabelBase.register(name="Roboto", fn_regular=path)
            return path
    print("[EarCare] Warning: no CJK-compatible font found.")
    return None


_register_cjk_font()


# =========================================================
# CONFIG
# =========================================================
SAMPLE_RATE = 44100
START_FREQ = 8000
END_FREQ = 20000
STEP_HZ = 500
TONE_DURATION_SEC = 1.8
CALIBRATION_FREQ = 1000

COLOR_BG = (0.98, 0.96, 0.90, 1)
COLOR_TEXT = (0.24, 0.18, 0.10, 1)
COLOR_MUTED = (0.55, 0.48, 0.38, 1)
COLOR_ACCENT = (0.20, 0.55, 0.55, 1)
COLOR_ACCENT2 = (0.95, 0.72, 0.30, 1)
COLOR_DANGER = (0.88, 0.36, 0.30, 1)
COLOR_GOOD = (0.30, 0.62, 0.40, 1)
COLOR_CARD = (1.0, 1.0, 0.98, 1)
COLOR_WAVE = (0.20, 0.55, 0.55, 1)
COLOR_WAVE_HIGH = (0.95, 0.55, 0.20, 1)
COLOR_STEP_BADGE = (0.90, 0.87, 0.78, 1)
COLOR_NAV_DISABLED = (0.85, 0.83, 0.78, 1)
COLOR_DONE = (0.85, 0.93, 0.87, 1)
COLOR_PENDING = (0.94, 0.94, 0.90, 1)


# =========================================================
# Age -> expected typical hearing bracket
# =========================================================
AGE_BRACKET_STEPS = [
    (17000, "age_10_20"),
    (15000, "age_20_30"),
    (12000, "age_30_40"),
    (10000, "age_40_50"),
    (8000, "age_50_60"),
    (0, "age_60_plus"),
]

EXPECTED_HZ_FOR_BRACKET = {
    "age_10_20": 17000,
    "age_20_30": 15000,
    "age_30_40": 12000,
    "age_40_50": 10000,
    "age_50_60": 8000,
    "age_60_plus": 6000,
}


def estimate_age_bracket_key(freq):
    for threshold, key in AGE_BRACKET_STEPS:
        if freq >= threshold:
            return key
    return AGE_BRACKET_STEPS[-1][1]


def age_to_bracket_key(age):
    if age < 20:
        return "age_10_20"
    if age < 30:
        return "age_20_30"
    if age < 40:
        return "age_30_40"
    if age < 50:
        return "age_40_50"
    if age < 60:
        return "age_50_60"
    return "age_60_plus"


def comment_key_for(avg_freq):
    if avg_freq >= 15000:
        return "comment_good"
    if avg_freq >= 10000:
        return "comment_moderate"
    return "comment_caution"


# =========================================================
# Translations (no emoji -- plain text only)
# =========================================================
TRANSLATIONS = {
    "ko": {
        "lang_name": "\ud55c\uad6d\uc5b4",
        "app_name": "\uc774\uc5b4\ucf00\uc5b4",
        "app_subtitle": "\uccad\ub825 \uc790\uac00\uc9c4\ub2e8 \ud0a4\ud2b8",
        "step": "STEP {n}/4",
        "back_btn": "< \ub4a4\ub85c",
        "forward_btn": "\ub2e4\uc74c >",
        "intro_title": "\uccad\ub825 \uccb4\ud06c",
        "intro_body": (
            "\ub098\uc774\uac00 \ub4e4\uc218\ub85d \uc798 \uc548 \ub4e4\ub9ac\uac8c \ub418\ub294 "
            "\ub192\uc740 \uc74c\uc744 \uc5bc\ub9c8\ub098 \ub4e4\uc744 \uc218 \uc788\ub294\uc9c0 "
            "\uac04\ub2e8\ud788 \ud655\uc778\ud574\ubcf4\ub294 \uac74\uac15 \uccb4\ud06c\ud0a4\ud2b8\uc608\uc694. "
            "\uc758\ud559\uc801 \uc9c4\ub2e8\uc774 \uc544\ub2c8\ub2c8 \ucc38\uace0\ub85c\ub9cc \ubd10\uc8fc\uc138\uc694."
        ),
        "intro_bullets": (
            "\u2022 \uc774\uc5b4\ud3f0\uc744 \ucc29\uc6a9\ud574\uc8fc\uc138\uc694\n"
            "\u2022 \uc870\uc6a9\ud55c \uacf3\uc5d0\uc11c \uc9c4\ud589\ud574\uc8fc\uc138\uc694\n"
            "\u2022 \uc67c\ucabd\uacfc \uc624\ub978\ucabd\uc744 \uac01\uac01 \uac80\uc0ac\ud574\uc694\n"
            "\u2022 \uc18c\ub9ac\uac00 \uc548 \ub4e4\ub9ac\uba74 \ubc84\ud2bc\uc744 \ub20c\ub7ec\uc8fc\uc138\uc694"
        ),
        "start_btn": "\uc2dc\uc791\ud558\uae30",
        "history_btn": "\uc9c0\ub09c \uae30\ub85d \ubcf4\uae30",
        "age_title": "\ub098\uc774\ub97c \uc54c\ub824\uc8fc\uc138\uc694",
        "age_body": (
            "\uc785\ub825\ud558\uc2e0 \ub098\uc774\ub97c \uae30\uc900\uc73c\ub85c \ub610\ub798 \ud3c9\uade0\uacfc "
            "\ube44\uad50\ud55c \ubd84\uc11d\uc744 \uacb0\uacfc \ud654\uba74\uc5d0 \ubcf4\uc5ec\ub4dc\ub824\uc694. "
            "\uc6d0\ud558\uc9c0 \uc54a\uc73c\uba74 \uac74\ub108\ub6f0\uc5b4\ub3c4 \uad1c\ucc2e\uc544\uc694."
        ),
        "age_hint": "\ub098\uc774 \uc785\ub825 (\uc608: 45)",
        "age_invalid_msg": "\uc22b\uc790\ub85c \ub098\uc774\ub97c \uc785\ub825\ud574\uc8fc\uc138\uc694 (1~120)",
        "age_continue_btn": "\ub2e4\uc74c",
        "age_skip_btn": "\uac74\ub108\ub6f0\uae30",
        "calib_title": "\ubcfc\ub968 \ud655\uc778",
        "calib_body": (
            "\uc544\ub798 \ubc84\ud2bc\uc744 \ub20c\ub7ec \uae30\uc900 \uc18c\ub9ac\ub97c \ub4e4\uc5b4\ubcf4\uace0, "
            "\ud3b8\uc548\ud558\uac8c \ub4e4\ub9ac\ub294 \uc218\uc900\uc73c\ub85c \ubcfc\ub968\uc744 \ub9de\ucdb0\uc8fc\uc138\uc694."
        ),
        "play_ref_btn": "\uae30\uc900 \uc18c\ub9ac \ub4e4\uc5b4\ubcf4\uae30",
        "ready_btn": "\uc900\ube44\ub410\uc5b4\uc694, \uac80\uc0ac\ub85c",
        "hub_title": "\uac80\uc0ac\ub97c \uc120\ud0dd\ud558\uc138\uc694",
        "hub_body": "\uc67c\ucabd\uacfc \uc624\ub978\ucabd\uc744 \uac01\uac01 \uac80\uc0ac\ud574\uc8fc\uc138\uc694. \uc21c\uc11c\ub294 \uc0c1\uad00\uc5c6\uc5b4\uc694.",
        "ear_left": "\uc67c\ucabd \uadc0",
        "ear_right": "\uc624\ub978\ucabd \uadc0",
        "ear_pending": "\uc544\uc9c1 \uac80\uc0ac \uc804",
        "ear_done": "\uc644\ub8cc: {hz}Hz",
        "ear_test_btn": "\uac80\uc0ac \uc2dc\uc791",
        "ear_retest_btn": "\ub2e4\uc2dc \uac80\uc0ac",
        "view_results_btn": "\uacb0\uacfc \ubcf4\uae30",
        "hub_need_both": "\uc591\ucabd \uadc0\ub97c \ubaa8\ub450 \uac80\uc0ac\ud558\uba74 \uacb0\uacfc\ub97c \ubcfc \uc218 \uc788\uc5b4\uc694",
        "test_title_left": "\uc67c\ucabd \uadc0 \uac80\uc0ac \uc911",
        "test_title_right": "\uc624\ub978\ucabd \uadc0 \uac80\uc0ac \uc911",
        "test_body": (
            "\uc18c\ub9ac\uac00 \ub4e4\ub9ac\ub294 \ub3d9\uc548\uc740 \uae30\ub2e4\ub824\uc8fc\uc138\uc694. "
            "\ub354 \uc774\uc0c1 \uc548 \ub4e4\ub9ac\uba74 \uc544\ub798 \ubc84\ud2bc\uc744 \ub20c\ub7ec\uc8fc\uc138\uc694."
        ),
        "playing_status": "\uc7ac\uc0dd \uc911...",
        "cannot_hear_btn": "\uc774\uc81c \uc548 \ub4e4\ub824\uc694",
        "results_title": "\uac80\uc0ac \uacb0\uacfc",
        "results_left": "\uc67c\ucabd \uadc0: \uc57d {hz}Hz\uae4c\uc9c0 \uac10\uc9c0  ({age})",
        "results_right": "\uc624\ub978\ucabd \uadc0: \uc57d {hz}Hz\uae4c\uc9c0 \uac10\uc9c0  ({age})",
        "comment_good": (
            "\ud6cc\ub96d\ud574\uc694! \uc774 \uacb0\uacfc\ub294 \ub610\ub798 \ud3c9\uade0\ubcf4\ub2e4 \uc88b\uc740 "
            "\ud3b8\uc774\uc5d0\uc694. \uc9c0\uae08\ucc98\ub7fc \uadc0 \uac74\uac15\uc744 \uc798 \uc720\uc9c0\ud574\uc8fc\uc138\uc694."
        ),
        "comment_moderate": (
            "\ud3c9\uade0\uc801\uc778 \uc218\uc900\uc774\uc5d0\uc694. \ud070 \uc18c\ub9ac\uc5d0 \uc624\ub798 \ub178\ucd9c\ub418\uc9c0 "
            "\uc54a\ub3c4\ub85d \uc8fc\uc758\ud558\uace0, \uac00\ub054\uc529 \uadc0\ub97c \uc26c\uc5b4\uc8fc\uc138\uc694."
        ),
        "comment_caution": (
            "\ub192\uc740 \uc74c\uc5ed\ub300\uac00 \ub2e4\uc18c \uc798 \uc548 \ub4e4\ub9ac\ub294 \ud3b8\uc774\uc5d0\uc694. "
            "\uc774\uc5b4\ud3f0 \ubcfc\ub968\uc744 \ub0ae\ucd94\uace0, \uc2dc\ub044\ub7fd\uac70\ub098 \ubd88\ud3b8\ud568\uc774 "
            "\uc788\ub2e4\uba74 \uc774\ube44\uc778\ud6c4\uacfc \uc0c1\ub2f4\uc744 \uad8c\uc7a5\ub4dc\ub824\uc694."
        ),
        "compare_above": "\ud3c9\uade0 \uc774\uc0c1",
        "compare_average": "\ub610\ub798 \ud3c9\uade0\uacfc \ube44\uc2b7",
        "compare_below": "\ub610\ub798 \ud3c9\uade0\ubcf4\ub2e4 \ub0ae\uc74c",
        "age_comparison_line": (
            "\uc785\ub825\ud558\uc2e0 \ub098\uc774 \uae30\uc900 \ud3c9\uade0 \uc0c1\ud55c\uc740 \uc57d {expected}Hz\uc608\uc694. "
            "\uc774\ubc88 \uacb0\uacfc\ub294 {comparison}\uc774\uc5d0\uc694."
        ),
        "disclaimer": (
            "\uc774 \uacb0\uacfc\ub294 \ucc38\uace0\uc6a9\uc774\uc5d0\uc694. \uc815\ud655\ud55c \uccad\ub825 \uc0c1\ud0dc\ub294 "
            "\uc774\ube44\uc778\ud6c4\uacfc\uc5d0\uc11c \uac80\uc0ac\ubc1b\uc544\ubcf4\uc138\uc694."
        ),
        "save_btn": "\uc800\uc7a5\ud558\uae30",
        "retry_btn": "\ub2e4\uc2dc \uac80\uc0ac\ud558\uae30",
        "save_popup_title": "\uc774\ubc88 \uac80\uc0ac \uc774\ub984 \uc9c0\uc5b4\uc8fc\uae30",
        "save_popup_hint": "\uc608: 1\ucc28 \uac80\uc0ac",
        "save_popup_confirm": "\uc800\uc7a5",
        "save_popup_cancel": "\ucde8\uc18c",
        "history_title": "\uc9c0\ub09c \uae30\ub85d",
        "history_empty": "\uc800\uc7a5\ub41c \uae30\ub85d\uc774 \uc5c6\uc5b4\uc694.",
        "history_row": "{n}\ud68c\ucc28  |  {date}  |  {title}  |  L {left}Hz / R {right}Hz",
        "back_to_intro_btn": "\ucc98\uc74c\uc73c\ub85c",
        "age_10_20": "10~20\ub300",
        "age_20_30": "20~30\ub300",
        "age_30_40": "30~40\ub300",
        "age_40_50": "40~50\ub300",
        "age_50_60": "50~60\ub300",
        "age_60_plus": "60\ub300 \uc774\uc0c1",
    },
    "en": {
        "lang_name": "English",
        "app_name": "EarCare",
        "app_subtitle": "Hearing Self-Check Kit",
        "step": "STEP {n}/4",
        "back_btn": "< Back",
        "forward_btn": "Next >",
        "intro_title": "Hearing Check",
        "intro_body": (
            "A quick self-check of the highest pitch you can hear -- hearing "
            "tends to drop at high frequencies with age. Informal reference "
            "tool, not a medical diagnosis."
        ),
        "intro_bullets": (
            "\u2022 Wear headphones\n"
            "\u2022 Find a quiet room\n"
            "\u2022 Test each ear separately\n"
            "\u2022 Press the button when a tone becomes inaudible"
        ),
        "start_btn": "Start",
        "history_btn": "View Past Records",
        "age_title": "What's your age?",
        "age_body": "We'll compare your result to the typical average for your age group on the results screen. Feel free to skip.",
        "age_hint": "Enter age (e.g. 45)",
        "age_invalid_msg": "Please enter a number between 1 and 120",
        "age_continue_btn": "Next",
        "age_skip_btn": "Skip",
        "calib_title": "Volume Check",
        "calib_body": "Play the reference tone and set a comfortable volume. Keep it there for the whole test.",
        "play_ref_btn": "Play Reference Tone",
        "ready_btn": "Ready, Continue",
        "hub_title": "Choose a Test",
        "hub_body": "Test the left and right ear separately, in any order.",
        "ear_left": "Left Ear",
        "ear_right": "Right Ear",
        "ear_pending": "Not tested yet",
        "ear_done": "Done: {hz}Hz",
        "ear_test_btn": "Start Test",
        "ear_retest_btn": "Test Again",
        "view_results_btn": "View Results",
        "hub_need_both": "Test both ears to see your results",
        "test_title_left": "Testing Left Ear",
        "test_title_right": "Testing Right Ear",
        "test_body": "Wait while the tone plays. Press the button the moment you can no longer hear it.",
        "playing_status": "Playing...",
        "cannot_hear_btn": "I can't hear this",
        "results_title": "Results",
        "results_left": "Left ear: up to {hz}Hz  ({age})",
        "results_right": "Right ear: up to {hz}Hz  ({age})",
        "comment_good": "Great result! This is better than the average for your peers. Keep taking care of your hearing.",
        "comment_moderate": "This is an average result. Try to avoid loud noise exposure and rest your ears now and then.",
        "comment_caution": (
            "Your ears have a bit more trouble with high frequencies. Consider "
            "lowering headphone volume, and if you notice ringing or "
            "discomfort, see an ENT specialist."
        ),
        "compare_above": "above average",
        "compare_average": "about average",
        "compare_below": "below average",
        "age_comparison_line": "The typical upper limit for your age group is about {expected}Hz. Your result is {comparison}.",
        "disclaimer": "This result is informal. See an ENT specialist for an accurate hearing test.",
        "save_btn": "Save",
        "retry_btn": "Test Again",
        "save_popup_title": "Name this test",
        "save_popup_hint": "e.g. Test #1",
        "save_popup_confirm": "Save",
        "save_popup_cancel": "Cancel",
        "history_title": "Past Records",
        "history_empty": "No saved records yet.",
        "history_row": "#{n}  |  {date}  |  {title}  |  L {left}Hz / R {right}Hz",
        "back_to_intro_btn": "Back to Start",
        "age_10_20": "10s-20s",
        "age_20_30": "20s-30s",
        "age_30_40": "30s-40s",
        "age_40_50": "40s-50s",
        "age_50_60": "50s-60s",
        "age_60_plus": "60s+",
    },
    "ja": {
        "lang_name": "\u65e5\u672c\u8a9e",
        "app_name": "\u30a4\u30e4\u30b1\u30a2",
        "app_subtitle": "\u8074\u529b\u30bb\u30eb\u30d5\u30c1\u30a7\u30c3\u30af\u30ad\u30c3\u30c8",
        "step": "STEP {n}/4",
        "back_btn": "< \u623b\u308b",
        "forward_btn": "\u6b21\u3078 >",
        "intro_title": "\u8074\u529b\u30c1\u30a7\u30c3\u30af",
        "intro_body": (
            "\u5e74\u9f62\u3068\u3068\u3082\u306b\u4e0b\u304c\u308a\u3084\u3059\u3044\u9ad8\u3044\u97f3\u3092"
            "\u3069\u306e\u304f\u3089\u3044\u805e\u3053\u3048\u308b\u304b\u78ba\u8a8d\u3067\u304d\u307e\u3059\u3002"
            "\u533b\u5b66\u7684\u8a3a\u65ad\u3067\u306f\u3042\u308a\u307e\u305b\u3093\u3002"
        ),
        "intro_bullets": (
            "\u2022 \u30a4\u30e4\u30db\u30f3\u3092\u7740\u7528\n"
            "\u2022 \u9759\u304b\u306a\u5834\u6240\u3067\n"
            "\u2022 \u5de6\u53f3\u306e\u8033\u3092\u305d\u308c\u305e\u308c\u691c\u67fb\n"
            "\u2022 \u805e\u3053\u3048\u306a\u304f\u306a\u3063\u305f\u3089\u30dc\u30bf\u30f3\u3092"
        ),
        "start_btn": "\u306f\u3058\u3081\u308b",
        "history_btn": "\u904e\u53bb\u306e\u8a18\u9332",
        "age_title": "\u5e74\u9f62\u3092\u6559\u3048\u3066\u304f\u3060\u3055\u3044",
        "age_body": "\u5e74\u9f62\u306b\u5fdc\u3058\u305f\u5e73\u5747\u3068\u6bd4\u8f03\u3057\u307e\u3059\u3002\u30b9\u30ad\u30c3\u30d7\u3082\u53ef\u80fd\u3067\u3059\u3002",
        "age_hint": "\u5e74\u9f62\u5165\u529b\uff08\u4f8b\uff1a45\uff09",
        "age_invalid_msg": "1\u301c120\u306e\u6570\u5b57\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044",
        "age_continue_btn": "\u6b21\u3078",
        "age_skip_btn": "\u30b9\u30ad\u30c3\u30d7",
        "calib_title": "\u97f3\u91cf\u78ba\u8a8d",
        "calib_body": "\u57fa\u6e96\u97f3\u3092\u518d\u751f\u3057\u3066\u5feb\u9069\u306a\u97f3\u91cf\u306b\u8abf\u6574\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
        "play_ref_btn": "\u57fa\u6e96\u97f3\u3092\u518d\u751f",
        "ready_btn": "\u6e96\u5099OK",
        "hub_title": "\u691c\u67fb\u3092\u9078\u629e",
        "hub_body": "\u5de6\u53f3\u306e\u8033\u3092\u305d\u308c\u305e\u308c\u691c\u67fb\u3057\u307e\u3059\u3002\u9806\u756a\u306f\u81ea\u7531\u3067\u3059\u3002",
        "ear_left": "\u5de6\u8033",
        "ear_right": "\u53f3\u8033",
        "ear_pending": "\u672a\u691c\u67fb",
        "ear_done": "\u5b8c\u4e86: {hz}Hz",
        "ear_test_btn": "\u691c\u67fb\u958b\u59cb",
        "ear_retest_btn": "\u3082\u3046\u4e00\u5ea6",
        "view_results_btn": "\u7d50\u679c\u3092\u898b\u308b",
        "hub_need_both": "\u4e21\u8033\u3092\u691c\u67fb\u3059\u308b\u3068\u7d50\u679c\u304c\u898b\u3089\u308c\u307e\u3059",
        "test_title_left": "\u5de6\u8033\u691c\u67fb\u4e2d",
        "test_title_right": "\u53f3\u8033\u691c\u67fb\u4e2d",
        "test_body": "\u97f3\u304c\u805e\u3053\u3048\u3066\u3044\u308b\u9593\u306f\u304a\u5f85\u3061\u304f\u3060\u3055\u3044\u3002",
        "playing_status": "\u518d\u751f\u4e2d...",
        "cannot_hear_btn": "\u3082\u3046\u805e\u3053\u3048\u307e\u305b\u3093",
        "results_title": "\u7d50\u679c",
        "results_left": "\u5de6\u8033\uff1a\u7d04{hz}Hz\u307e\u3067\u691f\u77e5  \uff08{age}\uff09",
        "results_right": "\u53f3\u8033\uff1a\u7d04{hz}Hz\u307e\u3067\u691f\u77e5  \uff08{age}\uff09",
        "comment_good": "\u7d20\u6674\u3089\u3057\u3044\u7d50\u679c\u3067\u3059\uff01\u3053\u306e\u8abf\u5b50\u3067\u8033\u3092\u5927\u5207\u306b\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
        "comment_moderate": "\u5e73\u5747\u7684\u306a\u7d50\u679c\u3067\u3059\u3002\u5927\u304d\u306a\u97f3\u3092\u907f\u3051\u3001\u6642\u3005\u8033\u3092\u4f11\u307e\u305b\u3066\u3042\u3052\u3066\u304f\u3060\u3055\u3044\u3002",
        "comment_caution": (
            "\u9ad8\u3044\u97f3\u57df\u304c\u3084\u3084\u805e\u3053\u3048\u306b\u304f\u3044\u3088\u3046\u3067\u3059\u3002"
            "\u30a4\u30e4\u30db\u30f3\u306e\u97f3\u91cf\u3092\u4e0b\u3052\u3001\u5fc3\u914d\u306a\u3089\u8033\u9f3b\u54bd\u5674\u79d1"
            "\u3078\u306e\u76f8\u8ac7\u3092\u304a\u3059\u3059\u3081\u3057\u307e\u3059\u3002"
        ),
        "compare_above": "\u5e73\u5747\u4ee5\u4e0a",
        "compare_average": "\u5e73\u5747\u7a0b\u5ea6",
        "compare_below": "\u5e73\u5747\u3088\u308a\u4f4e\u3081",
        "age_comparison_line": "\u3042\u306a\u305f\u306e\u5e74\u4ee3\u306e\u5e73\u5747\u4e0a\u9650\u306f\u7d04{expected}Hz\u3067\u3059\u3002\u4eca\u56de\u306e\u7d50\u679c\u306f{comparison}\u3067\u3059\u3002",
        "disclaimer": "\u3053\u306e\u7d50\u679c\u306f\u53c2\u8003\u7528\u3067\u3059\u3002\u6b63\u78ba\u306a\u691c\u67fb\u306f\u8033\u9f3b\u54bd\u5674\u79d1\u3067\u3002",
        "save_btn": "\u4fdd\u5b58",
        "retry_btn": "\u3082\u3046\u4e00\u5ea6\u691c\u67fb",
        "save_popup_title": "\u4eca\u56de\u306e\u691c\u67fb\u540d",
        "save_popup_hint": "\u4f8b\uff1a\u7b2c1\u56de",
        "save_popup_confirm": "\u4fdd\u5b58",
        "save_popup_cancel": "\u30ad\u30e3\u30f3\u30bb\u30eb",
        "history_title": "\u904e\u53bb\u306e\u8a18\u9332",
        "history_empty": "\u4fdd\u5b58\u3055\u308c\u305f\u8a18\u9332\u306f\u3042\u308a\u307e\u305b\u3093\u3002",
        "history_row": "\u7b2c{n}\u56de  |  {date}  |  {title}  |  L {left}Hz / R {right}Hz",
        "back_to_intro_btn": "\u6700\u521d\u306b\u623b\u308b",
        "age_10_20": "10~20\u4ee3",
        "age_20_30": "20~30\u4ee3",
        "age_30_40": "30~40\u4ee3",
        "age_40_50": "40~50\u4ee3",
        "age_50_60": "50~60\u4ee3",
        "age_60_plus": "60\u4ee3\u4ee5\u4e0a",
    },
}


def tr(key, **fmt):
    app = App.get_running_app()
    lang = getattr(app, "language", "ko") if app else "ko"
    text = TRANSLATIONS.get(lang, TRANSLATIONS["ko"]).get(key, key)
    return text.format(**fmt) if fmt else text


# =========================================================
# Sound generation
# =========================================================

def generate_tone_wav_file(freq, duration_sec, ear="both", volume=0.4):
    t = np.linspace(0, duration_sec, int(SAMPLE_RATE * duration_sec), endpoint=False)
    tone = volume * np.sin(2 * np.pi * freq * t)

    fade_len = max(1, int(0.015 * SAMPLE_RATE))
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)
    tone[:fade_len] *= fade_in
    tone[-fade_len:] *= fade_out

    stereo = np.zeros((len(tone), 2), dtype=np.float32)
    if ear == "left":
        stereo[:, 0] = tone
    elif ear == "right":
        stereo[:, 1] = tone
    else:
        stereo[:, 0] = tone
        stereo[:, 1] = tone

    pcm16 = np.clip(stereo * 32767, -32768, 32767).astype(np.int16)

    fd, path = tempfile.mkstemp(suffix=".wav", prefix="earcare_")
    os.close(fd)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm16.tobytes())

    return path


def build_frequency_steps(start=START_FREQ, end=END_FREQ, step=STEP_HZ):
    return list(range(start, end + 1, step))


class HearingTestEngine:
    def __init__(self):
        self.frequencies = build_frequency_steps()
        self.current_ear = None
        self.current_index = 0
        self.thresholds = {"left": None, "right": None}

    def start_ear(self, ear):
        self.current_ear = ear
        self.current_index = 0

    def current_frequency(self):
        if self.current_index >= len(self.frequencies):
            return None
        return self.frequencies[self.current_index]

    def progress_fraction(self):
        return self.current_index / max(len(self.frequencies) - 1, 1)

    def advance(self):
        self.current_index += 1
        if self.current_index >= len(self.frequencies):
            self.thresholds[self.current_ear] = self.frequencies[-1]
            return True
        return False

    def record_response(self):
        freq = self.current_frequency()
        self.thresholds[self.current_ear] = freq
        return freq

    def both_done(self):
        return self.thresholds["left"] is not None and self.thresholds["right"] is not None


# =========================================================
# Reusable widgets
# =========================================================

class RoundedButton(Button):
    def __init__(self, bg_color=COLOR_ACCENT, radius=22, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.bold = True
        self._bg_color = bg_color
        with self.canvas.before:
            self._color_ctx = Color(*bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def set_disabled_look(self, disabled):
        self.disabled = disabled
        self._color_ctx.rgba = COLOR_NAV_DISABLED if disabled else self._bg_color
        self.color = COLOR_MUTED if disabled else (1, 1, 1, 1)


class OutlineButton(Button):
    def __init__(self, active=False, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.bold = active
        with self.canvas.before:
            self._fill = Color(*(COLOR_ACCENT if active else COLOR_CARD))
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
            Color(*COLOR_ACCENT)
            self._border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 10), width=1.2)
        self.color = (1, 1, 1, 1) if active else COLOR_ACCENT
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, 10)

    def set_active(self, active):
        self._fill.rgba = COLOR_ACCENT if active else COLOR_CARD
        self.color = (1, 1, 1, 1) if active else COLOR_ACCENT
        self.bold = active


class Card(BoxLayout):
    def __init__(self, radius=26, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.85, 0.80, 0.65, 0.5)
            self._shadow = RoundedRectangle(pos=(self.x - 2, self.y - 6), size=self.size, radius=[radius])
            Color(*COLOR_CARD)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._shadow.pos = (self.x - 2, self.y - 6)
        self._shadow.size = self.size


class StepBadge(Label):
    def __init__(self, **kwargs):
        super().__init__(
            color=COLOR_MUTED, font_size="13sp", bold=True,
            size_hint=(None, None), size=(100, 26), halign="center", valign="middle",
            **kwargs,
        )
        with self.canvas.before:
            Color(*COLOR_STEP_BADGE)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[13])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class NavBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=34, spacing=8, **kwargs)
        self.back_btn = RoundedButton(bg_color=COLOR_ACCENT2, radius=8, font_size="12sp",
                                       size_hint_x=None, width=90)
        self.forward_btn = RoundedButton(bg_color=COLOR_ACCENT2, radius=8, font_size="12sp",
                                          size_hint_x=None, width=90)
        self.back_btn.bind(on_release=lambda *_: App.get_running_app().go_back())
        self.forward_btn.bind(on_release=lambda *_: App.get_running_app().go_forward())
        self.add_widget(self.back_btn)
        self.add_widget(Widget())
        self.add_widget(self.forward_btn)

    def refresh(self):
        app = App.get_running_app()
        self.back_btn.text = tr("back_btn")
        self.forward_btn.text = tr("forward_btn")
        self.back_btn.set_disabled_look(len(app.nav_history) == 0)
        self.forward_btn.set_disabled_look(len(app.nav_forward) == 0)


class SineWaveWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.freq_display = START_FREQ
        self._phase = 0.0
        with self.canvas.before:
            Color(0.93, 0.95, 0.94, 1)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[20])
        with self.canvas:
            self._glow_color = Color(*COLOR_WAVE)
            self._glow_line = Line(points=[], width=7, cap="round", joint="round")
            self._mid_color = Color(*COLOR_WAVE)
            self._mid_line = Line(points=[], width=3.5, cap="round", joint="round")
            Color(1, 1, 1, 0.9)
            self._core_line = Line(points=[], width=1.6, cap="round", joint="round")
        self.bind(pos=self._on_geometry, size=self._on_geometry)
        Clock.schedule_interval(self._tick, 1 / 30.0)

    def set_frequency(self, freq):
        self.freq_display = freq

    def _on_geometry(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._redraw()

    def _tick(self, dt):
        self._phase += dt * 5.0
        self._redraw()

    def _color_for_freq(self):
        frac = np.clip((self.freq_display - START_FREQ) / (END_FREQ - START_FREQ), 0, 1)
        r = COLOR_WAVE[0] + (COLOR_WAVE_HIGH[0] - COLOR_WAVE[0]) * frac
        g = COLOR_WAVE[1] + (COLOR_WAVE_HIGH[1] - COLOR_WAVE[1]) * frac
        b = COLOR_WAVE[2] + (COLOR_WAVE_HIGH[2] - COLOR_WAVE[2]) * frac
        return (r, g, b)

    def _wave_points(self, amp_scale, phase_offset):
        cycles = np.interp(self.freq_display, [START_FREQ, END_FREQ], [3, 16])
        n_points = 160
        points = []
        for i in range(n_points):
            xf = i / (n_points - 1)
            x = self.x + xf * self.width
            y = self.y + self.height / 2 + (self.height * 0.30 * amp_scale) * np.sin(
                2 * np.pi * cycles * xf + self._phase + phase_offset
            )
            points.append(x)
            points.append(y)
        return points

    def _redraw(self):
        if self.width <= 0 or self.height <= 0:
            return
        r, g, b = self._color_for_freq()
        self._glow_color.rgba = (r, g, b, 0.30)
        self._mid_color.rgba = (r, g, b, 0.9)
        self._glow_line.points = self._wave_points(1.15, 0.15)
        self._mid_line.points = self._wave_points(1.0, 0.0)
        self._core_line.points = self._wave_points(0.55, -0.15)


class ResultBars(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.values = {"left": 0, "right": 0}
        self.max_value = END_FREQ + 1000
        with self.canvas.before:
            Color(0.94, 0.96, 0.95, 1)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
        self.bind(size=self._redraw, pos=self._redraw)

    def set_values(self, left, right):
        self.values = {"left": left, "right": right}
        self._redraw()

    def _redraw(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self.canvas.after.clear()
        if self.width <= 0 or self.height <= 0:
            return
        with self.canvas.after:
            keys = ["left", "right"]
            bar_colors = [COLOR_ACCENT, COLOR_ACCENT2]
            n = len(keys)
            gap = self.width * 0.18
            bar_width = (self.width - gap * (n + 1)) / n
            for i, k in enumerate(keys):
                value = self.values[k]
                frac = min(value / self.max_value, 1.0)
                bar_height = frac * (self.height - 40)
                x = self.x + gap + i * (bar_width + gap)
                y = self.y + 20
                Color(*bar_colors[i])
                RoundedRectangle(pos=(x, y), size=(bar_width, bar_height), radius=[10])


def _bind_auto_height(label, extra=6):
    def _update_text_size(instance, width):
        instance.text_size = (width, None)

    def _update_height(instance, texture_size):
        instance.height = texture_size[1] + extra

    label.bind(width=_update_text_size)
    label.bind(texture_size=_update_height)
    return label


def body_label(font_size="16sp"):
    lbl = Label(text="", color=COLOR_MUTED, font_size=font_size,
                halign="left", valign="top", size_hint_y=None, height=30)
    return _bind_auto_height(lbl)


def title_label():
    lbl = Label(text="", color=COLOR_TEXT, font_size="26sp", bold=True,
                size_hint_y=None, height=40, halign="left", valign="middle")
    return _bind_auto_height(lbl, extra=4)


# =========================================================
# Screens
# =========================================================

class LanguageRow(BoxLayout):
    def __init__(self, on_change, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=38, spacing=8, **kwargs)
        self.on_change = on_change
        self.buttons = {}
        for code in ("ko", "en", "ja"):
            btn = OutlineButton(text=TRANSLATIONS[code]["lang_name"], font_size="13sp",
                                 active=(code == "en"))
            btn.bind(on_release=lambda inst, c=code: self.on_change(c))
            self.buttons[code] = btn
            self.add_widget(btn)

    def set_active(self, code):
        for c, btn in self.buttons.items():
            btn.set_active(c == code)


class IntroScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        outer = BoxLayout(orientation="vertical", padding=18)
        card = Card(orientation="vertical", padding=26, spacing=10, size_hint=(1, 1))

        self.nav_bar = NavBar()
        card.add_widget(self.nav_bar)
        self.lang_row = LanguageRow(on_change=self._on_lang_change)
        card.add_widget(self.lang_row)

        self.brand_label = Label(text="", color=COLOR_ACCENT, font_size="24sp", bold=True,
                                  size_hint_y=None, height=40, halign="left", valign="middle")
        card.add_widget(self.brand_label)
        self.subtitle_label = Label(text="", color=COLOR_MUTED, font_size="14sp",
                                     size_hint_y=None, height=22, halign="left", valign="middle")
        card.add_widget(self.subtitle_label)

        self.title_lbl = title_label()
        card.add_widget(self.title_lbl)
        self.body_lbl = body_label()
        card.add_widget(self.body_lbl)
        self.bullets_lbl = body_label()
        card.add_widget(self.bullets_lbl)
        card.add_widget(Widget())

        self.history_btn = RoundedButton(size_hint_y=None, height=56, font_size="15sp", bg_color=COLOR_ACCENT2)
        self.history_btn.bind(on_release=lambda *_: App.get_running_app().go_to("history"))
        card.add_widget(self.history_btn)

        self.start_btn = RoundedButton(size_hint_y=None, height=72, font_size="19sp", bg_color=COLOR_ACCENT)
        self.start_btn.bind(on_release=lambda *_: App.get_running_app().go_to("age_input"))
        card.add_widget(self.start_btn)

        outer.add_widget(card)
        self.add_widget(outer)
        self.refresh_texts()

    def _on_lang_change(self, code):
        App.get_running_app().language = code
        self.lang_row.set_active(code)
        self.refresh_texts()

    def refresh_texts(self):
        self.nav_bar.refresh()
        self.brand_label.text = tr("app_name")
        self.subtitle_label.text = tr("app_subtitle")
        self.title_lbl.text = tr("intro_title")
        self.body_lbl.text = tr("intro_body")
        self.bullets_lbl.text = tr("intro_bullets")
        self.history_btn.text = tr("history_btn")
        self.start_btn.text = tr("start_btn")

    def on_pre_enter(self, *args):
        self.refresh_texts()


class AgeInputScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        outer = BoxLayout(orientation="vertical", padding=18)
        card = Card(orientation="vertical", padding=26, spacing=14, size_hint=(1, 1))

        self.nav_bar = NavBar()
        card.add_widget(self.nav_bar)
        self.step_badge = StepBadge()
        card.add_widget(self.step_badge)
        self.title_lbl = title_label()
        card.add_widget(self.title_lbl)
        self.body_lbl = body_label()
        card.add_widget(self.body_lbl)

        self.age_input = TextInput(
            multiline=False, input_filter="int", font_size="22sp",
            size_hint_y=None, height=58, padding=(16, 14),
            background_color=(1, 1, 1, 1), foreground_color=COLOR_TEXT,
        )
        card.add_widget(self.age_input)

        self.error_lbl = Label(text="", color=COLOR_DANGER, font_size="13sp",
                                size_hint_y=None, height=22, halign="left", valign="middle")
        self.error_lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        card.add_widget(self.error_lbl)

        card.add_widget(Widget())

        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=64, spacing=10)
        self.skip_btn = RoundedButton(bg_color=COLOR_NAV_DISABLED, font_size="15sp")
        self.skip_btn.bind(on_release=self._on_skip)
        self.continue_btn = RoundedButton(bg_color=COLOR_ACCENT, font_size="17sp")
        self.continue_btn.bind(on_release=self._on_continue)
        btn_row.add_widget(self.skip_btn)
        btn_row.add_widget(self.continue_btn)
        card.add_widget(btn_row)

        outer.add_widget(card)
        self.add_widget(outer)
        self.refresh_texts()

    def refresh_texts(self):
        self.nav_bar.refresh()
        self.step_badge.text = tr("step", n=1)
        self.title_lbl.text = tr("age_title")
        self.body_lbl.text = tr("age_body")
        self.age_input.hint_text = tr("age_hint")
        self.skip_btn.text = tr("age_skip_btn")
        self.continue_btn.text = tr("age_continue_btn")
        self.error_lbl.text = ""

    def on_pre_enter(self, *args):
        self.refresh_texts()

    def _on_skip(self, *_):
        App.get_running_app().user_age = None
        App.get_running_app().go_to("calibration")

    def _on_continue(self, *_):
        text = self.age_input.text.strip()
        try:
            age = int(text)
            if not (1 <= age <= 120):
                raise ValueError
        except ValueError:
            self.error_lbl.text = tr("age_invalid_msg")
            return
        App.get_running_app().user_age = age
        App.get_running_app().go_to("calibration")


class CalibrationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sound = None
        outer = BoxLayout(orientation="vertical", padding=18)
        card = Card(orientation="vertical", padding=26, spacing=12, size_hint=(1, 1))

        self.nav_bar = NavBar()
        card.add_widget(self.nav_bar)
        self.step_badge = StepBadge()
        card.add_widget(self.step_badge)
        self.title_lbl = title_label()
        card.add_widget(self.title_lbl)
        self.body_lbl = body_label()
        card.add_widget(self.body_lbl)
        card.add_widget(Widget())

        self.play_btn = RoundedButton(size_hint_y=None, height=64, font_size="16sp", bg_color=COLOR_ACCENT2)
        self.play_btn.bind(on_release=self._play_tone)
        card.add_widget(self.play_btn)

        self.ready_btn = RoundedButton(size_hint_y=None, height=72, font_size="19sp", bg_color=COLOR_ACCENT)
        self.ready_btn.bind(on_release=lambda *_: App.get_running_app().go_to("hub"))
        card.add_widget(self.ready_btn)

        outer.add_widget(card)
        self.add_widget(outer)
        self.refresh_texts()

    def refresh_texts(self):
        self.nav_bar.refresh()
        self.step_badge.text = tr("step", n=2)
        self.title_lbl.text = tr("calib_title")
        self.body_lbl.text = tr("calib_body")
        self.play_btn.text = tr("play_ref_btn")
        self.ready_btn.text = tr("ready_btn")

    def on_pre_enter(self, *args):
        self.refresh_texts()

    def on_leave(self, *args):
        if self._sound:
            self._sound.stop()

    def _play_tone(self, *_):
        if self._sound:
            self._sound.stop()
        path = generate_tone_wav_file(CALIBRATION_FREQ, 1.2, ear="both")
        self._sound = SoundLoader.load(path)
        if self._sound:
            self._sound.play()


class TestHubScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        outer = BoxLayout(orientation="vertical", padding=18)
        card = Card(orientation="vertical", padding=26, spacing=14, size_hint=(1, 1))

        self.nav_bar = NavBar()
        card.add_widget(self.nav_bar)
        self.step_badge = StepBadge()
        card.add_widget(self.step_badge)
        self.title_lbl = title_label()
        card.add_widget(self.title_lbl)
        self.body_lbl = body_label()
        card.add_widget(self.body_lbl)

        self.left_row = self._build_ear_row("left")
        card.add_widget(self.left_row["container"])
        self.right_row = self._build_ear_row("right")
        card.add_widget(self.right_row["container"])

        card.add_widget(Widget())

        self.hint_lbl = body_label(font_size="13sp")
        card.add_widget(self.hint_lbl)

        self.results_btn = RoundedButton(size_hint_y=None, height=72, font_size="19sp", bg_color=COLOR_GOOD)
        self.results_btn.bind(on_release=lambda *_: App.get_running_app().go_to("results"))
        card.add_widget(self.results_btn)

        outer.add_widget(card)
        self.add_widget(outer)
        self.refresh_texts()

    def _build_ear_row(self, ear):
        container = BoxLayout(orientation="horizontal", size_hint_y=None, height=76, spacing=12)
        with container.canvas.before:
            color_ctx = Color(*COLOR_PENDING)
            rect = RoundedRectangle(pos=container.pos, size=container.size, radius=[16])

        def _update(*_a):
            rect.pos = container.pos
            rect.size = container.size

        container.bind(pos=_update, size=_update)

        info_box = BoxLayout(orientation="vertical", padding=(14, 8))
        name_lbl = Label(text="", color=COLOR_TEXT, font_size="17sp", bold=True,
                          halign="left", valign="middle", size_hint_y=None, height=28)
        name_lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        status_lbl = Label(text="", color=COLOR_MUTED, font_size="13sp",
                            halign="left", valign="middle", size_hint_y=None, height=22)
        status_lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        info_box.add_widget(name_lbl)
        info_box.add_widget(status_lbl)
        container.add_widget(info_box)

        test_btn = RoundedButton(size_hint_x=None, width=140, font_size="14sp", bg_color=COLOR_ACCENT)
        test_btn.bind(on_release=lambda *_: self._start_ear(ear))
        container.add_widget(test_btn)

        return {
            "container": container, "color_ctx": color_ctx, "name_lbl": name_lbl,
            "status_lbl": status_lbl, "test_btn": test_btn,
        }

    def _start_ear(self, ear):
        app = App.get_running_app()
        app.engine.start_ear(ear)
        app.go_to("test")
        self.manager.get_screen("test").begin_step()

    def refresh_texts(self):
        self.nav_bar.refresh()
        app = App.get_running_app()
        self.step_badge.text = tr("step", n=3)
        self.title_lbl.text = tr("hub_title")
        self.body_lbl.text = tr("hub_body")

        for ear, row in (("left", self.left_row), ("right", self.right_row)):
            row["name_lbl"].text = tr("ear_left") if ear == "left" else tr("ear_right")
            freq = app.engine.thresholds[ear]
            if freq is None:
                row["status_lbl"].text = tr("ear_pending")
                row["test_btn"].text = tr("ear_test_btn")
                row["color_ctx"].rgba = COLOR_PENDING
            else:
                row["status_lbl"].text = tr("ear_done", hz=f"{freq:,}")
                row["test_btn"].text = tr("ear_retest_btn")
                row["color_ctx"].rgba = COLOR_DONE

        both = app.engine.both_done()
        self.results_btn.text = tr("view_results_btn")
        self.results_btn.set_disabled_look(not both)
        self.hint_lbl.text = "" if both else tr("hub_need_both")

    def on_pre_enter(self, *args):
        self.refresh_texts()


class TestScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sound = None
        self._current_path = None
        outer = BoxLayout(orientation="vertical", padding=18)
        card = Card(orientation="vertical", padding=24, spacing=10, size_hint=(1, 1))

        self.nav_bar = NavBar()
        card.add_widget(self.nav_bar)
        self.step_badge = StepBadge()
        card.add_widget(self.step_badge)
        self.ear_title = title_label()
        card.add_widget(self.ear_title)

        self.wave_widget = SineWaveWidget(size_hint_y=1)
        card.add_widget(self.wave_widget)

        self.body_lbl = body_label()
        card.add_widget(self.body_lbl)

        self.status_label = Label(text="", color=COLOR_ACCENT, font_size="18sp", bold=True,
                                   size_hint_y=None, height=36)
        card.add_widget(self.status_label)

        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=12)
        card.add_widget(self.progress)

        self.cannot_hear_btn = RoundedButton(size_hint_y=None, height=76, font_size="18sp", bg_color=COLOR_DANGER)
        self.cannot_hear_btn.bind(on_release=self._on_cannot_hear)
        card.add_widget(self.cannot_hear_btn)

        outer.add_widget(card)
        self.add_widget(outer)
        self.refresh_texts()

    def refresh_texts(self):
        self.nav_bar.refresh()
        app = App.get_running_app()
        ear = getattr(app.engine, "current_ear", None) if app else None
        self.step_badge.text = tr("step", n=3)
        self.ear_title.text = tr("test_title_right") if ear == "right" else tr("test_title_left")
        self.body_lbl.text = tr("test_body")
        self.status_label.text = tr("playing_status")
        self.cannot_hear_btn.text = tr("cannot_hear_btn")

    def on_pre_enter(self, *args):
        self.refresh_texts()

    def on_leave(self, *args):
        self._stop_and_cleanup()

    def _stop_and_cleanup(self):
        Clock.unschedule(self._on_tone_timeout)
        if self._sound:
            self._sound.stop()
            self._sound.unload()
            self._sound = None
        if self._current_path and os.path.exists(self._current_path):
            try:
                os.remove(self._current_path)
            except OSError:
                pass
            self._current_path = None

    def begin_step(self):
        self.refresh_texts()
        self._play_current_step()

    def _play_current_step(self):
        self._stop_and_cleanup()

        app = App.get_running_app()
        freq = app.engine.current_frequency()
        if freq is None:
            self._finish_ear()
            return

        self.progress.value = app.engine.progress_fraction() * 100
        self.wave_widget.set_frequency(freq)

        path = generate_tone_wav_file(freq, TONE_DURATION_SEC, ear=app.engine.current_ear)
        self._current_path = path
        self._sound = SoundLoader.load(path)
        if self._sound:
            self._sound.play()

        Clock.schedule_once(self._on_tone_timeout, TONE_DURATION_SEC)

    def _on_tone_timeout(self, *_):
        app = App.get_running_app()
        finished = app.engine.advance()
        if finished:
            self._finish_ear()
        else:
            self._play_current_step()

    def _on_cannot_hear(self, *_):
        self._stop_and_cleanup()
        app = App.get_running_app()
        app.engine.record_response()
        self._finish_ear()

    def _finish_ear(self):
        self._stop_and_cleanup()
        App.get_running_app().go_to("hub")


class ResultsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        outer = BoxLayout(orientation="vertical", padding=18)
        card = Card(orientation="vertical", padding=24, spacing=10, size_hint=(1, 1))

        # NOTE: no NavBar here on purpose -- Save / Test Again below cover
        # navigation, and the small nav buttons looked like odd squares.
        self.step_badge = StepBadge()
        card.add_widget(self.step_badge)
        self.title_lbl = title_label()
        card.add_widget(self.title_lbl)

        self.summary_label = Label(text="", color=COLOR_TEXT, font_size="15sp", bold=True,
                                    size_hint_y=None, height=30, halign="left", valign="top")
        _bind_auto_height(self.summary_label)
        card.add_widget(self.summary_label)

        self.chart = ResultBars(size_hint_y=None, height=140)
        card.add_widget(self.chart)

        self.comment_label = Label(text="", color=COLOR_TEXT, font_size="14sp",
                                    size_hint_y=None, height=30, halign="left", valign="top")
        _bind_auto_height(self.comment_label)
        card.add_widget(self.comment_label)

        self.age_compare_label = Label(text="", color=COLOR_ACCENT, font_size="14sp", bold=True,
                                        size_hint_y=None, height=30, halign="left", valign="top")
        _bind_auto_height(self.age_compare_label)
        card.add_widget(self.age_compare_label)

        self.disclaimer_lbl = body_label(font_size="12sp")
        card.add_widget(self.disclaimer_lbl)
        card.add_widget(Widget())

        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=64, spacing=10)
        self.save_btn = RoundedButton(font_size="16sp", bg_color=COLOR_ACCENT2)
        self.save_btn.bind(on_release=self._open_save_popup)
        self.retry_btn = RoundedButton(font_size="16sp", bg_color=COLOR_ACCENT)
        self.retry_btn.bind(on_release=self._retry)
        btn_row.add_widget(self.save_btn)
        btn_row.add_widget(self.retry_btn)
        card.add_widget(btn_row)

        outer.add_widget(card)
        self.add_widget(outer)
        self.refresh_texts()

    def refresh_texts(self):
        self.step_badge.text = tr("step", n=4)
        self.title_lbl.text = tr("results_title")
        self.disclaimer_lbl.text = tr("disclaimer")
        self.save_btn.text = tr("save_btn")
        self.retry_btn.text = tr("retry_btn")

    def on_pre_enter(self, *args):
        self.refresh_texts()
        self.populate()

    def populate(self):
        app = App.get_running_app()
        left_freq = app.engine.thresholds["left"]
        right_freq = app.engine.thresholds["right"]
        if left_freq is None or right_freq is None:
            return

        self.summary_label.text = (
            tr("results_left", hz=f"{left_freq:,}", age=tr(estimate_age_bracket_key(left_freq)))
            + "\n"
            + tr("results_right", hz=f"{right_freq:,}", age=tr(estimate_age_bracket_key(right_freq)))
        )
        self.chart.set_values(left_freq, right_freq)

        avg = (left_freq + right_freq) / 2
        self.comment_label.text = tr(comment_key_for(avg))

        user_age = getattr(app, "user_age", None)
        if user_age:
            bracket_key = age_to_bracket_key(user_age)
            expected = EXPECTED_HZ_FOR_BRACKET[bracket_key]
            if avg >= expected * 1.05:
                comparison = tr("compare_above")
            elif avg <= expected * 0.85:
                comparison = tr("compare_below")
            else:
                comparison = tr("compare_average")
            self.age_compare_label.text = tr(
                "age_comparison_line", expected=f"{expected:,}", comparison=comparison
            )
        else:
            self.age_compare_label.text = ""

    def _open_save_popup(self, *_):
        app = App.get_running_app()
        if not app.engine.both_done():
            return

        content = BoxLayout(orientation="vertical", padding=16, spacing=12)
        content.add_widget(Label(text=tr("save_popup_title"), color=COLOR_TEXT, size_hint_y=None, height=30))
        text_input = TextInput(hint_text=tr("save_popup_hint"), multiline=False, size_hint_y=None, height=44)
        content.add_widget(text_input)

        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=48, spacing=10)
        confirm_btn = RoundedButton(text=tr("save_popup_confirm"), bg_color=COLOR_ACCENT)
        cancel_btn = RoundedButton(text=tr("save_popup_cancel"), bg_color=COLOR_NAV_DISABLED)
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(confirm_btn)
        content.add_widget(btn_row)

        popup = Popup(title="", content=content, size_hint=(0.85, 0.4), separator_height=0)
        cancel_btn.bind(on_release=popup.dismiss)

        def _confirm(*_a):
            title = text_input.text.strip() or text_input.hint_text
            App.get_running_app().save_record(title)
            popup.dismiss()

        confirm_btn.bind(on_release=_confirm)
        popup.open()

    def _retry(self, *_):
        app = App.get_running_app()
        app.engine = HearingTestEngine()
        app.go_to("intro")


class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        outer = BoxLayout(orientation="vertical", padding=18)
        card = Card(orientation="vertical", padding=24, spacing=10, size_hint=(1, 1))

        self.nav_bar = NavBar()
        card.add_widget(self.nav_bar)
        self.title_lbl = title_label()
        card.add_widget(self.title_lbl)

        self.scroll = ScrollView(size_hint=(1, 1))
        self.list_layout = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=(0, 8))
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        card.add_widget(self.scroll)

        self.back_btn = RoundedButton(size_hint_y=None, height=60, font_size="15sp", bg_color=COLOR_ACCENT)
        self.back_btn.bind(on_release=lambda *_: App.get_running_app().go_to("intro"))
        card.add_widget(self.back_btn)

        outer.add_widget(card)
        self.add_widget(outer)

    def refresh_texts(self):
        self.nav_bar.refresh()
        self.title_lbl.text = tr("history_title")
        self.back_btn.text = tr("back_to_intro_btn")
        self._populate_list()

    def on_pre_enter(self, *args):
        self.refresh_texts()

    def _populate_list(self):
        self.list_layout.clear_widgets()
        app = App.get_running_app()
        records = app.load_records()
        if not records:
            lbl = body_label()
            lbl.text = tr("history_empty")
            self.list_layout.add_widget(lbl)
            return
        for rec in reversed(records):
            row_text = tr(
                "history_row", n=rec.get("id", "?"), date=rec.get("date", ""),
                title=rec.get("title", ""), left=rec.get("left", "?"), right=rec.get("right", "?"),
            )
            lbl = Label(
                text=row_text, color=COLOR_TEXT, font_size="13sp",
                size_hint_y=None, height=40, halign="left", valign="middle",
            )
            lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            self.list_layout.add_widget(lbl)


# =========================================================
# App
# =========================================================

class HearingTestApp(App):
    language = "en"

    def build(self):
        self.title = "EarCare"
        Window.clearcolor = COLOR_BG
        self.engine = HearingTestEngine()
        self.user_age = None
        self.nav_history = []
        self.nav_forward = []

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(IntroScreen(name="intro"))
        self.sm.add_widget(AgeInputScreen(name="age_input"))
        self.sm.add_widget(CalibrationScreen(name="calibration"))
        self.sm.add_widget(TestHubScreen(name="hub"))
        self.sm.add_widget(TestScreen(name="test"))
        self.sm.add_widget(ResultsScreen(name="results"))
        self.sm.add_widget(HistoryScreen(name="history"))
        return self.sm

    def go_to(self, name):
        if self.sm.current and self.sm.current != name:
            self.nav_history.append(self.sm.current)
            self.nav_forward.clear()
        self.sm.current = name

    def go_back(self):
        if not self.nav_history:
            return
        self.nav_forward.append(self.sm.current)
        self.sm.current = self.nav_history.pop()

    def go_forward(self):
        if not self.nav_forward:
            return
        self.nav_history.append(self.sm.current)
        self.sm.current = self.nav_forward.pop()

    def _history_path(self):
        return os.path.join(self.user_data_dir, "earcare_history.json")

    def load_records(self):
        path = self._history_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def save_record(self, title):
        records = self.load_records()
        record = {
            "id": len(records) + 1,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": title,
            "left": self.engine.thresholds["left"],
            "right": self.engine.thresholds["right"],
        }
        records.append(record)
        with open(self._history_path(), "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    HearingTestApp().run()


# =========================================================
# NEXT STEPS: turning this into an Android APK
# =========================================================
# 1. Download "Noto Sans KR" (Regular .ttf) from Google Fonts and place
#    it at ./fonts/NotoSansKR-Regular.ttf (required for the phone build).
# 2. Test on Windows first:  pip install kivy numpy  ->  python main.py
# 3. Build with Buildozer (Linux/WSL only):
#      wsl --install  ->  in Ubuntu: sudo apt install -y python3-pip git \
#        zip openjdk-17-jdk unzip  ->  pip3 install buildozer cython
#      Copy this folder (incl. fonts/) into WSL, then:
#        buildozer init  ->  edit buildozer.spec  ->  buildozer android debug
#      APK appears in bin/
