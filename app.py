#!/usr/bin/env python3
"""
MathWiz — learn mental-math tricks, practise them, and beat the clock.
Version 7 (complete): 36 lessons • 63 diagrams • difficulty tiers •
weak-spot drill • per-lesson tabs • quiz • progress persistence.

Run:  python mathwiz.py
Deps: pip install PySide6
"""
from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QTabWidget, QVBoxLayout,
    QWidget,
)

DIFF_NAMES = ["Easy", "Normal", "Hard"]

# --------------------------------------------------------------------------- #
#  Problem model
# --------------------------------------------------------------------------- #

@dataclass
class Problem:
    question: str
    answer: str
    hint: str
    steps: List[str]
    choices: Optional[List[str]] = None
    accept: Optional[List[str]] = None

def normalize(s: str) -> str:
    return s.strip().replace(",", "").replace(" ", "")

def answers_match(given: str, expected: str, accept=None) -> bool:
    g = normalize(given).lower()
    if not g: return False
    for opt in [expected, *(accept or [])]:
        o = normalize(opt).lower()
        if g == o: return True
        try:
            if float(g) == float(o): return True
        except ValueError: pass
    return False

PRAISE = ["✔ Correct!", "✔ Nice work!", "✔ Nailed it!", "✔ Brilliant!", "✔ Quick!"]

def _lvl(lvl, easy, normal, hard):
    return easy if lvl <= 0 else (normal if lvl == 1 else hard)

# --------------------------------------------------------------------------- #
#  Problem generators — every one takes a difficulty level 0/1/2
# --------------------------------------------------------------------------- #

def gen_mul11(lvl: int = 1) -> Problem:
    for _ in range(80):
        n = random.randint(*_lvl(lvl, (12, 49), (12, 99), (39, 99)))
        a, b = divmod(n, 10); s = a + b
        if lvl == 0 and s >= 10: continue
        if lvl == 2 and s < 10: continue
        break
    ans = n * 11
    if s < 10:
        steps = [f"Split the digits of {n}: <b>{a}</b> and <b>{b}</b>.", f"Add them: {a} + {b} = <b>{s}</b>.", f"Drop <b>{s}</b> in between: <b>{ans}</b>."]
    else:
        steps = [f"Split the digits of {n}: <b>{a}</b> and <b>{b}</b>.", f"Add them: {a} + {b} = <b>{s}</b> — two digits!", f"Carry the tens: first digit becomes {a} + 1 = <b>{a + 1}</b>, middle stays <b>{s - 10}</b>.", f"Read it off: <b>{ans}</b>."]
    return Problem(f"{n} × 11", str(ans), "Add the two digits and place the sum between them.", steps)

def gen_square5(lvl: int = 1) -> Problem:
    a = random.randint(*_lvl(lvl, (1, 4), (1, 9), (5, 12)))
    n = a * 10 + 5; prod = a * (a + 1); ans = n * n
    steps = [f"Take the part before the 5: <b>{a}</b>.", f"Multiply it by its neighbour: {a} × {a + 1} = <b>{prod}</b>.", f"Stick <b>25</b> on the end: <b>{ans}</b>."]
    return Problem(f"{n}²", str(ans), "Multiply the front by one more than itself, then append 25.", steps)

def gen_times9(lvl: int = 1) -> Problem:
    n = random.randint(*_lvl(lvl, (11, 39), (11, 69), (41, 99)))
    ans = n * 9
    steps = [f"{n} × 10 = <b>{n * 10}</b>.", f"Take one {n} away: {n * 10} − {n} = <b>{ans}</b>."]
    return Problem(f"{n} × 9", str(ans), "Multiply by 10, then subtract the number once.", steps)

def gen_times5(lvl: int = 1) -> Problem:
    n = random.randrange(12, 60, 2) if lvl == 0 else random.randint(*_lvl(lvl, (12, 99), (12, 99), (41, 99)))
    ans = n * 5
    if n % 2 == 0:
        steps = [f"Half of {n} is <b>{n // 2}</b>.", f"Add a zero (× 10): <b>{ans}</b>."]; hint = "Halve it, then multiply by 10."
    else:
        steps = [f"{n} is odd — round down to {n - 1}.", f"Half of {n - 1} is {n // 2}, times 10 gives {(n // 2) * 10}.", f"Add back the leftover 5: <b>{ans}</b>."]; hint = "Halve it (round down), × 10, then add 5."
    return Problem(f"{n} × 5", str(ans), hint, steps)

def gen_times25(lvl: int = 1) -> Problem:
    n = 4 * random.randint(*_lvl(lvl, (2, 6), (2, 14), (8, 24)))
    ans = n * 25
    steps = [f"Divide by 4: {n} ÷ 4 = <b>{n // 4}</b>.", f"Multiply by 100: <b>{ans}</b>."]
    return Problem(f"{n} × 25", str(ans), "25 goes into 100 four times: divide by 4, then × 100.", steps)

def gen_percent_flip(lvl: int = 1) -> Problem:
    base = random.choice(_lvl(lvl, [25, 50], [25, 50, 75], [25, 75]))
    if base == 50:
        small = random.choice(_lvl(lvl, [4, 6, 8], [4, 6, 8, 12, 14, 16, 18, 22, 24, 26], [4, 6, 8, 12, 14, 16, 18, 22, 24, 26, 28, 32, 36]))
    else:
        small = random.choice(_lvl(lvl, [4, 8, 12], [4, 8, 12, 16, 20, 24, 28, 32, 36, 40], [8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56]))
    ans = small * base // 100
    easy = (f"25% of {small} = {small} ÷ 4 = <b>{ans}</b>" if base == 25 else
            f"50% of {small} = {small} ÷ 2 = <b>{ans}</b>" if base == 50 else
            f"75% of {small} = {small} ÷ 4 × 3 = <b>{ans}</b>")
    steps = [f"Flip it! {small}% of {base} = <b>{base}% of {small}</b>.", easy + "."]
    return Problem(f"{small}% of {base}", str(ans), "Percentages flip: x% of y always equals y% of x.", steps)

def gen_double_half(lvl: int = 1) -> Problem:
    lo, hi = _lvl(lvl, (12, 48), (12, 98), (24, 148))
    a = random.randrange(lo, hi + 1, 2)
    b = random.choice(_lvl(lvl, [15, 25], [15, 25, 35, 45], [15, 25, 35, 45, 55, 65, 75]))
    x, y = a, b; steps = []
    while x % 2 == 0:
        nx, ny = x // 2, y * 2; steps.append(f"{x} × {y} → halve and double → <b>{nx} × {ny}</b>"); x, y = nx, ny
    steps.append(f"Now it's easy: {x} × {y} = <b>{a * b}</b>")
    return Problem(f"{a} × {b}", str(a * b), "One number is even: halve it, double the other, repeat.", steps)

def gen_near100(lvl: int = 1) -> Problem:
    rng = _lvl(lvl, (96, 99), (93, 99), (91, 99))
    a, b = random.randint(*rng), random.randint(*rng)
    da, db = 100 - a, 100 - b; left, right, ans = a - db, da * db, a * b
    steps = [f"How far below 100? {a} → <b>{da}</b>, &nbsp;{b} → <b>{db}</b>.", f"Subtract crosswise: {a} − {db} = <b>{left}</b>.", f"Multiply shortfalls: {da} × {db} = <b>{right:02d}</b>.", f"Join them: {left} | {right:02d} = <b>{ans}</b>."]
    return Problem(f"{a} × {b}", str(ans), "Subtract crosswise, multiply shortfalls.", steps)

def gen_round_square(lvl: int = 1) -> Problem:
    rng = _lvl(lvl, (21, 49), (21, 79), (21, 99))
    while True:
        n = random.randint(*rng); near = round(n / 10) * 10; d = abs(near - n)
        if d: break
    lo, hi = sorted((n - d, n + d)); ans = n * n
    steps = [f"{n} is <b>{d}</b> away from {near}.", f"Step {d} down and {d} up: {lo} × {hi} = <b>{lo * hi}</b>.", f"Add {d}² = {d * d}: <b>{ans}</b>."]
    return Problem(f"{n}²", str(ans), "n² = (n − d)(n + d) + d².", steps)

def gen_same_tens(lvl: int = 1) -> Problem:
    t = random.randint(*_lvl(lvl, (1, 4), (2, 9), (4, 9))); u = random.randint(1, 9); v = 10 - u
    a, b = 10 * t + u, 10 * t + v; front, back = t * (t + 1), u * v
    steps = [f"Same tens <b>{t}</b>, units make 10: {u} + {v} = 10. ✔", f"Front: {t} × {t + 1} = <b>{front}</b>.", f"Back: {u} × {v} = <b>{back:02d}</b>.", f"Glue: <b>{a * b}</b>."]
    return Problem(f"{a} × {b}", str(a * b), "Tens × (tens + 1), then units × units.", steps)

def gen_sub1000(lvl: int = 1) -> Problem:
    n = random.randint(*_lvl(lvl, (101, 499), (101, 999), (101, 999)))
    while n % 10 == 0: n = random.randint(*_lvl(lvl, (101, 499), (101, 999), (101, 999)))
    a, b, c = (int(d) for d in f"{n:03d}"); ans = 1000 - n
    steps = ["All from 9, last from 10:", f"9−{a}=<b>{9-a}</b> &nbsp; 9−{b}=<b>{9-b}</b> &nbsp; 10−{c}=<b>{10-c}</b>", f"Read it off: <b>{ans}</b>."]
    return Problem(f"1000 − {n}", str(ans), "Take every digit from 9, and the last one from 10.", steps)

def gen_divisibility(lvl: int = 1) -> Problem:
    rule = random.choice(_lvl(lvl, [3, 9], [3, 4, 6, 9], [3, 4, 6, 9, 11]))
    n = random.randint(*_lvl(lvl, (110, 499), (110, 999), (110, 999)))
    divisible = random.random() < 0.5
    r = n % rule
    if divisible:
        n -= r
        if n < 100: n += rule
    elif r == 0: n += 1 if n < 999 else -1
    ans = "Yes" if divisible else "No"; dig = [int(ch) for ch in str(n)]
    if rule in (3, 9):
        s = sum(dig); steps = [f"Digit sum: {' + '.join(map(str, dig))} = <b>{s}</b>.", f"{s} {'is' if divisible else 'is <b>not</b>'} divisible by {rule}.", f"Verdict: <b>{ans}</b>."]
    elif rule == 4:
        last = n % 100; steps = ["Only the <b>last two digits</b> matter.", f"<b>{last}</b> " + (f"÷ 4 = {last // 4} exactly." if divisible else "is not divisible by 4."), f"Verdict: <b>{ans}</b>."]
    elif rule == 6:
        s = sum(dig); steps = ["Must be <b>even</b> AND digit sum divisible by <b>3</b>.", f"{'Even ✔' if n % 2 == 0 else 'Odd ✘'}; sum {s} {'is' if s % 3 == 0 else 'is not'} divisible by 3.", f"Verdict: <b>{ans}</b>."]
    else:
        a, b, c = dig; alt = a - b + c
        steps = ["Alternating digit sum:", f"{a} − {b} + {c} = <b>{alt}</b>.", f"{'Is' if divisible else 'Is not'} a multiple of 11 → <b>{ans}</b>."]
    return Problem(f"Is {n} divisible by {rule}?", ans, "Use the digit tests — no long division.", steps, choices=["Yes", "No"])

def gen_mul12(lvl: int = 1) -> Problem:
    n = random.randint(*_lvl(lvl, (11, 19), (11, 29), (12, 49)))
    ans, t, d = n * 12, n * 10, n * 2
    steps = [f"{n} × 10 = <b>{t}</b>.", f"{n} × 2 = <b>{d}</b>.", f"Add them: {t} + {d} = <b>{ans}</b>."]
    return Problem(f"{n} × 12", str(ans), "Multiply by 10, then add double the number.", steps)

def gen_teens(lvl: int = 1) -> Problem:
    rng = _lvl(lvl, (2, 5), (2, 9), (4, 9))
    a, b = random.randint(*rng), random.randint(*rng)
    n1, n2 = 10 + a, 10 + b; front, back, ans = 10 + a + b, a * b, n1 * n2
    steps = [f"Add crosswise: {n1} + {b} = <b>{front}</b>.", f"Multiply units: {a} × {b} = <b>{back:02d}</b>.", f"Glue: {front} | {back:02d} = <b>{ans}</b>."]
    return Problem(f"{n1} × {n2}", str(ans), "Add crosswise for the front, multiply units for the back.", steps)

def gen_sq50(lvl: int = 1) -> Problem:
    d = random.randint(*_lvl(lvl, (1, 2), (1, 6), (4, 9)))
    if random.random() < 0.5: d = -d
    n = 50 + d; front, back, ans = 25 + d, d * d, n * n
    steps = [f"Distance from 50: {n} is <b>{d:+d}</b> away.", f"Add it to 25: 25 {'+' if d >= 0 else '−'} {abs(d)} = <b>{front}</b>.", f"Square the distance: {d}² = <b>{back:02d}</b>.", f"Join: <b>{ans}</b>."]
    return Problem(f"{n}²", str(ans), "Distance from 50 added to 25, then square the distance.", steps)

def gen_t99(lvl: int = 1) -> Problem:
    n = random.randint(*_lvl(lvl, (11, 39), (11, 59), (23, 99)))
    ans = n * 99
    steps = [f"{n} × 100 = <b>{n * 100}</b>.", f"Take one {n} away: {n * 100} − {n} = <b>{ans}</b>."]
    return Problem(f"{n} × 99", str(ans), "Multiply by 100, then subtract the number once.", steps)

def gen_d5(lvl: int = 1) -> Problem:
    n = 5 * random.randint(*_lvl(lvl, (3, 9), (3, 14), (7, 19)))
    ans = n // 5
    steps = [f"Double {n}: <b>{n * 2}</b>.", f"Divide by 10: <b>{ans}</b>."]
    return Problem(f"{n} ÷ 5", str(ans), "Double it, then divide by 10.", steps)

def gen_t15(lvl: int = 1) -> Problem:
    n = 2 * random.randint(*_lvl(lvl, (6, 12), (6, 19), (13, 29)))
    ans, t, h = n * 15, n * 10, (n * 10) // 2
    steps = [f"{n} × 10 = <b>{t}</b>.", f"Half of {t} is <b>{h}</b>.", f"Add them: {t} + {h} = <b>{ans}</b>."]
    return Problem(f"{n} × 15", str(ans), "Multiply by 10, then add half of that.", steps)

def gen_mul101(lvl: int = 1) -> Problem:
    n = random.randint(*_lvl(lvl, (10, 49), (10, 99), (10, 99)))
    ans = n * 101
    steps = [f"101 = 100 + 1, so {n} × 101 = {n}00 + {n}.", f"Adding just writes {n} a second time: <b>{ans}</b>."]
    return Problem(f"{n} × 101", str(ans), "A two-digit number × 101 is itself written twice.", steps)

def gen_t125(lvl: int = 1) -> Problem:
    k = random.randint(*_lvl(lvl, (2, 6), (2, 9), (5, 12)))
    n = 8 * k; ans = n * 125
    steps = [f"125 × 8 = 1000, so divide by 8 first: {n} ÷ 8 = <b>{k}</b>.", f"Then × 1000: <b>{ans}</b>."]
    return Problem(f"{n} × 125", str(ans), "125 goes into 1000 eight times: ÷ 8, then × 1000.", steps)

def gen_d25(lvl: int = 1) -> Problem:
    k = random.randint(*_lvl(lvl, (2, 19), (2, 29), (15, 39)))
    n = 25 * k; ans = k
    steps = [f"Double it: {n} × 2 = <b>{2 * n}</b>.", f"Double again: <b>{4 * n}</b>.", f"Divide by 100: <b>{ans}</b>."]
    return Problem(f"{n} ÷ 25", str(ans), "Multiply by 4 (double, double), then ÷ 100.", steps)

def gen_addrnd(lvl: int = 1) -> Problem:
    a = random.randint(*_lvl(lvl, (120, 380), (120, 580), (220, 880)))
    m = random.randint(2, _lvl(lvl, 2, 3, 4)); c = random.randint(1, _lvl(lvl, 4, 7, 9))
    up = random.random() < (0.75 if lvl == 0 else 0.5)
    b = m * 100 - c if up else m * 100 + c; ans = a + b
    if up:
        steps = [f"{b} is {c} below {m * 100} — borrow it: {a} + {m * 100} = <b>{a + m * 100}</b>.", f"Give the {c} back: {a + m * 100} − {c} = <b>{ans}</b>."]
        hint = f"Round {b} up to {m * 100}, add, then subtract {c}."
    else:
        steps = [f"{b} is {c} above {m * 100}: {a} + {m * 100} = <b>{a + m * 100}</b>.", f"Add the extra {c}: <b>{ans}</b>."]
        hint = f"Round {b} down to {m * 100}, add, then add {c}."
    return Problem(f"{a} + {b}", str(ans), hint, steps)

def gen_countup(lvl: int = 1) -> Problem:
    rng = _lvl(lvl, (11, 49), (11, 79), (31, 99))
    n = random.randint(*rng)
    while n % 10 == 0: n = random.randint(*rng)
    tens = (n // 10 + 1) * 10; h1, h2 = tens - n, 100 - tens; ans = h1 + h2
    steps = [f"Hop {n} → {tens}: that's +{h1}.", f"Hop {tens} → 100: that's +{h2}.", f"Total distance: {h1} + {h2} = <b>{ans}</b>."]
    return Problem(f"100 − {n}", str(ans), "Count up from the small number to 100; the hops are the answer.", steps)

def gen_splitmul(lvl: int = 1) -> Problem:
    a = random.randint(*_lvl(lvl, (11, 19), (12, 25), (12, 29)))
    t = random.randint(*_lvl(lvl, (2, 3), (2, 4), (2, 5))); u = random.randint(1, 9); b = t * 10 + u
    p1, p2, ans = a * t * 10, a * u, a * b
    steps = [f"Split {b} into {t * 10} + {u}.", f"{a} × {t * 10} = <b>{p1}</b>.", f"{a} × {u} = <b>{p2}</b>.", f"Add the parts: {p1} + {p2} = <b>{ans}</b>."]
    return Problem(f"{a} × {b}", str(ans), "Split the multiplier into tens and ones, multiply each, add.", steps)

def gen_t4(lvl: int = 1) -> Problem:
    n = random.randint(*_lvl(lvl, (12, 39), (12, 69), (23, 99)))
    ans = n * 4
    steps = [f"Double {n}: <b>{2 * n}</b>.", f"Double again: <b>{ans}</b>."]
    return Problem(f"{n} × 4", str(ans), "Doubling twice is multiplying by 4.", steps)

def gen_d4(lvl: int = 1) -> Problem:
    n = 4 * random.randint(*_lvl(lvl, (4, 19), (4, 34), (17, 49)))
    ans = n // 4
    steps = [f"Halve: {n} → <b>{n // 2}</b>.", f"Halve again: <b>{ans}</b>."]
    return Problem(f"{n} ÷ 4", str(ans), "Dividing by 4 is halving twice.", steps)

def gen_t19(lvl: int = 1) -> Problem:
    n = random.randint(*_lvl(lvl, (11, 29), (11, 44), (21, 69)))
    ans = n * 19
    steps = [f"{n} × 20 = <b>{n * 20}</b>.", f"Take one {n} away: {n * 20} − {n} = <b>{ans}</b>."]
    return Problem(f"{n} × 19", str(ans), "Multiply by 20, then subtract the number once.", steps)

def gen_t75(lvl: int = 1) -> Problem:
    n = 4 * random.randint(*_lvl(lvl, (2, 8), (2, 16), (9, 24)))
    ans = n * 75; q = n // 4; tq = q * 3
    steps = [f"75 is three quarters — find one: {n} ÷ 4 = <b>{q}</b>.", f"Take three: {q} × 3 = <b>{tq}</b>.", f"× 100: <b>{ans}</b>."]
    return Problem(f"{n} × 75", str(ans), "÷ 4, × 3, × 100 — 75 is three quarters.", steps)

def gen_subcomp(lvl: int = 1) -> Problem:
    b = random.choice(_lvl(lvl, [29, 38, 47, 49], [29, 38, 47, 49, 58, 67, 76, 79, 88, 89, 97, 98], [67, 76, 79, 88, 89, 97, 98]))
    bump = (b // 10 + 1) * 10 - b
    hi_a = _lvl(lvl, 99, 150, 260)
    a = random.randint(b + 20, max(b + 40, hi_a))
    ans = a - b; a2, b2 = a + bump, b + bump
    steps = [f"Add {bump} to both so the bottom rounds up: {a} − {b} = {a2} − {b2}.", f"Now it's easy: <b>{ans}</b>."]
    return Problem(f"{a} − {b}", str(ans), f"Add {bump} to both numbers — the difference doesn't change.", steps)

def gen_pct10(lvl: int = 1) -> Problem:
    base = random.choice(_lvl(lvl, [40, 60, 80], [40, 60, 80, 120, 140, 160], [40, 60, 80, 120, 140, 160, 180, 200]))
    tens = random.randint(1, _lvl(lvl, 4, 6, 7))
    half = random.random() < (0.25 if lvl == 0 else 0.5)
    pct = tens * 10 + (5 if half else 0)
    ten_pct = base // 10
    ans = tens * ten_pct + (ten_pct // 2 if half else 0)
    steps = [f"10% of {base} = <b>{ten_pct}</b>.", f"Take {tens} blocks: {tens} × {ten_pct} = <b>{tens * ten_pct}</b>."]
    if half: steps.append(f"Plus a 5% half-block (+{ten_pct // 2}): <b>{ans}</b>.")
    else: steps.append(f"Total: <b>{ans}</b>.")
    return Problem(f"{pct}% of {base}", str(ans), "Build it from 10% blocks; 5% is half a block.", steps)

def gen_t8(lvl: int = 1) -> Problem:
    n = random.randint(*_lvl(lvl, (11, 24), (11, 39), (21, 69)))
    ans = n * 8
    steps = [f"Double: <b>{2 * n}</b>.", f"Double again: <b>{4 * n}</b>.", f"Double once more: <b>{ans}</b>."]
    return Problem(f"{n} × 8", str(ans), "Doubling three times is multiplying by 8.", steps)

def gen_d8(lvl: int = 1) -> Problem:
    n = 8 * random.randint(*_lvl(lvl, (4, 14), (4, 24), (14, 40)))
    ans = n // 8
    steps = [f"Halve: <b>{n // 2}</b>.", f"Halve again: <b>{n // 4}</b>.", f"Halve once more: <b>{ans}</b>."]
    return Problem(f"{n} ÷ 8", str(ans), "Halving three times is dividing by 8.", steps)

def gen_diff2(lvl: int = 1) -> Problem:
    m = random.randint(*_lvl(lvl, (11, 29), (11, 44), (21, 69)))
    a, b = m - 1, m + 1; ans = a * b
    steps = [f"{a} and {b} straddle <b>{m}</b>.", f"{m}² = <b>{m * m}</b>.", f"Subtract 1: <b>{ans}</b>."]
    return Problem(f"{a} × {b}", str(ans), "Two apart? Square the middle and subtract 1.", steps)

def gen_midsq(lvl: int = 1) -> Problem:
    d = random.randint(*_lvl(lvl, (2, 3), (2, 4), (3, 6)))
    m = random.randint(*_lvl(lvl, (20, 39), (20, 49), (25, 69)))
    a, b = m - d, m + d; ans = a * b
    steps = [f"The middle is <b>{m}</b>; both numbers are {d} away.", f"{m}² = <b>{m * m}</b>.", f"Subtract d² = {d * d}: <b>{ans}</b>."]
    return Problem(f"{a} × {b}", str(ans), "a × b = middle² − d², where middle = (a + b) / 2.", steps)

def gen_bfly(lvl: int = 1) -> Problem:
    pool = _lvl(lvl, [2, 3, 4], [2, 3, 4, 5, 6], [2, 3, 4, 5, 6, 7, 8, 9])
    b = random.choice(pool); d = random.choice(pool)
    while d == b: d = random.choice(pool)
    a = random.randint(1, b - 1); c = random.randint(1, d - 1)
    ad, cb = a * d, c * b; num, den = ad + cb, b * d
    steps = [f"Cross-multiply: {a}×{d} = <b>{ad}</b> and {c}×{b} = <b>{cb}</b>.", f"Add the crosses: {ad} + {cb} = <b>{num}</b>.", f"Multiply denominators: {b}×{d} = <b>{den}</b>.", f"Result: <b>{num}/{den}</b>."]
    g = math.gcd(num, den)
    accept = [f"{num // g}/{den // g}"] if g > 1 else None
    return Problem(f"{a}/{b} + {c}/{d}", f"{num}/{den}", "Butterfly: cross-multiply, add the crosses, multiply the denominators.", steps, accept=accept)

def gen_pct1(lvl: int = 1) -> Problem:
    hundreds = random.randint(*_lvl(lvl, (2, 4), (2, 6), (3, 9)))
    base = hundreds * 100; pct = random.randint(*_lvl(lvl, (11, 24), (11, 32), (13, 49)))
    ans = pct * hundreds
    steps = [f"1% of {base} = <b>{hundreds}</b>.", f"So {pct}% = {pct} × {hundreds} = <b>{ans}</b>."]
    return Problem(f"{pct}% of {base}", str(ans), "Find 1% first, then multiply by the percent.", steps)

# --------------------------------------------------------------------------- #
#  Trick catalogue (36 lessons)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Trick:
    id: str; name: str; emoji: str; tagline: str; explanation: str; example: str; proof: str; cheat: str; generate: Callable[..., Problem]

TRICKS: List[Trick] = [
    Trick("mul11", "Multiply by 11", "🧩", "Split, add, drop it in the middle.", "Add the digits and place the sum between them. If the sum is 10+, carry the 1.", "<b>72 × 11</b>: 7+2=9 → <b>792</b><br><br><b>85 × 11</b>: 8+5=13 → <b>935</b>", "11(10a+b) = 100a + 10(a+b) + b", "72 × 11 → 7 _(9)_ 2 → 792", gen_mul11),
    Trick("sq5", "Square ending in 5", "5️⃣", "Multiply neighbour, stick on 25.", "Front × (Front+1), then append 25.", "<b>35²</b>: 3×4=12 → <b>1225</b><br><br><b>115²</b>: 11×12=132 → <b>13225</b>", "(10a+5)² = 100a(a+1) + 25", "35² → 3×4 | 25 → 1225", gen_square5),
    Trick("t9", "Multiply by 9", "9️⃣", "Times 10, take one away.", "n × 10 − n", "<b>27 × 9</b> = 270 − 27 = <b>243</b>", "9n = 10n − n", "27 × 9 = 270 − 27 = 243", gen_times9),
    Trick("t5", "Multiply by 5", "✋", "Halve it, add a zero.", "Halve, then × 10. Odd? Halve down, ×10, add 5.", "<b>84 × 5</b> = 42 × 10 = <b>420</b>", "5n = (n÷2) × 10", "84 × 5 = 420", gen_times5),
    Trick("t25", "Multiply by 25", "🪙", "Divide by 4, add two zeros.", "Divide by 4, then × 100.", "<b>36 × 25</b> = 9 × 100 = <b>900</b>", "25n = (n÷4) × 100", "36 × 25 = 900", gen_times25),
    Trick("pct", "Percentage flip", "🔁", "x% of y = y% of x.", "Flip the percentage to whichever side is easier.", "<b>8% of 25</b> = 25% of 8 = <b>2</b>", "x·y ÷ 100 is commutative", "8% of 25 = 2", gen_percent_flip),
    Trick("dbh", "Double & halve", "⚖️", "Halve one, double the other.", "Product stays the same while numbers get friendlier.", "<b>12 × 35</b> = 6×70 = 3×140 = <b>420</b>", "a·b = (a÷2)·(2b)", "12 × 35 = 3 × 140 = 420", gen_double_half),
    Trick("n100", "Near 100 multiply", "💯", "Shortfalls and cross-subtraction.", "Crosswise subtract, multiply shortfalls.", "<b>97 × 96</b> → 93 | 12 = <b>9312</b>", "(100-p)(100-q) = 100(100-p-q) + pq", "97 × 96 → 9312", gen_near100),
    Trick("rsq", "Squares near round", "🎯", "Borrow round, pay back d².", "n² = (n−d)(n+d) + d² around a multiple of 10.", "<b>47²</b> = 44×50 + 9 = <b>2209</b>", "Difference of squares", "47² = 2200 + 9 = 2209", gen_round_square),
    Trick("st10", "Same tens, units=10", "👯", "Same tens, units make ten.", "t(t+1) | u·v", "<b>43 × 47</b> → 20 | 21 = <b>2021</b>", "100t(t+1) + uv", "43 × 47 → 2021", gen_same_tens),
    Trick("s1000", "Subtract from 1000", "🏦", "All from 9, last from 10.", "Every digit from 9, the last from 10.", "<b>1000 − 476</b> = <b>524</b>", "1000−n = (999−n)+1", "1000 − 476 → 524", gen_sub1000),
    Trick("div", "Divisibility radar", "🔍", "Instant yes/no tests.", "3/9: digit sum • 4: last two • 6: even+3 • 11: alternating.", "<b>918</b> sum=18 → div by 9 ✔", "10 ≡ 1 (mod 3,9); 100 ≡ 0 (mod 4); 10 ≡ −1 (mod 11)", "3/9: sum • 4: last 2 • 11: alt sum", gen_divisibility),
    Trick("mul12", "Multiply by 12", "🕛", "Times 10 plus times 2.", "Multiply by 10, add double.", "<b>24 × 12</b> = 240 + 48 = <b>288</b>", "12n = 10n + 2n", "24 × 12 = 240 + 48 = 288", gen_mul12),
    Trick("teens", "Teen multiplication", "👦", "Add crosswise, multiply units.", "For 1a × 1b: front = 10+a+b, back = a·b.", "<b>13 × 14</b> → 17 | 12 = <b>182</b>", "(10+a)(10+b) = 100+10(a+b)+ab", "13 × 14 → 17 | 12 = 182", gen_teens),
    Trick("sq50", "Squares near 50", "🎯", "Distance from 50 added to 25.", "25 ± d | d²", "<b>54²</b> → 29 | 16 = <b>2916</b>", "(50±d)² = 2500 ± 100d + d²", "54² = 29 | 16 = 2916", gen_sq50),
    Trick("t99", "Multiply by 99", "🎰", "Times 100 minus times 1.", "Multiply by 100, subtract n.", "<b>45 × 99</b> = 4500 − 45 = <b>4455</b>", "99n = 100n − n", "45 × 99 = 4455", gen_t99),
    Trick("d5", "Divide by 5", "✌️", "Double it, divide by 10.", "× 2, then ÷ 10.", "<b>85 ÷ 5</b> = 170 ÷ 10 = <b>17</b>", "n/5 = 2n/10", "85 ÷ 5 = 17", gen_d5),
    Trick("t15", "Multiply by 15", "⏱️", "Times 10 plus half of that.", "× 10, add half.", "<b>24 × 15</b> = 240 + 120 = <b>360</b>", "15n = 10n + 10n/2", "24 × 15 = 360", gen_t15),
    Trick("mul101", "Multiply by 101", "🪞", "Write the number twice.", "A two-digit number × 101 is simply itself written twice.", "<b>47 × 101 = 4747</b><br><br><b>68 × 101 = 6868</b>", "101n = 100n + n: shifted and plain copies never overlap.", "47 × 101 = 4747", gen_mul101),
    Trick("t125", "Multiply by 125", "🧊", "Divide by 8, add three zeros.", "× 125 = ÷ 8 then × 1000.", "<b>32 × 125</b>: 32 ÷ 8 = 4 → <b>4000</b>", "125n = 1000n ÷ 8", "32 × 125 = 4000", gen_t125),
    Trick("d25", "Divide by 25", "📐", "Double twice, then ÷ 100.", "÷ 25 = × 4 then ÷ 100.", "<b>225 ÷ 25</b>: ×4 = 900 → <b>9</b>", "n ÷ 25 = 4n ÷ 100", "225 ÷ 25 = 9", gen_d25),
    Trick("addrnd", "Round-addition", "🎈", "Round it, add it, fix it.", "Round to the nearest hundred, add, correct by the tiny difference.", "<b>456 + 298</b> = 456 + 300 − 2 = <b>754</b>", "a + b = (a + r) ± e", "456 + 298 = 754", gen_addrnd),
    Trick("countup", "Count up to subtract", "🛒", "Subtraction is distance — hop up.", "Hop to the next ten, then to 100; add the hops.", "<b>100 − 37</b>: +3 +60 = <b>63</b>", "(t − n) + (100 − t) = 100 − n", "100 − 37 = 3 + 60 = 63", gen_countup),
    Trick("splitmul", "Split multiplication", "🧱", "Tens and ones, separately.", "Distribute over tens + ones, then add (area model).", "<b>23 × 45</b> = 920 + 115 = <b>1035</b>", "a(t + u) = at + au", "23 × 45 = 920 + 115 = 1035", gen_splitmul),
    Trick("t4", "Multiply by 4", "🐰", "Double it twice.", "4 is 2 × 2: double, then double again.", "<b>36 × 4</b>: 72 → <b>144</b>", "4n = 2·(2n)", "36 × 4 = 72 × 2 = 144", gen_t4),
    Trick("d4", "Divide by 4", "🍰", "Halve it twice.", "÷ 4 is halving twice.", "<b>132 ÷ 4</b>: 66 → <b>33</b>", "n ÷ 4 = (n ÷ 2) ÷ 2", "132 ÷ 4 = 66 ÷ 2 = 33", gen_d4),
    Trick("t19", "Multiply by 19", "🧮", "Twenty times, minus one.", "× 20 (double, ×10) then subtract one lot.", "<b>27 × 19</b> = 540 − 27 = <b>513</b>", "19n = 20n − n", "27 × 19 = 540 − 27 = 513", gen_t19),
    Trick("t75", "Multiply by 75", "🕰️", "Three quarters of 100.", "÷ 4, × 3, × 100.", "<b>36 × 75</b>: 9 → 27 → <b>2700</b>", "75n = (n ÷ 4)·3·100", "36 × 75 = 2700", gen_t75),
    Trick("subcomp", "Equal-shift subtraction", "↔️", "Move both numbers, keep the gap.", "Add the same k to both so the bottom rounds up.", "<b>83 − 47</b> = 86 − 50 = <b>36</b>", "(a + k) − (b + k) = a − b", "83 − 47 = 86 − 50 = 36", gen_subcomp),
    Trick("pct10", "Percent by blocks", "🧊", "Stack 10% blocks, add a 5% half.", "Build any percent from 10% blocks; 5% is half a block.", "<b>35% of 80</b>: 3×8 + 4 = <b>28</b>", "10% = ÷10; 5% = 10% ÷ 2", "35% of 80 = 3×8 + 4 = 28", gen_pct10),
    Trick("t8", "Multiply by 8", "🐙", "Double, double, double.", "8 is 2 × 2 × 2: three doublings in a row.", "<b>23 × 8</b>: 46 → 92 → <b>184</b>", "8n = 2·(2·(2n))", "23 × 8 = 46 → 92 → 184", gen_t8),
    Trick("d8", "Divide by 8", "🎂", "Halve, halve, halve.", "÷ 8 is halving three times.", "<b>184 ÷ 8</b>: 92 → 46 → <b>23</b>", "n ÷ 8 = ((n ÷ 2) ÷ 2) ÷ 2", "184 ÷ 8 = 92 → 46 → 23", gen_d8),
    Trick("diff2", "Pairs two apart", "👫", "Middle square minus one.", "Numbers 2 apart: square the middle, subtract 1.", "<b>24 × 26</b> = 25² − 1 = <b>624</b><br><br><b>39 × 41</b> = 40² − 1 = <b>1599</b>", "(m − 1)(m + 1) = m² − 1", "24 × 26 = 25² − 1 = 624", gen_diff2),
    Trick("midsq", "Middle-square product", "🌓", "middle² − distance².", "Same-parity pair: middle squared minus distance squared.", "<b>23 × 27</b> = 25² − 2² = <b>621</b><br><br><b>41 × 47</b> = 44² − 3² = <b>1927</b>", "(m − d)(m + d) = m² − d² with m = (a+b)/2", "23 × 27 = 25² − 2² = 621", gen_midsq),
    Trick("bfly", "Butterfly fractions", "🦋", "Cross, add, multiply.", "Cross-multiply for numerators, add them, multiply denominators.", "<b>1/3 + 1/4</b> = (4+3)/12 = <b>7/12</b><br><br><b>2/5 + 1/3</b> = (6+5)/15 = <b>11/15</b>", "a/b + c/d = (ad + bc)/bd", "1/3 + 1/4 = 7/12", gen_bfly),
    Trick("pct1", "The 1% method", "💠", "Find 1%, then scale.", "1% is just ÷ 100 — then multiply by the percent.", "<b>17% of 300</b> = 17 × 3 = <b>51</b><br><br><b>24% of 500</b> = 24 × 5 = <b>120</b>", "x% of n = x · (n/100)", "17% of 300 = 17 × 3 = 51", gen_pct1),
]

# --------------------------------------------------------------------------- #
#  Stylesheet
# --------------------------------------------------------------------------- #
STYLE = """
QWidget { background: #14161d; color: #e7eaf2; font-size: 14px; }
QLabel { background: transparent; }
#sidebar { background: #191c26; border-right: 1px solid #262b3b; }
#brand { font-size: 20px; font-weight: 800; color: #ffffff; padding: 18px 18px 10px 18px; }
#sideNote { color: #6d7488; font-size: 11px; padding: 8px 18px 14px 18px; }
QListWidget { background: transparent; border: none; font-size: 14px; outline: 0; }
QListWidget::item { padding: 9px 12px; margin: 2px 8px; border-radius: 8px; color: #c3c9da; }
QListWidget::item:selected { background: #2c3d68; color: #ffffff; }
QListWidget::item:hover:!selected { background: #212635; }
QScrollArea { border: none; background: transparent; }
QScrollArea QWidget { background: transparent; }
QFrame#card { background: #1c2029; border: 1px solid #2a3040; border-radius: 12px; }
QFrame#row { background: #1b202c; border-radius: 10px; }
QLabel#cardTitle { color: #85a4ff; font-size: 12px; font-weight: 700; letter-spacing: 1px; }
QLabel#pageTitle { font-size: 26px; font-weight: 800; color: #ffffff; }
QLabel#tagline { color: #9aa2b8; font-size: 15px; }
QLabel#question { font-size: 36px; font-weight: 800; color: #ffffff; padding: 8px 0; }
QLabel#dim { color: #8a91a5; font-size: 13px; }
QLabel#statBig { font-size: 18px; font-weight: 700; color: #ffffff; }
QLabel#finalScore { font-size: 44px; font-weight: 800; color: #ffd76a; }
QLabel#logo { font-size: 42px; font-weight: 800; color: #ffffff; }
QLabel.fbGood { color: #41d98d; font-weight: 700; font-size: 15px; }
QLabel.fbBad  { color: #ff7d7d; font-weight: 700; font-size: 15px; }
QLabel.hintLbl { color: #ffd479; font-size: 14px; }
QLabel.stepsLbl { color: #c7d3f5; font-size: 14px; }
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab { background: transparent; color: #9aa2b8; padding: 9px 18px; margin-right: 4px; font-weight: 600; border-radius: 9px; font-size: 14px; }
QTabBar::tab:selected { background: #262d40; color: #ffffff; }
QTabBar::tab:hover:!selected { background: #1d2230; color: #dfe3ee; }
QLineEdit { background: #101319; border: 2px solid #333b54; border-radius: 10px; padding: 10px 14px; font-size: 22px; color: #ffffff; }
QLineEdit:focus { border-color: #5b8def; }
QLineEdit[state="ok"] { border-color: #2fbf7f; background: #12241c; }
QLineEdit[state="bad"] { border-color: #e05a5a; background: #271619; }
QLineEdit:disabled { color: #9aa2b8; }
QPushButton { background: #2a3040; color: #e7eaf2; border: none; border-radius: 9px; padding: 9px 16px; font-weight: 600; }
QPushButton:hover { background: #333a50; }
QPushButton:pressed { background: #232838; }
QPushButton:disabled { background: #1d212c; color: #5c6377; }
QPushButton#primary { background: #4c7df0; color: #ffffff; }
QPushButton#primary:hover { background: #5e8bf6; }
QPushButton#primary:pressed { background: #3d6bd6; }
QPushButton#ghost { background: transparent; color: #9aa2b8; }
QPushButton#ghost:hover { background: #212635; color: #ffffff; }
QPushButton#choiceBtn { font-size: 18px; padding: 12px 28px; }
QProgressBar { background: #101319; border: none; border-radius: 6px; }
QProgressBar::chunk { background: #4c7df0; border-radius: 6px; }
QCheckBox { spacing: 8px; color: #dfe3ee; padding: 4px 2px; }
QCheckBox::indicator { width: 17px; height: 17px; border-radius: 5px; border: 2px solid #3a4157; background: #101319; }
QCheckBox::indicator:checked { background: #4c7df0; border-color: #4c7df0; }
QComboBox { background: #1c2029; border: 1px solid #333b54; border-radius: 8px; padding: 6px 12px; color: #ffffff; min-width: 70px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #1c2029; color: #ffffff; selection-background-color: #2c3d68; border: 1px solid #333b54; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2e3548; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3a4258; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #2e3548; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""

# --------------------------------------------------------------------------- #
#  Progress store (stats + settings)
# --------------------------------------------------------------------------- #
class ProgressStore:
    def __init__(self):
        self.path = Path.home() / ".mathwiz_progress.json"
        self.data = {"tricks": {}, "quiz": {"played": 0, "best_score": 0}, "settings": {}}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.data["tricks"].update(loaded.get("tricks", {}))
            self.data["quiz"].update(loaded.get("quiz", {}))
            self.data["settings"].update(loaded.get("settings", {}))
        except Exception: pass
    def _save(self):
        try: self.path.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        except Exception: pass
    def trick_stats(self, tid: str) -> dict:
        return self.data["tricks"].setdefault(tid, {"attempts": 0, "correct": 0, "best_streak": 0})
    def record_answer(self, tid: str, correct: bool, streak: int):
        t = self.trick_stats(tid); t["attempts"] += 1
        if correct: t["correct"] += 1; t["best_streak"] = max(t["best_streak"], streak)
        self._save()
    def record_quiz(self, score: int):
        q = self.data["quiz"]; q["played"] += 1; q["best_score"] = max(q["best_score"], score); self._save()
    def setting(self, key: str, default=None):
        return self.data["settings"].get(key, default)
    def set_setting(self, key: str, value):
        self.data["settings"][key] = value; self._save()
    def reset(self):
        settings = self.data.get("settings", {})
        self.data = {"tricks": {}, "quiz": {"played": 0, "best_score": 0}, "settings": settings}
        self._save()
    def totals(self):
        att = cor = best = 0
        for t in self.data["tricks"].values():
            att += t["attempts"]; cor += t["correct"]; best = max(best, t["best_streak"])
        return att, cor, best
    def weak_tricks(self, min_attempts: int = 4, threshold: int = 75) -> List[str]:
        return [tid for tid, st in self.data["tricks"].items()
                if st["attempts"] >= min_attempts and st["correct"] * 100 < threshold * st["attempts"]]

def set_edit_state(edit: QLineEdit, state: str):
    edit.setProperty("state", state); edit.style().unpolish(edit); edit.style().polish(edit)

# --------------------------------------------------------------------------- #
#  Diagram painting helpers
# --------------------------------------------------------------------------- #
C_TEXT, C_DIM, C_ACCENT, C_ACCENT_SOFT, C_ACCENT_TEXT = "#e7eaf2", "#8a91a5", "#4c7df0", "#2c3d68", "#cfe0ff"
C_GREEN, C_GREEN_SOFT = "#41d98d", "#1d3a2c"
C_YELLOW, C_YELLOW_SOFT = "#ffd76a", "#3a3320"
C_RED, C_RED_SOFT = "#ff7d7d", "#3a2430"
C_BOX, C_BOX_BORDER, C_PANEL, C_PANEL_BORDER = "#232838", "#3a4157", "#191d28", "#2a3040"

def _f(size: int, bold: bool = True) -> QFont:
    f = QFont(); f.setPointSize(size); f.setBold(bold); return f

def _rect(cx, cy, bw, bh) -> QRectF:
    return QRectF(cx - bw / 2, cy - bh / 2, bw, bh)

def rbox(p, cx, cy, bw, bh, txt="", fill=C_BOX, border=C_BOX_BORDER, fg=C_TEXT, size=15, radius=10):
    p.setBrush(QColor(fill)); p.setPen(QPen(QColor(border), 1.6))
    r = _rect(cx, cy, bw, bh); p.drawRoundedRect(r, radius, radius)
    if txt: p.setPen(QColor(fg)); p.setFont(_f(size)); p.drawText(r, Qt.AlignmentFlag.AlignCenter, txt)

def dtext(p, cx, cy, s, color=C_TEXT, size=14, bold=True, width=420):
    p.setPen(QColor(color)); p.setFont(_f(size, bold))
    p.drawText(QRectF(cx - width / 2, cy - 16, width, 32), Qt.AlignmentFlag.AlignCenter, s)

def arrow(p, x1, y1, x2, y2, color=C_ACCENT, width=2.4, head=10):
    p.setPen(QPen(QColor(color), width)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    ang = math.atan2(y2 - y1, x2 - x1)
    p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF([QPointF(x2, y2), QPointF(x2 - head * math.cos(ang - 0.45), y2 - head * math.sin(ang - 0.45)), QPointF(x2 - head * math.cos(ang + 0.45), y2 - head * math.sin(ang + 0.45))]))

def curve_arrow(p, x1, y1, x2, y2, bulge, color=C_ACCENT, head=10):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - bulge
    path = QPainterPath(); path.moveTo(x1, y1); path.quadTo(mx, my, x2, y2)
    p.setPen(QPen(QColor(color), 2.4)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(path)
    ang = math.atan2(y2 - my, x2 - mx)
    p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF([QPointF(x2, y2), QPointF(x2 - head * math.cos(ang - 0.45), y2 - head * math.sin(ang - 0.45)), QPointF(x2 - head * math.cos(ang + 0.45), y2 - head * math.sin(ang + 0.45))]))

def bubble(p, cx, cy, r, txt, fill=C_BOX, border=C_BOX_BORDER, fg=C_TEXT, size=14):
    p.setBrush(QColor(fill)); p.setPen(QPen(QColor(border), 1.8))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.setPen(QColor(fg)); p.setFont(_f(size))
    p.drawText(QRectF(cx - r, cy - r, 2 * r, 2 * r), Qt.AlignmentFlag.AlignCenter, txt)

def dot(p, x, y, color, r=7):
    p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(x, y), r, r)

# --------------------------------------------------------------------------- #
#  Diagrams — 63 total
# --------------------------------------------------------------------------- #
class Diagram(QWidget):
    H = 180
    def __init__(self, parent=None): super().__init__(parent); self.setFixedHeight(self.H); self.setMinimumWidth(480); self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); self.draw(p, self.width(), self.height()); p.end()
    def draw(self, p, w, h): pass

class Mul11Diagram(Diagram):
    H = 460
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 20, "72 × 11 — add the digits, drop the sum in the middle", C_DIM, 13, True, w)
        rbox(p, cx - 42, 64, 56, 50, "7", size=20); rbox(p, cx + 42, 64, 56, 50, "2", size=20)
        dtext(p, cx + 200, 64, "7 + 2 = 9", C_YELLOW, 15, width=140)
        arrow(p, cx - 42, 92, cx - 72, 126); arrow(p, cx + 42, 92, cx + 72, 126); arrow(p, cx + 145, 82, cx + 32, 134, C_YELLOW)
        rbox(p, cx - 72, 156, 56, 50, "7", size=20); rbox(p, cx, 156, 56, 50, "9", fill=C_ACCENT_SOFT, border=C_ACCENT, size=20); rbox(p, cx + 72, 156, 56, 50, "2", size=20)
        dtext(p, cx, 202, "= 792", C_GREEN, 18)
        dtext(p, cx, 246, "85 × 11 — the sum is 10 or more, so carry the 1", C_DIM, 13, True, w)
        rbox(p, cx - 42, 290, 56, 50, "8", size=20); rbox(p, cx + 42, 290, 56, 50, "5", size=20)
        dtext(p, cx + 205, 290, "8 + 5 = 13", C_RED, 15, width=140)
        arrow(p, cx - 42, 318, cx - 72, 352); arrow(p, cx + 42, 318, cx + 72, 352); arrow(p, cx + 150, 308, cx + 32, 360, C_RED)
        dtext(p, cx - 138, 382, "8+1", C_RED, 12, width=70)
        rbox(p, cx - 72, 382, 56, 50, "9", fill=C_RED_SOFT, border=C_RED, size=20); rbox(p, cx, 382, 56, 50, "3", fill=C_ACCENT_SOFT, border=C_ACCENT, size=20); rbox(p, cx + 72, 382, 56, 50, "5", size=20)
        dtext(p, cx, 428, "= 935", C_GREEN, 18)

class Mul11BarsDiagram(Diagram):
    H = 160
    def draw(self, p, w, h):
        cx = w / 2; x0 = cx - 230
        dtext(p, cx, 22, "Why it works: 72 × 11 = 72 × 10 + 72", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, 50, 330, 42), 8, 8)
        dtext(p, x0 + 165, 71, "72 × 10 = 720", C_ACCENT_TEXT, 14, width=300)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0 + 334, 50, 120, 42), 8, 8)
        dtext(p, x0 + 394, 71, "+ 72", C_YELLOW, 14, width=110)
        dtext(p, cx, 128, "720 + 72 = 792 — the 7 + 2 lands in the tens column", C_GREEN, 15, width=460)

class Sq5Diagram(Diagram):
    H = 160
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 24, "35² = (3 × 4) glued to 25", C_DIM, 13, True, w)
        rbox(p, cx - 210, 80, 92, 54, "35²", size=19); arrow(p, cx - 160, 80, cx - 120, 80)
        rbox(p, cx - 40, 80, 150, 54, "3 × 4 = 12", fill=C_ACCENT_SOFT, border=C_ACCENT, size=16)
        rbox(p, cx + 90, 80, 76, 54, "25", fill=C_YELLOW_SOFT, border=C_YELLOW, size=16); arrow(p, cx + 132, 80, cx + 172, 80)
        dtext(p, cx + 228, 80, "1225", C_GREEN, 20, width=120)

class Sq5TilesDiagram(Diagram):
    H = 235
    def draw(self, p, w, h):
        cx = w / 2; x0, y0, big, small = cx - 210, 40, 130, 45
        dtext(p, cx, 18, "35² as a cut-up square: (30 + 5)²", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, y0, big, big), 6, 6)
        dtext(p, x0 + big / 2, y0 + big / 2, "30² = 900", C_ACCENT_TEXT, 13, width=120)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0 + big + 4, y0, small, big), 6, 6)
        dtext(p, x0 + big + 4 + small / 2, y0 + big / 2, "150", C_YELLOW, 12, width=60)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0, y0 + big + 4, big, small), 6, 6)
        dtext(p, x0 + big / 2, y0 + big + 4 + small / 2, "150", C_YELLOW, 12, width=120)
        p.setBrush(QColor(C_GREEN_SOFT)); p.setPen(QPen(QColor(C_GREEN), 1.8)); p.drawRoundedRect(QRectF(x0 + big + 4, y0 + big + 4, small, small), 6, 6)
        dtext(p, x0 + big + 4 + small / 2, y0 + big + 4 + small / 2, "25", C_GREEN, 11, width=50)
        dtext(p, cx + 140, y0 + 50, "900 + 150 + 150 + 25", C_TEXT, 14, width=250)
        dtext(p, cx + 140, y0 + 85, "= 1225", C_GREEN, 18, width=200)
        dtext(p, cx + 140, y0 + 130, "900 + 300 = 12 hundreds", C_DIM, 12, width=250)
        dtext(p, cx + 140, y0 + 155, "— that's the 3 × 4!", C_DIM, 12, width=250)

class Times9Diagram(Diagram):
    H = 175
    def draw(self, p, w, h):
        cx = w / 2; x0, x1, cut = cx - 220, cx + 220, cx + 128
        dtext(p, cx, 22, "27 × 9 = 27 × 10 − 27", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, 50, cut - x0 - 4, 46), 10, 10)
        p.setBrush(QColor(C_RED_SOFT)); p.setPen(QPen(QColor(C_RED), 1.8)); p.drawRoundedRect(QRectF(cut, 50, x1 - cut, 46), 10, 10)
        dtext(p, (x0 + cut) / 2, 73, "27 × 10 = 270", C_ACCENT_TEXT, 15, width=280)
        dtext(p, (cut + x1) / 2, 73, "− 27", C_RED, 14, width=90)
        dtext(p, (x0 + cut) / 2, 132, "take one 27 away  →  243", C_GREEN, 17, width=340)

class Times9LineDiagram(Diagram):
    H = 185
    def draw(self, p, w, h):
        cx = w / 2; y = 100
        dtext(p, cx, 20, "27 × 9 on the number line: jump to 270, step back 27", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        dot(p, cx - 200, y, C_TEXT); dtext(p, cx - 200, y + 26, "0", C_DIM, 12, width=40)
        curve_arrow(p, cx - 200, y - 12, cx + 170, y - 12, 50, C_ACCENT)
        dtext(p, cx - 15, y - 72, "× 10 → 270", C_ACCENT, 14, width=160)
        dot(p, cx + 170, y, C_ACCENT); dtext(p, cx + 175, y + 26, "270", C_ACCENT, 12, width=60)
        curve_arrow(p, cx + 170, y - 10, cx + 118, y - 10, 24, C_RED)
        dtext(p, cx + 148, y - 42, "− 27", C_RED, 13, width=70)
        dot(p, cx + 118, y, C_GREEN); dtext(p, cx + 112, y + 46, "243", C_GREEN, 13, width=60)
        dtext(p, cx - 60, 168, "landing point = 27 × 9", C_GREEN, 14, width=300)

class Times5Diagram(Diagram):
    H = 145
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "84 × 5 — halve it, then add a zero", C_DIM, 13, True, w)
        rbox(p, cx - 175, 82, 84, 52, "84", size=19); arrow(p, cx - 128, 82, cx - 82, 82); dtext(p, cx - 105, 56, "halve", C_DIM, 12, width=80)
        rbox(p, cx - 35, 82, 84, 52, "42", size=19); arrow(p, cx + 12, 82, cx + 58, 82); dtext(p, cx + 35, 56, "× 10", C_DIM, 12, width=80)
        rbox(p, cx + 108, 82, 96, 52, "420", fill=C_ACCENT_SOFT, border=C_ACCENT, size=19)

class Times5HalfBarDiagram(Diagram):
    H = 175
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "84 × 5 is half of 84 × 10", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(cx - 220, 45, 150, 90), 8, 8)
        dtext(p, cx - 145, 78, "84 × 10", C_ACCENT_TEXT, 14, width=140); dtext(p, cx - 145, 102, "840", "#ffffff", 16, width=140)
        p.setBrush(QColor(C_GREEN_SOFT)); p.setPen(QPen(QColor(C_GREEN), 1.8)); p.drawRoundedRect(QRectF(cx - 20, 90, 150, 45), 8, 8)
        dtext(p, cx + 55, 112, "420", C_GREEN, 16, width=140)
        curve_arrow(p, cx - 110, 42, cx + 20, 82, 30, C_YELLOW); dtext(p, cx - 60, 36, "halve", C_YELLOW, 13, width=90)
        dtext(p, cx + 40, 156, "× 5 = × 10 then halve", C_GREEN, 15, width=320)

class Div5PartsDiagram(Diagram):
    H = 170
    def draw(self, p, w, h):
        cx = w / 2; x0, y0, W, Hh = cx - 225, 60, 350, 48
        dtext(p, cx, 22, "85 split into 5 equal parts", C_DIM, 13, True, w)
        pw = W / 5
        for i in range(5):
            hot = i == 0
            p.setBrush(QColor(C_ACCENT_SOFT if hot else C_PANEL)); p.setPen(QPen(QColor(C_ACCENT if hot else C_PANEL_BORDER), 1.6))
            p.drawRoundedRect(QRectF(x0 + i * pw + 2, y0, pw - 4, Hh), 6, 6)
            dtext(p, x0 + i * pw + pw / 2, y0 + Hh / 2, "17", C_ACCENT_TEXT if hot else C_DIM, 13, width=50)
        dtext(p, cx, 140, "one part = 17  →  85 ÷ 5 = 17", C_GREEN, 16, width=360)

class Times25Diagram(Diagram):
    H = 215
    def draw(self, p, w, h):
        cx = w / 2; sx, sy, side = cx - 260, 40, 122
        p.setBrush(QColor(C_PANEL)); p.setPen(QPen(QColor(C_PANEL_BORDER), 1.6)); p.drawRoundedRect(QRectF(sx, sy, side, side), 10, 10)
        p.setPen(QPen(QColor(C_BOX_BORDER), 1.2)); p.drawLine(QPointF(sx + side / 2, sy), QPointF(sx + side / 2, sy + side)); p.drawLine(QPointF(sx, sy + side / 2), QPointF(sx + side, sy + side / 2))
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(sx + 3, sy + 3, side / 2 - 4, side / 2 - 4), 6, 6)
        dtext(p, sx + side / 4, sy + side / 4, "25", C_ACCENT_TEXT, 13, width=50)
        for dx, dy in ((3 * side / 4, side / 4), (side / 4, 3 * side / 4), (3 * side / 4, 3 * side / 4)): dtext(p, sx + dx, sy + dy, "25", C_DIM, 12, width=50)
        dtext(p, sx + side / 2, sy + side + 24, "100 = 4 × 25", C_DIM, 13, width=200)
        rx = cx + 100
        dtext(p, rx, 36, "36 × 25", C_TEXT, 18, width=200); arrow(p, rx, 54, rx, 72)
        rbox(p, rx, 96, 196, 46, "36 ÷ 4 = 9", size=16); arrow(p, rx, 122, rx, 140)
        rbox(p, rx, 164, 196, 46, "9 × 100 = 900", fill=C_ACCENT_SOFT, border=C_ACCENT, size=16)

class Times25CoinsDiagram(Diagram):
    H = 170
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 18, "Think in quarters: four 25s make 100", C_DIM, 13, True, w)
        for i in range(4): bubble(p, cx - 150 + i * 60, 70, 24, "25", fill=C_YELLOW_SOFT, border=C_YELLOW, fg=C_YELLOW, size=13)
        dtext(p, cx + 120, 70, "= 100", C_GREEN, 16, width=120)
        dtext(p, cx, 130, "36 × 25 = 9 groups of four 25s = 9 × 100 = 900", C_GREEN, 15, width=460)

class PercentDiagram(Diagram):
    H = 195
    def draw(self, p, w, h):
        cx = w / 2
        curve_arrow(p, cx - 60, 44, cx + 60, 44, 26, C_YELLOW); dtext(p, cx, 14, "flip!", C_YELLOW, 13, width=80)
        rbox(p, cx - 130, 76, 190, 54, "8% of 25", size=17); rbox(p, cx + 130, 76, 190, 54, "25% of 8", fill=C_ACCENT_SOFT, border=C_ACCENT, size=17)
        dtext(p, cx, 76, "=", C_DIM, 22, width=40)
        arrow(p, cx - 130, 106, cx - 48, 138, C_GREEN); arrow(p, cx + 130, 106, cx + 48, 138, C_GREEN)
        rbox(p, cx, 160, 88, 46, "2", fill=C_GREEN_SOFT, border=C_GREEN, size=19)

class PercentScaleDiagram(Diagram):
    H = 200
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 18, "The flip balances: both pans are x·y ÷ 100", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_BOX_BORDER), 3)); p.drawLine(QPointF(cx - 170, 70), QPointF(cx + 170, 70))
        p.setBrush(QColor(C_BOX)); p.setPen(QPen(QColor(C_BOX_BORDER), 1.6))
        p.drawPolygon(QPolygonF([QPointF(cx, 70), QPointF(cx - 18, 108), QPointF(cx + 18, 108)]))
        for px, lab in ((cx - 150, "8% of 25"), (cx + 150, "25% of 8")):
            p.setPen(QPen(QColor(C_BOX_BORDER), 1.6)); p.drawLine(QPointF(px, 70), QPointF(px, 92))
            p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8))
            p.drawRoundedRect(QRectF(px - 70, 92, 140, 40), 8, 8)
            dtext(p, px, 112, lab, C_ACCENT_TEXT, 14, width=140)
        dtext(p, cx, 162, "= 2 on both pans", C_GREEN, 15, width=260)

class DoubleHalfDiagram(Diagram):
    H = 175
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "12 × 35 — halve one side, double the other", C_DIM, 13, True, w)
        step = min(150, (w - 60) / 4); xs = [cx - 1.5 * step + i * step for i in range(4)]
        labels = ["12 × 35", "6 × 70", "3 × 140", "= 420"]; bw = min(124, step - 24)
        for i, (x, lab) in enumerate(zip(xs, labels)):
            last = i == 3
            rbox(p, x, 88, bw, 54, lab, fill=C_ACCENT_SOFT if last else C_BOX, border=C_ACCENT if last else C_BOX_BORDER, fg=C_GREEN if last else C_TEXT, size=15)
        for i in range(3):
            arrow(p, xs[i] + bw / 2 + 3, 88, xs[i + 1] - bw / 2 - 3, 88)
            dtext(p, (xs[i] + xs[i + 1]) / 2, 56, "÷ 2 • × 2", C_YELLOW, 11, width=90)

class DoubleHalfAreaDiagram(Diagram):
    H = 270
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 18, "Same area, friendlier shape", C_DIM, 13, True, w)
        lx, ly, lw, lh = cx - 250, 80, 170, 100
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(lx, ly, lw, lh), 8, 8)
        dtext(p, lx + lw / 2, ly + lh / 2 - 10, "12 × 35", "#ffffff", 16, width=160)
        dtext(p, lx + lw / 2, ly + lh / 2 + 12, "area 420", C_ACCENT_TEXT, 12, width=160)
        dtext(p, lx + lw / 2, ly + lh + 18, "width 12", C_DIM, 11, width=100); dtext(p, lx - 28, ly + lh / 2, "35", C_DIM, 11, width=50)
        rx, ry, rw2, rh2 = cx + 90, 40, 85, 180
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(rx, ry, rw2, rh2), 8, 8)
        dtext(p, rx + rw2 / 2, ry + rh2 / 2 - 10, "6 × 70", "#ffffff", 16, width=100)
        dtext(p, rx + rw2 / 2, ry + rh2 / 2 + 12, "area 420", C_YELLOW, 12, width=100)
        dtext(p, rx + rw2 / 2, ry + rh2 + 16, "width 6", C_DIM, 11, width=80); dtext(p, rx + rw2 + 26, ry + rh2 / 2, "70", C_DIM, 11, width=50)
        arrow(p, cx - 60, 110, cx + 60, 110, C_YELLOW)
        dtext(p, cx, 92, "halve width", C_YELLOW, 12, width=140); dtext(p, cx, 128, "double height", C_YELLOW, 12, width=140)
        dtext(p, cx, 254, "the area never changes", C_GREEN, 14, width=300)

class Near100Diagram(Diagram):
    H = 270
    def draw(self, p, w, h):
        cx = w / 2; nx = cx - 60
        dtext(p, cx, 20, "97 × 96 — Vedic 'vertically and crosswise'", C_DIM, 13, True, w)
        rbox(p, nx, 60, 100, 46, "97", size=18); rbox(p, nx, 116, 100, 46, "96", size=18)
        dtext(p, nx + 110, 60, "−3", C_RED, 17, width=60); dtext(p, nx + 110, 116, "−4", C_RED, 17, width=60)
        p.setPen(QPen(QColor(C_BOX_BORDER), 1.6)); p.drawLine(QPointF(nx - 150, 152), QPointF(nx + 150, 152))
        rbox(p, nx - 55, 196, 98, 48, "93", fill=C_ACCENT_SOFT, border=C_ACCENT, size=19)
        rbox(p, nx + 53, 196, 82, 48, "12", fill=C_YELLOW_SOFT, border=C_YELLOW, size=19)
        dtext(p, cx, 246, "93 | 12  →  9312", C_GREEN, 18)

class Near100BarsDiagram(Diagram):
    H = 160
    def draw(self, p, w, h):
        cx = w / 2; x0 = cx - 240
        dtext(p, cx, 22, "97 × 96 = 93 hundreds + 12", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, 50, 340, 44), 8, 8)
        dtext(p, x0 + 170, 72, "93 × 100 = 9300", C_ACCENT_TEXT, 15, width=300)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0 + 344, 50, 90, 44), 8, 8)
        dtext(p, x0 + 389, 72, "+ 12", C_YELLOW, 14, width=90)
        dtext(p, cx, 128, "9300 + 12 = 9312", C_GREEN, 17, width=300)

class RoundSquareDiagram(Diagram):
    H = 225
    def draw(self, p, w, h):
        cx = w / 2; rx, ry, rw, rh = cx - 230, 58, 330, 84
        dtext(p, cx, 24, "47² — borrow the friendly number 50", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(rx, ry, rw, rh), 8, 8)
        dtext(p, rx + rw / 2, ry + rh / 2 - 12, "44 × 50", "#ffffff", 18, width=200)
        dtext(p, rx + rw / 2, ry + rh / 2 + 14, "= 2200", C_ACCENT_TEXT, 13, width=200)
        sx = rx + rw + 8
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(sx, ry + rh - 42, 42, 42), 6, 6)
        dtext(p, sx + 21, ry + rh - 21, "3²", C_YELLOW, 12, width=42)
        arrow(p, cx - 40, 150, cx - 40, 170, C_GREEN); dtext(p, cx - 40, 196, "47² = 2200 + 9 = 2209", C_GREEN, 18, width=340)

class RoundSqLineDiagram(Diagram):
    H = 185
    def draw(self, p, w, h):
        cx = w / 2; y = 108
        dtext(p, cx, 20, "47² — equal steps of d = 3 around the round number", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        for x, lab, col in ((cx - 170, "44", C_ACCENT), (cx - 60, "47", C_TEXT), (cx + 60, "50", C_GREEN), (cx + 170, "53", C_ACCENT)):
            dot(p, x, y, col); dtext(p, x, y + 26, lab, col, 13, width=60)
        curve_arrow(p, cx - 60, y - 12, cx + 60, y - 12, 24, C_YELLOW); dtext(p, cx, y - 46, "d = 3", C_YELLOW, 12, width=80)
        curve_arrow(p, cx + 60, y - 12, cx + 170, y - 12, 24, C_YELLOW); dtext(p, cx + 115, y - 46, "d = 3", C_YELLOW, 12, width=80)
        dtext(p, cx, 166, "44 × 50 + 3² = 2209", C_GREEN, 17, width=340)

class SameTensDiagram(Diagram):
    H = 160
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 24, "43 × 47 — the units add to 10 (3 + 7)", C_DIM, 13, True, w)
        rbox(p, cx - 215, 80, 104, 54, "43 × 47", size=17); arrow(p, cx - 158, 80, cx - 122, 80)
        rbox(p, cx - 42, 80, 150, 54, "4 × 5 = 20", fill=C_ACCENT_SOFT, border=C_ACCENT, size=16)
        rbox(p, cx + 90, 80, 120, 54, "3 × 7 = 21", fill=C_YELLOW_SOFT, border=C_YELLOW, size=16); arrow(p, cx + 155, 80, cx + 190, 80)
        dtext(p, cx + 245, 80, "2021", C_GREEN, 20, width=130)

class SameTensMidDiagram(Diagram):
    H = 185
    def draw(self, p, w, h):
        cx = w / 2; y = 105
        dtext(p, cx, 20, "43 and 47 straddle 45 — so 45² − 2²", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        for x, lab, col in ((cx - 160, "43", C_ACCENT), (cx, "45", C_GREEN), (cx + 160, "47", C_ACCENT)):
            dot(p, x, y, col); dtext(p, x, y + 26, lab, col, 13, width=60)
        curve_arrow(p, cx - 160, y - 12, cx, y - 12, 24, C_YELLOW); dtext(p, cx - 80, y - 46, "d = 2", C_YELLOW, 12, width=80)
        curve_arrow(p, cx, y - 12, cx + 160, y - 12, 24, C_YELLOW); dtext(p, cx + 80, y - 46, "d = 2", C_YELLOW, 12, width=80)
        dtext(p, cx, 166, "45² − 2² = 2025 − 4 = 2021", C_GREEN, 17, width=380)

class Sub1000Diagram(Diagram):
    H = 235
    def draw(self, p, w, h):
        cx = w / 2; xs = [cx - 80, cx, cx + 80]
        dtext(p, cx, 22, "1000 − 476 — all from 9, the last from 10", C_DIM, 13, True, w)
        for x, d in zip(xs, "476"): rbox(p, x, 70, 56, 50, d, size=20)
        ops, cols, res = ["9 − 4", "9 − 7", "10 − 6"], [C_DIM, C_DIM, C_YELLOW], "524"
        for x, op, col, r in zip(xs, ops, cols, res):
            dtext(p, x, 128, op, col, 13, width=90); arrow(p, x, 146, x, 162, col)
            rbox(p, x, 192, 56, 50, r, fill=C_GREEN_SOFT, border=C_GREEN, size=20)

class Sub1000LineDiagram(Diagram):
    H = 195
    def draw(self, p, w, h):
        cx = w / 2; y = 100
        dtext(p, cx, 20, "1000 − 476 as change-making: hop up to 1000", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        for x, lab, col in [(cx - 190, "476", C_TEXT), (cx - 120, "500", C_YELLOW), (cx + 60, "900", C_YELLOW), (cx + 190, "1000", C_GREEN)]:
            dot(p, x, y, col); dtext(p, x, y + 26, lab, col, 12, width=70)
        curve_arrow(p, cx - 190, y - 12, cx - 120, y - 12, 24, C_YELLOW); dtext(p, cx - 155, y - 44, "+24", C_YELLOW, 12, width=60)
        curve_arrow(p, cx - 120, y - 12, cx + 60, y - 12, 34, C_YELLOW); dtext(p, cx - 30, y - 54, "+400", C_YELLOW, 12, width=70)
        curve_arrow(p, cx + 60, y - 12, cx + 190, y - 12, 26, C_YELLOW); dtext(p, cx + 125, y - 46, "+100", C_YELLOW, 12, width=70)
        dtext(p, cx, 170, "24 + 400 + 100 = 524", C_GREEN, 16, width=340)

class DivisibilityDiagram(Diagram):
    H = 255
    def draw(self, p, w, h):
        cx = w / 2; pw, gap = max(170, min(200, (w - 80) / 3)), 16
        centers = [cx - pw - gap, cx, cx + pw + gap]
        for pcx in centers:
            p.setBrush(QColor(C_PANEL)); p.setPen(QPen(QColor(C_PANEL_BORDER), 1.6)); p.drawRoundedRect(QRectF(pcx - pw / 2, 34, pw, 180), 12, 12)
        p1 = centers[0]; dtext(p, p1, 58, "÷ 3 and ÷ 9", C_ACCENT, 13, width=200)
        for i, (x, d) in enumerate(zip([p1 - 44, p1, p1 + 44], "918")):
            if i: dtext(p, x - 22, 98, "+", C_DIM, 14, width=30)
            bubble(p, x, 98, 17, d)
        dtext(p, p1, 148, "9+1+8 = 18", C_TEXT, 14, width=200); dtext(p, p1, 178, "18 ÷ 9 ✔", C_GREEN, 12, width=200)
        p2 = centers[1]; dtext(p, p2, 58, "÷ 4", C_ACCENT, 13, width=200)
        dtext(p, p2 - 26, 98, "7", C_TEXT, 22, width=40)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(p2 - 2, 78, 58, 40), 8, 8)
        dtext(p, p2 + 27, 98, "28", C_ACCENT_TEXT, 20, width=54)
        dtext(p, p2, 148, "last two: 28", C_TEXT, 14, width=200); dtext(p, p2, 178, "28 ÷ 4 ✔", C_GREEN, 12, width=200)
        p3 = centers[2]; dtext(p, p3, 58, "÷ 11", C_ACCENT, 13, width=200)
        for x, d, sign in zip([p3 - 44, p3, p3 + 44], "528", ["+", "−", "+"]):
            dtext(p, x, 66, sign, C_YELLOW if sign == "−" else C_DIM, 13, width=30); bubble(p, x, 98, 17, d)
        dtext(p, p3, 148, "5 − 2 + 8 = 11", C_TEXT, 14, width=200); dtext(p, p3, 178, "11 ✔", C_GREEN, 12, width=200)

class DivModBarsDiagram(Diagram):
    H = 210
    def draw(self, p, w, h):
        cx = w / 2; x0 = cx - 250
        dtext(p, cx, 16, "Why the tests work: how 10 and 100 sit near multiples", C_DIM, 12, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.6)); p.drawRoundedRect(QRectF(x0, 44, 270, 34), 6, 6)
        dtext(p, x0 + 135, 61, "9", C_ACCENT_TEXT, 12, width=240)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.6)); p.drawRoundedRect(QRectF(x0 + 274, 44, 30, 34), 6, 6)
        dtext(p, x0 + 289, 61, "1", C_YELLOW, 11, width=30)
        dtext(p, cx + 150, 61, "10 = 9 + 1 → digit sums (3, 9)", C_DIM, 11, width=260)
        for i in range(4):
            p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.6)); p.drawRoundedRect(QRectF(x0 + i * 76 + 2, 100, 72, 34), 6, 6)
            dtext(p, x0 + i * 76 + 38, 117, "25", C_ACCENT_TEXT, 11, width=60)
        dtext(p, cx + 150, 117, "100 = 4 × 25 → last two digits (4)", C_DIM, 11, width=260)
        p.setBrush(QColor(C_PANEL)); p.setPen(QPen(QColor(C_PANEL_BORDER), 1.6)); p.drawRoundedRect(QRectF(x0, 156, 270, 34), 6, 6)
        dtext(p, x0 + 135, 173, "10", C_TEXT, 12, width=240)
        p.setBrush(QColor(C_RED_SOFT)); p.setPen(QPen(QColor(C_RED), 1.6)); p.drawRoundedRect(QRectF(x0 + 274, 156, 30, 34), 6, 6)
        dtext(p, x0 + 289, 173, "1", C_RED, 11, width=30)
        dtext(p, cx + 150, 173, "10 = 11 − 1 → alternating signs (11)", C_DIM, 11, width=260)

class Mul12Diagram(Diagram):
    H = 160
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "24 × 12 — times 10 plus times 2", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(cx - 220, 50, 300, 40), 8, 8)
        dtext(p, cx - 70, 70, "24 × 10 = 240", C_ACCENT_TEXT, 14, width=280)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(cx + 90, 50, 130, 40), 8, 8)
        dtext(p, cx + 155, 70, "24 × 2 = 48", C_YELLOW, 14, width=120)
        arrow(p, cx, 95, cx, 115, C_GREEN); dtext(p, cx, 135, "240 + 48 = 288", C_GREEN, 18)

class Mul12SplitDiagram(Diagram):
    H = 190
    def draw(self, p, w, h):
        cx = w / 2; x0 = cx - 230
        dtext(p, cx, 20, "24 × 12 as area: 24×10 plus 24×2", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, 50, 300, 46), 8, 8)
        dtext(p, x0 + 150, 73, "24 × 10 = 240", C_ACCENT_TEXT, 15, width=280)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0, 102, 130, 40), 8, 8)
        dtext(p, x0 + 65, 122, "24 × 2 = 48", C_YELLOW, 13, width=140)
        dtext(p, x0 - 28, 99, "24", C_DIM, 12, width=50)
        dtext(p, x0 + 95, 165, "240 + 48 = 288", C_GREEN, 17, width=320)

class TeensDiagram(Diagram):
    H = 220
    def draw(self, p, w, h):
        cx = w / 2; nx = cx - 60
        dtext(p, cx, 20, "13 × 14 — add crosswise, multiply units", C_DIM, 13, True, w)
        rbox(p, nx, 60, 100, 46, "13", size=18); rbox(p, nx, 116, 100, 46, "14", size=18)
        dtext(p, nx + 110, 60, "3", C_YELLOW, 17, width=60); dtext(p, nx + 110, 116, "4", C_YELLOW, 17, width=60)
        dtext(p, nx - 120, 88, "13 + 4 = 17", C_ACCENT, 14, width=140); dtext(p, nx + 200, 88, "3 × 4 = 12", C_YELLOW, 14, width=140)
        p.setPen(QPen(QColor(C_BOX_BORDER), 1.6)); p.drawLine(QPointF(nx - 150, 152), QPointF(nx + 150, 152))
        rbox(p, nx - 55, 186, 98, 48, "17", fill=C_ACCENT_SOFT, border=C_ACCENT, size=19)
        rbox(p, nx + 53, 186, 82, 48, "12", fill=C_YELLOW_SOFT, border=C_YELLOW, size=19)

class TeensTilesDiagram(Diagram):
    H = 230
    def draw(self, p, w, h):
        cx = w / 2; x0, y0, ten, three, four = cx - 200, 42, 110, 33, 44
        dtext(p, cx, 16, "13 × 14 as four areas: (10+3)(10+4)", C_DIM, 12, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, y0, ten, ten), 6, 6)
        dtext(p, x0 + ten / 2, y0 + ten / 2, "10×10 = 100", C_ACCENT_TEXT, 12, width=110)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0 + ten + 4, y0, three, ten), 6, 6)
        dtext(p, x0 + ten + 4 + three / 2, y0 + ten / 2, "30", C_YELLOW, 11, width=34)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0, y0 + ten + 4, ten, four), 6, 6)
        dtext(p, x0 + ten / 2, y0 + ten + 4 + four / 2, "40", C_YELLOW, 12, width=110)
        p.setBrush(QColor(C_GREEN_SOFT)); p.setPen(QPen(QColor(C_GREEN), 1.8)); p.drawRoundedRect(QRectF(x0 + ten + 4, y0 + ten + 4, three, four), 6, 6)
        dtext(p, x0 + ten + 4 + three / 2, y0 + ten + 4 + four / 2, "12", C_GREEN, 11, width=34)
        dtext(p, cx + 140, y0 + 45, "100 + 30 + 40 + 12", C_TEXT, 14, width=230)
        dtext(p, cx + 140, y0 + 80, "= 182", C_GREEN, 19, width=200)
        dtext(p, cx, 212, "exactly 13 × 14", C_DIM, 12, True, w)

class Sq50Diagram(Diagram):
    H = 200
    def draw(self, p, w, h):
        cx = w / 2; y = 90
        dtext(p, cx, 20, "54² — distance from 50 added to 25", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 200, y), QPointF(cx + 200, y))
        for val, x_off in [(-25, -150), (0, 0), (25, 150)]:
            px = cx + x_off; p.drawLine(QPointF(px, y - 8), QPointF(px, y + 8))
            dtext(p, px, y + 24, str(25 + val) if val != 0 else "50", C_DIM, 12, width=60)
        px54 = cx + 24
        dot(p, px54, y, C_ACCENT, 8); dtext(p, px54, y - 24, "54", C_ACCENT, 14, width=60)
        arrow(p, px54, y + 40, cx - 60, 140, C_YELLOW); dtext(p, cx - 60, 160, "25 + 4 = 29", C_YELLOW, 14, width=140)
        dtext(p, cx + 80, 160, "4² = 16", C_YELLOW, 14, width=140); dtext(p, cx, 190, "29 | 16 → 2916", C_GREEN, 16)

class Sq50MapDiagram(Diagram):
    H = 180
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 16, "The front part: shift the 'distance from 50' onto 25", C_DIM, 12, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 200, 60), QPointF(cx + 200, 60))
        p.drawLine(QPointF(cx - 80, 52), QPointF(cx - 80, 68)); dtext(p, cx - 80, 42, "25", C_DIM, 12, width=50)
        dot(p, cx + 40, 60, C_ACCENT); dtext(p, cx + 40, 42, "29", C_ACCENT, 13, width=50)
        p.drawLine(QPointF(cx - 200, 125), QPointF(cx + 200, 125))
        p.drawLine(QPointF(cx - 80, 117), QPointF(cx - 80, 133)); dtext(p, cx - 80, 150, "50", C_GREEN, 12, width=50)
        dot(p, cx + 40, 125, C_TEXT); dtext(p, cx + 40, 150, "54", C_TEXT, 13, width=50)
        arrow(p, cx + 40, 112, cx + 40, 74, C_YELLOW); dtext(p, cx + 108, 93, "25 + d", C_YELLOW, 13, width=120)
        curve_arrow(p, cx - 80, 133, cx + 40, 133, -18, C_YELLOW); dtext(p, cx - 20, 166, "d = 4", C_YELLOW, 12, width=80)

class Times99Diagram(Diagram):
    H = 170
    def draw(self, p, w, h):
        cx = w / 2; x0, x1, cut = cx - 200, cx + 200, cx + 140
        dtext(p, cx, 22, "45 × 99 — times 100 minus times 1", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, 50, cut - x0 - 4, 50), 10, 10)
        dtext(p, (x0 + cut) / 2, 75, "45 × 100 = 4500", C_ACCENT_TEXT, 15, width=280)
        p.setBrush(QColor(C_RED_SOFT)); p.setPen(QPen(QColor(C_RED), 1.8)); p.drawRoundedRect(QRectF(cut, 50, x1 - cut, 50), 10, 10)
        dtext(p, (cut + x1) / 2, 75, "− 45", C_RED, 15, width=90)
        dtext(p, cx, 135, "4500 − 45 = 4455", C_GREEN, 18)

class Times99LineDiagram(Diagram):
    H = 180
    def draw(self, p, w, h):
        cx = w / 2; y = 100
        dtext(p, cx, 16, "45 × 99: jump to 4500, step back 45", C_DIM, 12, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        dot(p, cx - 210, y, C_TEXT); dtext(p, cx - 210, y + 26, "0", C_DIM, 12, width=40)
        curve_arrow(p, cx - 210, y - 12, cx + 150, y - 12, 40, C_ACCENT)
        dtext(p, cx - 30, 70, "× 100 → 4500", C_ACCENT, 13, width=180)
        dot(p, cx + 150, y, C_ACCENT); dtext(p, cx + 152, y + 26, "4500", C_ACCENT, 12, width=70)
        curve_arrow(p, cx + 150, y - 10, cx + 105, y - 10, 22, C_RED)
        dtext(p, cx + 128, y - 44, "− 45", C_RED, 13, width=70)
        dot(p, cx + 105, y, C_GREEN); dtext(p, cx + 100, y + 46, "4455", C_GREEN, 13, width=70)
        dtext(p, cx - 40, 164, "landing point = 45 × 99", C_GREEN, 14, width=340)

class Div5Diagram(Diagram):
    H = 150
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "85 ÷ 5 — double it, then divide by 10", C_DIM, 13, True, w)
        rbox(p, cx - 180, 82, 80, 52, "85", size=19); arrow(p, cx - 135, 82, cx - 85, 82); dtext(p, cx - 110, 56, "× 2", C_YELLOW, 13, width=60)
        rbox(p, cx - 35, 82, 80, 52, "170", size=19); arrow(p, cx + 10, 82, cx + 60, 82); dtext(p, cx + 35, 56, "÷ 10", C_YELLOW, 13, width=60)
        rbox(p, cx + 115, 82, 80, 52, "17", fill=C_ACCENT_SOFT, border=C_ACCENT, size=19)

class Times15Diagram(Diagram):
    H = 180
    def draw(self, p, w, h):
        cx = w / 2; x0 = cx - 180
        dtext(p, cx, 22, "24 × 15 — times 10 plus half of that", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, 50, 240, 46), 8, 8)
        dtext(p, x0 + 120, 73, "24 × 10 = 240", C_ACCENT_TEXT, 15, width=220)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0 + 244, 50, 120, 46), 8, 8)
        dtext(p, x0 + 304, 73, "half = 120", C_YELLOW, 14, width=120)
        arrow(p, cx, 105, cx, 125, C_GREEN); dtext(p, cx, 150, "240 + 120 = 360", C_GREEN, 18)

class Times15ClockDiagram(Diagram):
    H = 205
    def draw(self, p, w, h):
        cx = w / 2; ox, oy, r = cx - 150, 108, 56
        dtext(p, cx, 16, "15 minutes = a quarter of the clock", C_DIM, 12, True, w)
        p.setBrush(QColor(C_PANEL)); p.setPen(QPen(QColor(C_BOX_BORDER), 2)); p.drawEllipse(QPointF(ox, oy), r, r)
        p.setPen(QPen(QColor(C_ACCENT), 3)); p.drawLine(QPointF(ox, oy), QPointF(ox + r - 12, oy))
        dot(p, ox, oy, C_ACCENT, 5)
        dtext(p, ox, oy - r - 12, "0", C_DIM, 11, width=40); dtext(p, ox + r + 16, oy, "15", C_YELLOW, 11, width=40)
        dtext(p, ox, oy + r + 12, "30", C_DIM, 11, width=40); dtext(p, ox - r - 16, oy, "45", C_DIM, 11, width=40)
        dtext(p, cx + 120, 66, "24 × 15 minutes", C_TEXT, 15, width=240)
        dtext(p, cx + 120, 98, "= 24 quarter-hours", C_DIM, 13, width=240)
        dtext(p, cx + 120, 128, "= 6 hours", C_TEXT, 14, width=240)
        dtext(p, cx + 120, 160, "= 360 minutes", C_GREEN, 17, width=240)

class Mul101Diagram(Diagram):
    H = 150
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "47 × 101 — the number writes itself twice", C_DIM, 13, True, w)
        rbox(p, cx - 150, 78, 46, 48, "4", size=18); rbox(p, cx - 100, 78, 46, 48, "7", size=18)
        arrow(p, cx - 66, 78, cx + 2, 78, C_YELLOW); dtext(p, cx - 32, 52, "copy", C_YELLOW, 12, width=70)
        rbox(p, cx + 30, 78, 46, 48, "4", size=18); rbox(p, cx + 80, 78, 46, 48, "7", size=18)
        rbox(p, cx + 130, 78, 46, 48, "4", fill=C_ACCENT_SOFT, border=C_ACCENT, size=18)
        rbox(p, cx + 180, 78, 46, 48, "7", fill=C_ACCENT_SOFT, border=C_ACCENT, size=18)
        dtext(p, cx + 105, 132, "= 4747", C_GREEN, 17, width=140)

class Mul101ColumnsDiagram(Diagram):
    H = 205
    def draw(self, p, w, h):
        cx = w / 2; xs = [cx - 69, cx - 23, cx + 23, cx + 69]
        dtext(p, cx, 16, "4700 + 47, written in columns", C_DIM, 12, True, w)
        for x, dch in zip(xs, "4700"): rbox(p, x, 50, 40, 36, dch, size=16)
        dtext(p, cx - 115, 96, "+", C_YELLOW, 18, width=30)
        rbox(p, xs[2], 96, 40, 36, "4", size=16); rbox(p, xs[3], 96, 40, 36, "7", size=16)
        p.setPen(QPen(QColor(C_BOX_BORDER), 2)); p.drawLine(QPointF(cx - 100, 122), QPointF(cx + 100, 122))
        for x, dch, hot in zip(xs, "4747", [False, False, True, True]):
            rbox(p, x, 146, 40, 36, dch, fill=C_ACCENT_SOFT if hot else C_BOX, border=C_ACCENT if hot else C_BOX_BORDER, size=16)
        dtext(p, cx, 192, "the 47 reappears in the last two places", C_GREEN, 13, True, w)

class Times125Diagram(Diagram):
    H = 200
    def draw(self, p, w, h):
        cx = w / 2; x0, y0, W, Hh = cx - 250, 45, 300, 70
        dtext(p, cx, 20, "1000 = 8 × 125 — so divide by 8 first", C_DIM, 13, True, w)
        p.setBrush(QColor(C_PANEL)); p.setPen(QPen(QColor(C_PANEL_BORDER), 1.6)); p.drawRoundedRect(QRectF(x0, y0, W, Hh), 8, 8)
        sw = W / 8
        for i in range(1, 8):
            p.setPen(QPen(QColor(C_BOX_BORDER), 1.2)); p.drawLine(QPointF(x0 + i * sw, y0), QPointF(x0 + i * sw, y0 + Hh))
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0 + 2, y0 + 2, sw - 3, Hh - 4), 5, 5)
        dtext(p, x0 + sw / 2, y0 + Hh / 2, "125", C_ACCENT_TEXT, 11, width=50)
        dtext(p, x0 + W / 2, y0 + Hh + 22, "eight of these make 1000", C_DIM, 12, width=320)
        rx = cx + 150
        rbox(p, rx, 60, 150, 42, "32 ÷ 8 = 4", size=15); arrow(p, rx, 84, rx, 102)
        rbox(p, rx, 124, 170, 42, "4 × 1000 = 4000", fill=C_ACCENT_SOFT, border=C_ACCENT, size=15)

class Div25Diagram(Diagram):
    H = 150
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "225 ÷ 25 — double, double, then ÷ 100", C_DIM, 13, True, w)
        rbox(p, cx - 210, 82, 84, 52, "225", size=18); arrow(p, cx - 163, 82, cx - 117, 82); dtext(p, cx - 140, 56, "× 2", C_YELLOW, 12, width=60)
        rbox(p, cx - 70, 82, 84, 52, "450", size=18); arrow(p, cx - 23, 82, cx + 23, 82); dtext(p, cx, 56, "× 2", C_YELLOW, 12, width=60)
        rbox(p, cx + 70, 82, 84, 52, "900", size=18); arrow(p, cx + 117, 82, cx + 163, 82); dtext(p, cx + 140, 56, "÷ 100", C_YELLOW, 12, width=70)
        rbox(p, cx + 210, 82, 70, 52, "9", fill=C_ACCENT_SOFT, border=C_ACCENT, size=19)

class Div25QuartersDiagram(Diagram):
    H = 170
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 18, "225¢ as a pile of quarters", C_DIM, 13, True, w)
        for i in range(9): bubble(p, cx - 200 + i * 48, 68, 20, "25", fill=C_YELLOW_SOFT, border=C_YELLOW, fg=C_YELLOW, size=10)
        dtext(p, cx, 130, "nine coins  →  225 ÷ 25 = 9", C_GREEN, 16, width=360)

class RoundAddDiagram(Diagram):
    H = 200
    def draw(self, p, w, h):
        cx = w / 2; y = 95
        dtext(p, cx, 20, "456 + 298 — round up, then give back", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        dot(p, cx - 180, y, C_TEXT); dtext(p, cx - 180, y + 26, "456", C_TEXT, 13, width=70)
        curve_arrow(p, cx - 180, y - 12, cx + 140, y - 12, 46, C_GREEN)
        dtext(p, cx - 20, y - 70, "+ 300", C_GREEN, 14, width=100)
        dot(p, cx + 140, y, C_GREEN); dtext(p, cx + 140, y + 26, "756", C_GREEN, 13, width=60)
        curve_arrow(p, cx + 140, y - 10, cx + 108, y - 10, 22, C_RED)
        dtext(p, cx + 152, y - 40, "− 2", C_RED, 13, width=60)
        dot(p, cx + 108, y, C_YELLOW); dtext(p, cx + 108, y + 48, "754", C_YELLOW, 13, width=60)
        dtext(p, cx - 40, 176, "456 + 300 − 2 = 754", C_GREEN, 17, width=340)

class RoundAddNotchDiagram(Diagram):
    H = 170
    def draw(self, p, w, h):
        cx = w / 2; x0, x1, cut = cx - 220, cx + 220, cx + 150
        dtext(p, cx, 22, "456 + 298 as a bar: 456 + 300, notch off 2", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, 50, cut - x0 - 4, 46), 10, 10)
        dtext(p, (x0 + cut) / 2, 73, "456 + 300 = 756", C_ACCENT_TEXT, 15, width=300)
        p.setBrush(QColor(C_RED_SOFT)); p.setPen(QPen(QColor(C_RED), 1.8)); p.drawRoundedRect(QRectF(cut, 50, x1 - cut, 46), 10, 10)
        dtext(p, (cut + x1) / 2, 73, "− 2", C_RED, 14, width=80)
        dtext(p, (x0 + cut) / 2, 132, "756 − 2 = 754", C_GREEN, 17, width=300)

class CountUpDiagram(Diagram):
    H = 190
    def draw(self, p, w, h):
        cx = w / 2; y = 100
        dtext(p, cx, 20, "100 − 37 — count up like a shopkeeper", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        dot(p, cx - 160, y, C_TEXT); dtext(p, cx - 160, y + 26, "37", C_TEXT, 13, width=50)
        dot(p, cx - 110, y, C_YELLOW); dtext(p, cx - 110, y + 26, "40", C_YELLOW, 13, width=50)
        dot(p, cx + 160, y, C_GREEN); dtext(p, cx + 160, y + 26, "100", C_GREEN, 13, width=60)
        curve_arrow(p, cx - 160, y - 12, cx - 110, y - 12, 26, C_YELLOW); dtext(p, cx - 135, y - 48, "+3", C_YELLOW, 13, width=60)
        curve_arrow(p, cx - 110, y - 12, cx + 160, y - 12, 46, C_GREEN); dtext(p, cx + 25, y - 66, "+60", C_GREEN, 14, width=80)
        dtext(p, cx, 168, "3 + 60 = 63 → 100 − 37 = 63", C_GREEN, 17, width=380)

class CountUpLadderDiagram(Diagram):
    H = 240
    def draw(self, p, w, h):
        cx = w / 2; lx = cx - 120
        dtext(p, cx, 14, "100 − 37 as a ladder of easy hops", C_DIM, 12, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(lx, 30), QPointF(lx, 200))
        rungs = [(30, "100", C_GREEN), (70, "80", C_YELLOW), (110, "60", C_YELLOW), (150, "40", C_YELLOW), (190, "37", C_TEXT)]
        for y, lab, col in rungs:
            p.setPen(QPen(QColor(col), 2.4)); p.drawLine(QPointF(lx - 22, y), QPointF(lx + 22, y))
            dtext(p, lx - 55, y, lab, col, 13, width=60)
        for y1, y2, lab in [(190, 150, "+3"), (150, 110, "+20"), (110, 70, "+20"), (70, 30, "+20")]:
            arrow(p, lx + 60, y1 - 5, lx + 60, y2 + 5, C_GREEN)
            dtext(p, lx + 105, (y1 + y2) / 2, lab, C_GREEN, 12, width=60)
        dtext(p, cx + 40, 222, "3 + 20 + 20 + 20 = 63", C_GREEN, 16, width=340)

class SplitMulDiagram(Diagram):
    H = 210
    def draw(self, p, w, h):
        cx = w / 2; x0, y0, hgt, w1, w2 = cx - 240, 50, 90, 260, 110
        dtext(p, cx, 20, "23 × 45 — split 45 into 40 + 5 (area model)", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, y0, w1, hgt), 8, 8)
        dtext(p, x0 + w1 / 2, y0 + hgt / 2 - 12, "23 × 40", "#ffffff", 16, width=200)
        dtext(p, x0 + w1 / 2, y0 + hgt / 2 + 12, "= 920", C_ACCENT_TEXT, 13, width=200)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8)); p.drawRoundedRect(QRectF(x0 + w1 + 6, y0, w2, hgt), 8, 8)
        dtext(p, x0 + w1 + 6 + w2 / 2, y0 + hgt / 2 - 12, "23 × 5", C_YELLOW, 15, width=120)
        dtext(p, x0 + w1 + 6 + w2 / 2, y0 + hgt / 2 + 12, "= 115", C_YELLOW, 13, width=120)
        dtext(p, x0 + w1 / 2, y0 - 14, "40", C_DIM, 12, width=60); dtext(p, x0 + w1 + 6 + w2 / 2, y0 - 14, "5", C_DIM, 12, width=40)
        dtext(p, x0 - 22, y0 + hgt / 2, "23", C_DIM, 12, width=50)
        arrow(p, cx - 20, 150, cx - 20, 168, C_GREEN)
        dtext(p, cx - 20, 190, "920 + 115 = 1035", C_GREEN, 17, width=340)

class Times4Diagram(Diagram):
    H = 150
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "36 × 4 — double, then double again", C_DIM, 13, True, w)
        rbox(p, cx - 175, 82, 80, 52, "36", size=19); arrow(p, cx - 130, 82, cx - 84, 82); dtext(p, cx - 107, 56, "× 2", C_YELLOW, 13, width=60)
        rbox(p, cx - 38, 82, 80, 52, "72", size=19); arrow(p, cx + 7, 82, cx + 53, 82); dtext(p, cx + 30, 56, "× 2", C_YELLOW, 13, width=60)
        rbox(p, cx + 105, 82, 92, 52, "144", fill=C_ACCENT_SOFT, border=C_ACCENT, size=19)
        dtext(p, cx + 215, 82, "= 36 × 4 ✔", C_GREEN, 13, width=150)

class Times4CopiesDiagram(Diagram):
    H = 150
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "× 4 is just four copies added", C_DIM, 13, True, w)
        for x in [cx - 205, cx - 95, cx + 15]:
            rbox(p, x, 82, 70, 50, "36", size=17)
            dtext(p, x + 55, 82, "+", C_DIM, 16, width=30)
        dtext(p, cx + 85, 82, "=", C_DIM, 18, width=30)
        rbox(p, cx + 150, 82, 90, 50, "144", fill=C_ACCENT_SOFT, border=C_ACCENT, size=18)

class Div4Diagram(Diagram):
    H = 150
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "132 ÷ 4 — halve, then halve again", C_DIM, 13, True, w)
        rbox(p, cx - 175, 82, 80, 52, "132", size=19); arrow(p, cx - 130, 82, cx - 84, 82); dtext(p, cx - 107, 56, "÷ 2", C_YELLOW, 13, width=60)
        rbox(p, cx - 38, 82, 80, 52, "66", size=19); arrow(p, cx + 7, 82, cx + 53, 82); dtext(p, cx + 30, 56, "÷ 2", C_YELLOW, 13, width=60)
        rbox(p, cx + 105, 82, 92, 52, "33", fill=C_ACCENT_SOFT, border=C_ACCENT, size=19)
        dtext(p, cx + 215, 82, "= 132 ÷ 4 ✔", C_GREEN, 13, width=150)

class Div4PizzaDiagram(Diagram):
    H = 190
    def draw(self, p, w, h):
        cx = w / 2; ox, oy, r = cx - 160, 100, 58
        dtext(p, cx, 16, "Dividing by 4 = taking one quarter", C_DIM, 12, True, w)
        p.setBrush(QColor(C_PANEL)); p.setPen(QPen(QColor(C_PANEL_BORDER), 1.6)); p.drawEllipse(QPointF(ox, oy), r, r)
        p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.8))
        p.drawPie(QRectF(ox - r, oy - r, 2 * r, 2 * r), 0, 90 * 16)
        p.setPen(QPen(QColor(C_BOX_BORDER), 1.6))
        p.drawLine(QPointF(ox - r, oy), QPointF(ox + r, oy)); p.drawLine(QPointF(ox, oy - r), QPointF(ox, oy + r))
        dtext(p, cx + 120, 70, "Share 132 into 4 equal slices", C_TEXT, 14, width=300)
        dtext(p, cx + 120, 106, "each gets 33", C_GREEN, 18, width=300)
        dtext(p, cx + 120, 138, "132 ÷ 4 = 33", C_DIM, 13, width=300)

class Times19Diagram(Diagram):
    H = 175
    def draw(self, p, w, h):
        cx = w / 2; x0, x1, cut = cx - 220, cx + 220, cx + 128
        dtext(p, cx, 22, "27 × 19 = 27 × 20 − 27", C_DIM, 13, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0, 50, cut - x0 - 4, 46), 10, 10)
        p.setBrush(QColor(C_RED_SOFT)); p.setPen(QPen(QColor(C_RED), 1.8)); p.drawRoundedRect(QRectF(cut, 50, x1 - cut, 46), 10, 10)
        dtext(p, (x0 + cut) / 2, 73, "27 × 20 = 540", C_ACCENT_TEXT, 15, width=280)
        dtext(p, (cut + x1) / 2, 73, "− 27", C_RED, 14, width=90)
        dtext(p, (x0 + cut) / 2, 132, "take one 27 away  →  513", C_GREEN, 17, width=340)

class Times19LineDiagram(Diagram):
    H = 180
    def draw(self, p, w, h):
        cx = w / 2; y = 100
        dtext(p, cx, 16, "27 × 19: jump to 540, step back 27", C_DIM, 12, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        dot(p, cx - 210, y, C_TEXT); dtext(p, cx - 210, y + 26, "0", C_DIM, 12, width=40)
        curve_arrow(p, cx - 210, y - 12, cx + 150, y - 12, 40, C_ACCENT)
        dtext(p, cx - 30, 70, "× 20 → 540", C_ACCENT, 13, width=180)
        dot(p, cx + 150, y, C_ACCENT); dtext(p, cx + 152, y + 26, "540", C_ACCENT, 12, width=70)
        curve_arrow(p, cx + 150, y - 10, cx + 105, y - 10, 22, C_RED)
        dtext(p, cx + 128, y - 44, "− 27", C_RED, 13, width=70)
        dot(p, cx + 105, y, C_GREEN); dtext(p, cx + 100, y + 46, "513", C_GREEN, 13, width=70)
        dtext(p, cx - 40, 164, "landing point = 27 × 19", C_GREEN, 14, width=340)

class Times75Diagram(Diagram):
    H = 205
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 16, "75 = three quarters of 100", C_DIM, 12, True, w)
        for i in range(4):
            hot = i < 3
            bubble(p, cx - 210 + i * 52, 60, 22, "25", fill=C_YELLOW_SOFT if hot else C_PANEL, border=C_YELLOW if hot else C_BOX_BORDER, fg=C_YELLOW if hot else C_DIM, size=12)
        dtext(p, cx + 20, 60, "= 100", C_GREEN, 15, width=100)
        rbox(p, cx - 150, 125, 150, 42, "36 ÷ 4 = 9", size=15); arrow(p, cx - 70, 125, cx - 50, 125)
        rbox(p, cx + 10, 125, 150, 42, "9 × 3 = 27", fill=C_YELLOW_SOFT, border=C_YELLOW, fg=C_YELLOW, size=15); arrow(p, cx + 90, 125, cx + 110, 125)
        rbox(p, cx + 185, 125, 140, 42, "×100 = 2700", fill=C_ACCENT_SOFT, border=C_ACCENT, size=15)
        dtext(p, cx, 186, "÷ 4, × 3, × 100", C_DIM, 13, True, w)

class SubCompDiagram(Diagram):
    H = 215
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 16, "83 − 47 — slide both numbers, the gap survives", C_DIM, 12, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 220, 70), QPointF(cx + 220, 70))
        dot(p, cx - 120, 70, C_YELLOW); dot(p, cx + 140, 70, C_YELLOW)
        dtext(p, cx - 120, 48, "50", C_YELLOW, 13, width=50); dtext(p, cx + 140, 48, "86", C_YELLOW, 13, width=50)
        curve_arrow(p, cx - 120, 58, cx + 140, 58, 26, C_GREEN); dtext(p, cx + 10, 34, "36", C_GREEN, 14, width=60)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 220, 150), QPointF(cx + 220, 150))
        dot(p, cx - 120, 150, C_TEXT); dot(p, cx + 140, 150, C_TEXT)
        dtext(p, cx - 120, 172, "47", C_TEXT, 13, width=50); dtext(p, cx + 140, 172, "83", C_TEXT, 13, width=50)
        curve_arrow(p, cx - 120, 138, cx + 140, 138, 26, C_GREEN); dtext(p, cx + 10, 118, "36", C_GREEN, 14, width=60)
        p.setPen(QPen(QColor(C_YELLOW), 1.8, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(cx - 120, 130), QPointF(cx - 120, 82)); p.drawLine(QPointF(cx + 140, 130), QPointF(cx + 140, 82))
        dtext(p, cx - 152, 106, "+3", C_YELLOW, 13, width=50); dtext(p, cx + 172, 106, "+3", C_YELLOW, 13, width=50)
        dtext(p, cx, 198, "86 − 50 = 36, and so is 83 − 47", C_GREEN, 15, width=400)

class Pct10Diagram(Diagram):
    H = 200
    def draw(self, p, w, h):
        cx = w / 2; x0, y0, cw, ch, gap = cx - 218, 58, 40, 44, 4
        dtext(p, cx, 16, "35% of 80 — three 10%-blocks and one half-block", C_DIM, 12, True, w)
        for i in range(10):
            x = x0 + i * (cw + gap)
            if i < 3: p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.6))
            else: p.setBrush(QColor(C_PANEL)); p.setPen(QPen(QColor(C_PANEL_BORDER), 1.6))
            p.drawRoundedRect(QRectF(x, y0, cw, ch), 6, 6)
            if i == 3:
                p.setBrush(QColor(C_YELLOW_SOFT)); p.setPen(QPen(QColor(C_YELLOW), 1.6))
                p.drawRoundedRect(QRectF(x, y0, cw / 2, ch), 6, 6)
        dtext(p, cx, 130, "10% of 80 = 8 per block • the shaded half-block is 5%", C_DIM, 12, True, w)
        dtext(p, cx, 168, "3 × 8 + 4 = 28", C_GREEN, 18, width=300)

class Pct10GridDiagram(Diagram):
    H = 215
    def draw(self, p, w, h):
        cx = w / 2; x0, y0, cs, gap = cx - 235, 38, 15, 2
        dtext(p, cx, 16, "35 of 100 squares shaded = 35%", C_DIM, 12, True, w)
        n = 0
        for row in range(10):
            for col in range(10):
                hot = n < 35
                p.setBrush(QColor(C_ACCENT_SOFT if hot else C_PANEL)); p.setPen(QPen(QColor(C_ACCENT if hot else C_PANEL_BORDER), 1.0))
                p.drawRoundedRect(QRectF(x0 + col * (cs + gap), y0 + row * (cs + gap), cs, cs), 3, 3)
                n += 1
        dtext(p, cx + 120, 80, "35 cells of 100", C_ACCENT_TEXT, 14, width=220)
        dtext(p, cx + 120, 112, "= 35%", C_ACCENT, 16, width=220)
        dtext(p, cx + 120, 148, "of 80 → 28", C_GREEN, 16, width=220)

class Times8Diagram(Diagram):
    H = 150
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "23 × 8 — double, double, double", C_DIM, 13, True, w)
        rbox(p, cx - 210, 82, 84, 52, "23", size=18); arrow(p, cx - 163, 82, cx - 117, 82); dtext(p, cx - 140, 56, "× 2", C_YELLOW, 12, width=60)
        rbox(p, cx - 70, 82, 84, 52, "46", size=18); arrow(p, cx - 23, 82, cx + 23, 82); dtext(p, cx, 56, "× 2", C_YELLOW, 12, width=60)
        rbox(p, cx + 70, 82, 84, 52, "92", size=18); arrow(p, cx + 117, 82, cx + 163, 82); dtext(p, cx + 140, 56, "× 2", C_YELLOW, 12, width=60)
        rbox(p, cx + 210, 82, 84, 52, "184", fill=C_ACCENT_SOFT, border=C_ACCENT, size=18)

class Times8CubeDiagram(Diagram):
    H = 175
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 18, "8 = 2 × 2 × 2 — three doubling steps", C_DIM, 12, True, w)
        for r in range(2):
            for c in range(4):
                hot = (r == 0 and c == 0)
                p.setBrush(QColor(C_ACCENT_SOFT if hot else C_PANEL)); p.setPen(QPen(QColor(C_ACCENT if hot else C_PANEL_BORDER), 1.6))
                p.drawRoundedRect(QRectF(cx - 228 + c * 44, 48 + r * 42, 36, 36), 6, 6)
        dtext(p, cx + 120, 66, "double three times", C_TEXT, 14, width=240)
        dtext(p, cx + 120, 100, "= multiply by 8", C_GREEN, 16, width=240)
        dtext(p, cx - 60, 150, "23 → 46 → 92 → 184", C_DIM, 13, True, w)

class Div8Diagram(Diagram):
    H = 150
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 22, "184 ÷ 8 — halve, halve, halve", C_DIM, 13, True, w)
        rbox(p, cx - 210, 82, 84, 52, "184", size=18); arrow(p, cx - 163, 82, cx - 117, 82); dtext(p, cx - 140, 56, "÷ 2", C_YELLOW, 12, width=60)
        rbox(p, cx - 70, 82, 84, 52, "92", size=18); arrow(p, cx - 23, 82, cx + 23, 82); dtext(p, cx, 56, "÷ 2", C_YELLOW, 12, width=60)
        rbox(p, cx + 70, 82, 84, 52, "46", size=18); arrow(p, cx + 117, 82, cx + 163, 82); dtext(p, cx + 140, 56, "÷ 2", C_YELLOW, 12, width=60)
        rbox(p, cx + 210, 82, 84, 52, "23", fill=C_ACCENT_SOFT, border=C_ACCENT, size=18)

class Diff2Diagram(Diagram):
    H = 195
    def draw(self, p, w, h):
        cx = w / 2; sx, sy, side = cx - 200, 42, 120
        dtext(p, cx, 18, "24 × 26 — the square minus its corner", C_DIM, 12, True, w)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(sx, sy, side, side), 8, 8)
        dtext(p, sx + side / 2, sy + side / 2, "25² = 625", C_ACCENT_TEXT, 14, width=140)
        p.setBrush(QColor(C_RED_SOFT)); p.setPen(QPen(QColor(C_RED), 1.8)); p.drawRoundedRect(QRectF(sx + side - 18, sy + side - 18, 18, 18), 4, 4)
        dtext(p, sx + side + 16, sy + side - 10, "−1", C_RED, 13, width=50)
        dtext(p, cx + 110, 70, "24 × 26", C_TEXT, 16, width=200)
        dtext(p, cx + 110, 102, "= 625 − 1", C_DIM, 14, width=200)
        dtext(p, cx + 110, 134, "= 624", C_GREEN, 18, width=200)
        dtext(p, cx, 180, "a pair two apart = middle² − 1", C_DIM, 12, True, w)

class MidSqDiagram(Diagram):
    H = 185
    def draw(self, p, w, h):
        cx = w / 2; y = 105
        dtext(p, cx, 20, "23 × 27 — square the middle, subtract d²", C_DIM, 13, True, w)
        p.setPen(QPen(QColor(C_DIM), 2)); p.drawLine(QPointF(cx - 240, y), QPointF(cx + 240, y))
        for x, lab, col in ((cx - 160, "23", C_ACCENT), (cx, "25", C_GREEN), (cx + 160, "27", C_ACCENT)):
            dot(p, x, y, col); dtext(p, x, y + 26, lab, col, 13, width=60)
        curve_arrow(p, cx - 160, y - 12, cx, y - 12, 24, C_YELLOW); dtext(p, cx - 80, y - 46, "d = 2", C_YELLOW, 12, width=80)
        curve_arrow(p, cx, y - 12, cx + 160, y - 12, 24, C_YELLOW); dtext(p, cx + 80, y - 46, "d = 2", C_YELLOW, 12, width=80)
        dtext(p, cx, 166, "25² − 2² = 625 − 4 = 621", C_GREEN, 17, width=380)

class BflyDiagram(Diagram):
    H = 220
    def draw(self, p, w, h):
        cx = w / 2
        dtext(p, cx, 14, "1/3 + 1/4 — the butterfly crosses", C_DIM, 12, True, w)
        rbox(p, cx - 160, 48, 56, 34, "1", size=16); rbox(p, cx - 160, 90, 56, 34, "3", size=16)
        rbox(p, cx + 160, 48, 56, 34, "1", size=16); rbox(p, cx + 160, 90, 56, 34, "4", size=16)
        curve_arrow(p, cx - 130, 52, cx + 130, 86, 30, C_YELLOW)
        curve_arrow(p, cx - 130, 94, cx + 130, 52, -30, C_YELLOW)
        dtext(p, cx, 34, "1 × 4 = 4", C_YELLOW, 13, width=120)
        dtext(p, cx, 122, "1 × 3 = 3", C_YELLOW, 13, width=120)
        rbox(p, cx, 158, 140, 34, "4 + 3 = 7", fill=C_ACCENT_SOFT, border=C_ACCENT, size=15)
        rbox(p, cx, 198, 140, 34, "3 × 4 = 12", fill=C_YELLOW_SOFT, border=C_YELLOW, fg=C_YELLOW, size=15)
        dtext(p, cx + 175, 178, "= 7/12", C_GREEN, 18, width=140)

class Pct1Diagram(Diagram):
    H = 180
    def draw(self, p, w, h):
        cx = w / 2; x0, y0, W, Hh = cx - 230, 55, 360, 44
        dtext(p, cx, 20, "17% of 300 — slice off 1% first", C_DIM, 13, True, w)
        p.setBrush(QColor(C_PANEL)); p.setPen(QPen(QColor(C_PANEL_BORDER), 1.6)); p.drawRoundedRect(QRectF(x0, y0, W, Hh), 8, 8)
        dtext(p, x0 + W / 2 + 20, y0 + Hh / 2, "300", C_DIM, 14, width=280)
        p.setBrush(QColor(C_ACCENT_SOFT)); p.setPen(QPen(QColor(C_ACCENT), 1.8)); p.drawRoundedRect(QRectF(x0 + 2, y0 + 2, 44, Hh - 4), 6, 6)
        dtext(p, x0 + 24, y0 + Hh + 22, "1% = 3", C_ACCENT, 13, width=110)
        dtext(p, cx + 40, 150, "17 × 3 = 51", C_GREEN, 18, width=300)

DIAGRAMS: Dict[str, List[Type[Diagram]]] = {
    "mul11": [Mul11Diagram, Mul11BarsDiagram],
    "sq5": [Sq5Diagram, Sq5TilesDiagram],
    "t9": [Times9Diagram, Times9LineDiagram],
    "t5": [Times5Diagram, Times5HalfBarDiagram, Div5PartsDiagram],
    "t25": [Times25Diagram, Times25CoinsDiagram],
    "pct": [PercentDiagram, PercentScaleDiagram],
    "dbh": [DoubleHalfDiagram, DoubleHalfAreaDiagram],
    "n100": [Near100Diagram, Near100BarsDiagram],
    "rsq": [RoundSquareDiagram, RoundSqLineDiagram],
    "st10": [SameTensDiagram, SameTensMidDiagram],
    "s1000": [Sub1000Diagram, Sub1000LineDiagram],
    "div": [DivisibilityDiagram, DivModBarsDiagram],
    "mul12": [Mul12Diagram, Mul12SplitDiagram],
    "teens": [TeensDiagram, TeensTilesDiagram],
    "sq50": [Sq50Diagram, Sq50MapDiagram],
    "t99": [Times99Diagram, Times99LineDiagram],
    "d5": [Div5Diagram],
    "t15": [Times15Diagram, Times15ClockDiagram],
    "mul101": [Mul101Diagram, Mul101ColumnsDiagram],
    "t125": [Times125Diagram],
    "d25": [Div25Diagram, Div25QuartersDiagram],
    "addrnd": [RoundAddDiagram, RoundAddNotchDiagram],
    "countup": [CountUpDiagram, CountUpLadderDiagram],
    "splitmul": [SplitMulDiagram],
    "t4": [Times4Diagram, Times4CopiesDiagram],
    "d4": [Div4Diagram, Div4PizzaDiagram],
    "t19": [Times19Diagram, Times19LineDiagram],
    "t75": [Times75Diagram],
    "subcomp": [SubCompDiagram],
    "pct10": [Pct10Diagram, Pct10GridDiagram],
    "t8": [Times8Diagram, Times8CubeDiagram],
    "d8": [Div8Diagram],
    "diff2": [Diff2Diagram],
    "midsq": [MidSqDiagram],
    "bfly": [BflyDiagram],
    "pct1": [Pct1Diagram],
}

# --------------------------------------------------------------------------- #
#  Reusable widgets
# --------------------------------------------------------------------------- #
class AnswerBox(QWidget):
    submitted = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); self.stack = QStackedWidget()
        self.edit = QLineEdit(); self.edit.setPlaceholderText("Your answer…  (Enter to check)"); self.edit.setAlignment(Qt.AlignmentFlag.AlignCenter); self.edit.setMaxLength(12)
        pal = self.edit.palette(); pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#5b6275")); self.edit.setPalette(pal)
        self.edit.returnPressed.connect(lambda: self.submitted.emit(self.edit.text())); self.stack.addWidget(self.edit)
        self.choice_host = QWidget(); self.choice_lay = QHBoxLayout(self.choice_host); self.choice_lay.setContentsMargins(0, 0, 0, 0); self.stack.addWidget(self.choice_host)
        lay.addWidget(self.stack); self._choice_btns: List[QPushButton] = []
    def load(self, p: Problem):
        set_edit_state(self.edit, ""); self.edit.clear(); self.edit.setEnabled(True)
        for b in self._choice_btns: b.deleteLater()
        self._choice_btns.clear()
        if p.choices:
            for c in p.choices:
                btn = QPushButton(c); btn.setObjectName("choiceBtn"); btn.clicked.connect(lambda _=False, txt=c: self.submitted.emit(txt))
                self.choice_lay.addWidget(btn); self._choice_btns.append(btn)
            self.stack.setCurrentWidget(self.choice_host)
        else: self.stack.setCurrentWidget(self.edit)
    def text(self) -> str: return self.edit.text()
    def mark(self, ok: bool): set_edit_state(self.edit, "ok" if ok else "bad")
    def set_enabled(self, enabled: bool):
        self.edit.setEnabled(enabled)
        for b in self._choice_btns: b.setEnabled(enabled)
    def focus(self):
        if self.stack.currentWidget() is self.edit: self.edit.setFocus(); self.edit.selectAll()
        elif self._choice_btns: self._choice_btns[0].setFocus()

class Card(QFrame):
    def __init__(self, title: Optional[str] = None, body_html: str = ""):
        super().__init__(); self.setObjectName("card"); self._lay = QVBoxLayout(self); self._lay.setContentsMargins(18, 14, 18, 16); self._lay.setSpacing(8)
        if title: t = QLabel(title); t.setObjectName("cardTitle"); self._lay.addWidget(t)
        if body_html: b = QLabel(body_html); b.setTextFormat(Qt.TextFormat.RichText); b.setWordWrap(True); self._lay.addWidget(b)
    def add(self, w: QWidget): self._lay.addWidget(w)
    def add_layout(self, l): self._lay.addLayout(l)

class PracticeCard(QFrame):
    def __init__(self, trick: Trick, store: ProgressStore):
        super().__init__(); self.setObjectName("card"); self.trick, self.store = trick, store
        self.problem: Optional[Problem] = None; self.revealed = 0; self.solved = False
        self.streak = 0; self.session_att = 0; self.session_ok = 0
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 16, 20, 18); lay.setSpacing(10)
        head = QHBoxLayout()
        t = QLabel("🎯 PRACTICE"); t.setObjectName("cardTitle")
        self.diff_combo = QComboBox(); self.diff_combo.addItems(DIFF_NAMES)
        self.diff_combo.setCurrentIndex(int(store.setting("difficulty", 1)))
        self.diff_combo.setFixedWidth(96)
        self.diff_combo.currentIndexChanged.connect(self._diff_changed)
        self.stat_lbl = QLabel(); self.stat_lbl.setObjectName("dim")
        head.addWidget(t); head.addSpacing(12)
        head.addWidget(QLabel("🎚")); head.addWidget(self.diff_combo)
        head.addStretch(1); head.addWidget(self.stat_lbl)
        lay.addLayout(head)
        self.q = QLabel(); self.q.setObjectName("question"); self.q.setAlignment(Qt.AlignmentFlag.AlignCenter); self.q.setWordWrap(True); lay.addWidget(self.q)
        self.answer = AnswerBox(); self.answer.submitted.connect(self.on_submit); lay.addWidget(self.answer)
        row = QHBoxLayout(); row.addStretch(1)
        self.check_btn = QPushButton("Check"); self.check_btn.setObjectName("primary"); self.check_btn.clicked.connect(self.on_check_btn)
        self.hint_btn = QPushButton("💡 Hint"); self.hint_btn.clicked.connect(self.show_hint)
        self.step_btn = QPushButton("🪜 Show a step"); self.step_btn.clicked.connect(self.reveal_step)
        self.new_btn = QPushButton("🔄 New"); self.new_btn.clicked.connect(self.new_problem)
        for b in (self.check_btn, self.hint_btn, self.step_btn, self.new_btn): row.addWidget(b)
        row.addStretch(1); lay.addLayout(row)
        self.fb = QLabel(); self.fb.setAlignment(Qt.AlignmentFlag.AlignCenter); self.fb.setWordWrap(True); self.fb.setTextFormat(Qt.TextFormat.RichText); self.fb.setVisible(False); lay.addWidget(self.fb)
        self.hint_lbl = QLabel(); self.hint_lbl.setObjectName("hintLbl"); self.hint_lbl.setWordWrap(True); self.hint_lbl.setVisible(False); lay.addWidget(self.hint_lbl)
        self.steps_lbl = QLabel(); self.steps_lbl.setObjectName("stepsLbl"); self.steps_lbl.setTextFormat(Qt.TextFormat.RichText); self.steps_lbl.setWordWrap(True); self.steps_lbl.setVisible(False); lay.addWidget(self.steps_lbl)
        self.new_problem()
    def _diff_changed(self, i: int):
        self.store.set_setting("difficulty", i); self.new_problem()
    def new_problem(self):
        self.problem = self.trick.generate(self.diff_combo.currentIndex())
        self.solved = False; self.revealed = 0
        self.q.setText(self.problem.question); self.answer.load(self.problem)
        self.fb.setVisible(False); self.hint_lbl.setVisible(False); self.steps_lbl.setVisible(False)
        self.hint_btn.setEnabled(True); self.step_btn.setEnabled(True); self.check_btn.setText("Check"); self._update_stats(); self.answer.focus()
    def on_check_btn(self):
        if self.solved: self.new_problem()
        else: self.check_answer(self.answer.text())
    def on_submit(self, text: str):
        if self.solved: self.new_problem()
        else: self.check_answer(text)
    def check_answer(self, text: str):
        if not self.problem or self.solved or not text.strip(): return
        ok = answers_match(text, self.problem.answer, self.problem.accept); self.session_att += 1
        if ok:
            self.streak += 1; self.session_ok += 1; self.store.record_answer(self.trick.id, True, self.streak)
            msg = random.choice(PRAISE)
            if self.revealed == 0 and self.streak >= 2: msg += f" &nbsp;🔥 {self.streak} in a row!"
            self._set_fb(msg, True)
        else:
            self.streak = 0; self.store.record_answer(self.trick.id, False, 0)
            self._set_fb(f"✘ Not quite — the answer was <b>{self.problem.answer}</b>.", False)
        self.solved = True; self.answer.mark(ok); self.answer.set_enabled(False); self.check_btn.setText("Next ➜"); self._update_stats()
    def show_hint(self):
        if self.problem: self.hint_lbl.setText(f"💡 {self.problem.hint}"); self.hint_lbl.setVisible(True); self.hint_btn.setEnabled(False)
    def reveal_step(self):
        if not self.problem or self.revealed >= len(self.problem.steps): return
        self.revealed += 1
        shown = "<br>".join(f"{i + 1}. {s}" for i, s in enumerate(self.problem.steps[: self.revealed]))
        self.steps_lbl.setText(shown); self.steps_lbl.setVisible(True)
        if self.revealed >= len(self.problem.steps): self.step_btn.setEnabled(False)
    def _set_fb(self, html: str, good: bool):
        self.fb.setText(html); self.fb.setProperty("class", "fbGood" if good else "fbBad"); self.fb.style().unpolish(self.fb); self.fb.style().polish(self.fb); self.fb.setVisible(True)
    def _update_stats(self): self.stat_lbl.setText(f"🔥 streak {self.streak}   •   session {self.session_ok}/{self.session_att}")

class ExamplesPanel(QWidget):
    def __init__(self, trick: Trick, store: ProgressStore):
        super().__init__(); self.trick, self.store = trick, store
        v = QVBoxLayout(self); v.setContentsMargins(0, 8, 0, 0); v.setSpacing(10)
        top = QHBoxLayout(); info = QLabel("Fresh worked examples at your current difficulty."); info.setObjectName("dim")
        regen = QPushButton("🔄 New examples"); regen.clicked.connect(self.rebuild)
        top.addWidget(info); top.addStretch(1); top.addWidget(regen); v.addLayout(top)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        host = QWidget(); host.setMaximumWidth(880); self.host_lay = QVBoxLayout(host); self.host_lay.setContentsMargins(0, 0, 0, 0); self.host_lay.setSpacing(10)
        scroll.setWidget(host); v.addWidget(scroll, 1); self.rebuild()
    def rebuild(self):
        while self.host_lay.count():
            item = self.host_lay.takeAt(0); wd = item.widget()
            if wd: wd.deleteLater()
        lvl = int(self.store.setting("difficulty", 1))
        for i in range(2):
            prob = self.trick.generate(lvl)
            steps_html = "<br>".join(f"{n + 1}. {s}" for n, s in enumerate(prob.steps))
            body = f"<div style='font-size:16px;'><b>{prob.question} = {prob.answer}</b></div><br>{steps_html}"
            self.host_lay.addWidget(Card(f"EXAMPLE {i + 1} — {prob.question}", body))
        self.host_lay.addStretch(1)

class TrickPage(QWidget):
    def __init__(self, trick: Trick, store: ProgressStore):
        super().__init__(); self.trick = trick
        v = QVBoxLayout(self); v.setContentsMargins(26, 20, 26, 14); v.setSpacing(8)
        title = QLabel(f"{trick.emoji}  {trick.name}"); title.setObjectName("pageTitle")
        tag = QLabel(trick.tagline); tag.setObjectName("tagline")
        v.addWidget(title); v.addWidget(tag)
        tabs = QTabWidget()
        tabs.addTab(self._build_learn(trick), "📖 Learn")
        tabs.addTab(ExamplesPanel(trick, store), "🧪 Examples")
        practice_host = QWidget(); ph = QVBoxLayout(practice_host); ph.setContentsMargins(0, 10, 0, 0); ph.addWidget(PracticeCard(trick, store)); ph.addStretch(1)
        tabs.addTab(self._scroll(practice_host), "🎯 Practice")
        tabs.addTab(self._build_proof(trick), "🧠 Why it works")
        v.addWidget(tabs, 1)
    @staticmethod
    def _scroll(widget: QWidget) -> QScrollArea:
        s = QScrollArea(); s.setWidgetResizable(True); s.setFrameShape(QFrame.Shape.NoFrame); s.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop); s.setWidget(widget); return s
    def _build_learn(self, trick: Trick) -> QWidget:
        host = QWidget(); host.setMaximumWidth(880); v = QVBoxLayout(host); v.setContentsMargins(0, 10, 0, 0); v.setSpacing(12)
        v.addWidget(Card("📖 THE IDEA", trick.explanation))
        for i, dia_cls in enumerate(DIAGRAMS.get(trick.id, [])):
            dcard = Card("🖼 PICTURE IT" if i == 0 else f"🖼 PICTURE IT — VIEW {i + 1}")
            dcard.add(dia_cls()); v.addWidget(dcard)
        v.addWidget(Card("🧪 WORKED EXAMPLE", trick.example)); v.addStretch(1); return self._scroll(host)
    def _build_proof(self, trick: Trick) -> QWidget:
        host = QWidget(); host.setMaximumWidth(880); v = QVBoxLayout(host); v.setContentsMargins(0, 10, 0, 0); v.setSpacing(12)
        v.addWidget(Card("🧠 WHY IT WORKS", trick.proof))
        v.addWidget(Card(None, "<i>Every trick here is just ordinary algebra in disguise — that's why it works every single time.</i>"))
        v.addStretch(1); return self._scroll(host)

class CheatSheetPage(QWidget):
    def __init__(self, tricks: List[Trick], open_cb: Callable[[str], None]):
        super().__init__(); self.tricks, self.open_cb = tricks, open_cb
        v = QVBoxLayout(self); v.setContentsMargins(26, 22, 26, 14); v.setSpacing(8)
        title = QLabel("📋 Cheat Sheet"); title.setObjectName("pageTitle")
        sub = QLabel("Every trick at a glance. Click a card to jump straight to its lesson."); sub.setObjectName("dim")
        v.addWidget(title); v.addWidget(sub); v.addSpacing(4)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget(); grid = QGridLayout(host); grid.setContentsMargins(0, 6, 0, 0); grid.setSpacing(12); grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        for i, t in enumerate(tricks): grid.addWidget(self._cell(t), i // 2, i % 2)
        scroll.setWidget(host); v.addWidget(scroll, 1)
    def _cell(self, t: Trick) -> QWidget:
        card = Card(f"{t.emoji}  {t.name}", f"<span style='color:#c9d3f5; font-size:14px;'>{t.cheat}</span>")
        btn = QPushButton("Open lesson →"); btn.setObjectName("ghost"); btn.clicked.connect(lambda _=False, tid=t.id: self.open_cb(tid))
        row = QHBoxLayout(); row.addStretch(1); row.addWidget(btn); card.add_layout(row); return card

# --------------------------------------------------------------------------- #
#  Quiz
# --------------------------------------------------------------------------- #
class QuizPage(QWidget):
    def __init__(self, tricks: List[Trick], store: ProgressStore):
        super().__init__(); self.tricks, self.store = tricks, store
        self.timer = QTimer(self); self.timer.setInterval(1000); self.timer.timeout.connect(self.tick)
        self.playing = False; self.time_left = 0; self.duration = 60; self.diff = 1; self.active: List[Trick] = []
        self.problem: Optional[Problem] = None; self.score = self.attempts = self.streak = self.best_streak = 0; self.locked = False; self.missed: List[tuple] = []
        v = QVBoxLayout(self); v.setContentsMargins(26, 22, 26, 22); v.setSpacing(12)
        title = QLabel("🎲 Quick Quiz"); title.setObjectName("pageTitle"); v.addWidget(title)
        self.stack = QStackedWidget(); self.stack.addWidget(self._build_setup()); self.stack.addWidget(self._build_play()); self.stack.addWidget(self._build_results()); v.addWidget(self.stack, 1)
    def _build_setup(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(14)
        intro = QLabel("Mix any tricks you like, set the clock and difficulty, and score as many as you can."); intro.setObjectName("dim"); v.addWidget(intro)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget(); hl = QVBoxLayout(host); hl.setContentsMargins(0, 0, 0, 0)
        card = Card("TRICKS IN THE MIX"); head = QHBoxLayout(); head.addStretch(1)
        all_btn = QPushButton("All"); all_btn.setObjectName("ghost"); all_btn.clicked.connect(lambda: self._toggle_all(True))
        none_btn = QPushButton("None"); none_btn.setObjectName("ghost"); none_btn.clicked.connect(lambda: self._toggle_all(False))
        head.addWidget(all_btn); head.addWidget(none_btn); card.add_layout(head)
        grid = QGridLayout(); grid.setSpacing(4); self.checks = {}
        for i, t in enumerate(self.tricks): cb = QCheckBox(f"{t.emoji}  {t.name}"); cb.setChecked(True); self.checks[t.id] = cb; grid.addWidget(cb, i // 2, i % 2)
        card.add_layout(grid); hl.addWidget(card); scroll.setWidget(host); v.addWidget(scroll, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel("🎚 Difficulty:"))
        self.diff_combo = QComboBox(); self.diff_combo.addItems(DIFF_NAMES)
        self.diff_combo.setCurrentIndex(int(self.store.setting("difficulty", 1)))
        self.diff_combo.currentIndexChanged.connect(lambda i: self.store.set_setting("difficulty", i))
        row.addWidget(self.diff_combo)
        row.addSpacing(18)
        row.addWidget(QLabel("⏱ Time limit:"))
        self.dur_combo = QComboBox(); self.dur_combo.addItems(["30", "60", "90", "120"]); self.dur_combo.setCurrentIndex(1)
        row.addWidget(self.dur_combo); row.addWidget(QLabel("seconds")); row.addStretch(1); v.addLayout(row)
        start_row = QHBoxLayout(); start_row.addStretch(1)
        start = QPushButton("▶  Start quiz"); start.setObjectName("primary"); start.clicked.connect(self.start_quiz)
        start_row.addWidget(start); start_row.addStretch(1); v.addLayout(start_row); return w
    def _build_play(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(12)
        top = QHBoxLayout()
        self.score_lbl = QLabel("⭐ 0"); self.score_lbl.setObjectName("statBig")
        self.streak_lbl = QLabel("🔥 0"); self.streak_lbl.setObjectName("statBig")
        self.time_lbl = QLabel("⏱ 1:00"); self.time_lbl.setObjectName("statBig")
        top.addWidget(self.score_lbl); top.addStretch(1); top.addWidget(self.streak_lbl); top.addStretch(1); top.addWidget(self.time_lbl); v.addLayout(top)
        self.bar = QProgressBar(); self.bar.setTextVisible(False); self.bar.setFixedHeight(10); v.addWidget(self.bar); v.addSpacing(6)
        card = Card(); self.q = QLabel("…"); self.q.setObjectName("question"); self.q.setAlignment(Qt.AlignmentFlag.AlignCenter); self.q.setWordWrap(True)
        self.answer = AnswerBox(); self.answer.submitted.connect(self.on_submit)
        self.fb = QLabel(); self.fb.setAlignment(Qt.AlignmentFlag.AlignCenter); self.fb.setWordWrap(True); self.fb.setTextFormat(Qt.TextFormat.RichText); self.fb.setVisible(False)
        skip = QPushButton("Skip ⏭"); skip.setObjectName("ghost"); skip.clicked.connect(self.skip)
        card.add(self.q); card.add(self.answer); card.add(self.fb)
        skip_row = QHBoxLayout(); skip_row.addStretch(1); skip_row.addWidget(skip); skip_row.addStretch(1); card.add_layout(skip_row); v.addWidget(card); v.addStretch(1); return w
    def _build_results(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(12); v.addStretch(1)
        t = QLabel("⏰ Time's up!"); t.setObjectName("pageTitle"); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.final_lbl = QLabel(); self.final_lbl.setObjectName("finalScore"); self.final_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_lbl = QLabel(); self.summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(t); v.addWidget(self.final_lbl); v.addWidget(self.summary_lbl)
        self.missed_card = Card("WORTH ANOTHER LOOK"); self.missed_lbl = QLabel(); self.missed_lbl.setTextFormat(Qt.TextFormat.RichText); self.missed_lbl.setWordWrap(True); self.missed_card.add(self.missed_lbl); v.addWidget(self.missed_card)
        row = QHBoxLayout(); row.addStretch(1)
        again = QPushButton("▶  Play again"); again.setObjectName("primary"); again.clicked.connect(self.start_quiz)
        settings = QPushButton("⚙  Change settings"); settings.setObjectName("ghost"); settings.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        row.addWidget(again); row.addWidget(settings); row.addStretch(1); v.addLayout(row); v.addStretch(2); return w
    def _toggle_all(self, state: bool):
        for cb in self.checks.values(): cb.setChecked(state)
    def preset_and_start(self, ids: Optional[List[str]] = None):
        for tid, cb in self.checks.items(): cb.setChecked(True if ids is None else tid in ids)
        self.start_quiz()
    def start_quiz(self):
        selected = [t for t in self.tricks if self.checks[t.id].isChecked()]
        if not selected: self.checks[self.tricks[0].id].setChecked(True); selected = [self.tricks[0]]
        self.active = selected; self.diff = self.diff_combo.currentIndex()
        self.duration = int(self.dur_combo.currentText()); self.time_left = self.duration
        self.score = self.attempts = self.streak = self.best_streak = 0; self.missed = []
        self.score_lbl.setText("⭐ 0"); self.streak_lbl.setText("🔥 0"); self.bar.setRange(0, self.duration); self.bar.setValue(self.duration)
        self.playing = True; self.stack.setCurrentIndex(1); self.next_problem(); self._update_time_lbl(); self.timer.start()
    def next_problem(self):
        if not self.playing: return
        self.locked = False; trick = random.choice(self.active); self.problem = trick.generate(self.diff)
        self.q.setText(self.problem.question); self.answer.load(self.problem); self.fb.setVisible(False); self.answer.focus()
    def on_submit(self, text: str):
        if self.locked or not self.problem or not text.strip(): return
        self.locked = True; self.attempts += 1; ok = answers_match(text, self.problem.answer, self.problem.accept)
        if ok:
            self.score += 1; self.streak += 1; self.best_streak = max(self.best_streak, self.streak)
            self._fb(f"{random.choice(PRAISE)} &nbsp;({self.problem.question} = {self.problem.answer})", True); QTimer.singleShot(650, self.next_problem)
        else:
            self.streak = 0; self.missed.append((self.problem.question, self.problem.answer)); self._fb(f"✘ It was <b>{self.problem.answer}</b>", False); QTimer.singleShot(1300, self.next_problem)
        self.answer.mark(ok); self.score_lbl.setText(f"⭐ {self.score}"); self.streak_lbl.setText(f"🔥 {self.streak}")
    def skip(self):
        if not self.locked: self.next_problem()
    def tick(self):
        self.time_left -= 1; self.bar.setValue(max(self.time_left, 0)); self._update_time_lbl()
        if self.time_left <= 0: self.finish()
    def finish(self):
        self.timer.stop(); self.playing = False; self.store.record_quiz(self.score)
        acc = round(100 * self.score / self.attempts) if self.attempts else 0
        self.final_lbl.setText(f"⭐ {self.score} points"); self.summary_lbl.setText(f"{self.score}/{self.attempts} correct ({acc}%)   •   best streak 🔥 {self.best_streak}")
        if self.missed:
            rows = "<br>".join(f"• {q} = <b>{a}</b>" for q, a in self.missed[:12]); extra = "<br>• …" if len(self.missed) > 12 else ""
            self.missed_lbl.setText(rows + extra); self.missed_card.setVisible(True)
        else: self.missed_card.setVisible(False)
        self.stack.setCurrentIndex(2)
    def _fb(self, html: str, good: bool):
        self.fb.setText(html); self.fb.setProperty("class", "fbGood" if good else "fbBad"); self.fb.style().unpolish(self.fb); self.fb.style().polish(self.fb); self.fb.setVisible(True)
    def _update_time_lbl(self): m, s = divmod(max(self.time_left, 0), 60); self.time_lbl.setText(f"⏱ {m}:{s:02d}")

# --------------------------------------------------------------------------- #
#  Progress / Home / Main window
# --------------------------------------------------------------------------- #
class ProgressPage(QWidget):
    COLS = [90, 90, 90, 120]
    def __init__(self, tricks: List[Trick], store: ProgressStore):
        super().__init__(); self.tricks, self.store = tricks, store
        v = QVBoxLayout(self); v.setContentsMargins(26, 22, 26, 22); v.setSpacing(10)
        title = QLabel("📈 Your progress"); title.setObjectName("pageTitle"); sub = QLabel("Practice results are saved automatically on this computer."); sub.setObjectName("dim")
        v.addWidget(title); v.addWidget(sub); v.addSpacing(6)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame); host = QWidget(); self.host_lay = QVBoxLayout(host); self.host_lay.setContentsMargins(0, 0, 0, 0); self.host_lay.setSpacing(6)
        self.host_lay.addWidget(self._row(["Trick", "Attempts", "Correct", "Accuracy", "Best streak"], header=True)); scroll.setWidget(host); v.addWidget(scroll, 1)
        self.quiz_lbl = QLabel(); self.quiz_lbl.setObjectName("dim"); v.addWidget(self.quiz_lbl)
        reset_row = QHBoxLayout(); reset_row.addStretch(1); reset = QPushButton("🗑  Reset all progress"); reset.setObjectName("ghost"); reset.clicked.connect(self._confirm_reset); reset_row.addWidget(reset); v.addLayout(reset_row)
        self._rows: List[QWidget] = []; self.refresh()
    def _row(self, cells, bold=False, header=False) -> QWidget:
        w = QFrame()
        if not header: w.setObjectName("row")
        h = QHBoxLayout(w); h.setContentsMargins(14, 9, 14, 9); h.setSpacing(6); name = QLabel(cells[0])
        if header: name.setObjectName("dim")
        if bold: f = name.font(); f.setBold(True); name.setFont(f)
        h.addWidget(name, 1)
        for i, c in enumerate(cells[1:]):
            l = QLabel(str(c)); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setFixedWidth(self.COLS[i])
            if header: l.setObjectName("dim")
            if bold: f = l.font(); f.setBold(True); l.setFont(f)
            h.addWidget(l)
        return w
    def refresh(self):
        for w in self._rows: self.host_lay.removeWidget(w); w.deleteLater()
        self._rows.clear(); tot_att = tot_cor = tot_best = 0
        for trick in self.tricks:
            st = self.store.trick_stats(trick.id); att, cor, best = st["attempts"], st["correct"], st["best_streak"]
            tot_att += att; tot_cor += cor; tot_best = max(tot_best, best)
            acc = f"{cor * 100 // att}%" if att else "—"
            row = self._row([f"{trick.emoji}  {trick.name}", att, cor, acc, f"🔥 {best}" if best else "—"]); self.host_lay.addWidget(row); self._rows.append(row)
        acc = f"{tot_cor * 100 // tot_att}%" if tot_att else "—"
        total = self._row(["Total", tot_att, tot_cor, acc, f"🔥 {tot_best}" if tot_best else "—"], bold=True); self.host_lay.addWidget(total); self._rows.append(total); self.host_lay.addStretch(1)
        q = self.store.data["quiz"]; self.quiz_lbl.setText(f"🎲 Quizzes played: {q['played']}   •   Best quiz score: {q['best_score']}")
    def _confirm_reset(self):
        reply = QMessageBox.question(self, "Reset progress", "Delete all saved practice and quiz statistics? (Preferences are kept.)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: self.store.reset(); self.refresh()

class HomePage(QWidget):
    def __init__(self, store: ProgressStore, goto: Callable[[str], None]):
        super().__init__(); self.store, self.goto = store, goto
        v = QVBoxLayout(self); v.setContentsMargins(30, 30, 30, 20); v.addStretch(1)
        logo = QLabel("🧮 MathWiz"); logo.setObjectName("logo"); logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag = QLabel("36 tricks • 63 diagrams • 3 difficulty levels. Learn, practise, beat the clock."); tag.setObjectName("tagline"); tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(logo); v.addWidget(tag); v.addSpacing(14)
        how = Card(None, "📖 &nbsp;Each lesson has tabs: idea, diagrams, fresh examples, practice, and the proof.<br><br>🎚 &nbsp;Switch between Easy, Normal and Hard anywhere — the setting is remembered.<br><br>🩹 &nbsp;Weak-spot drill jumps straight into a quiz of only the tricks you find hardest.<br><br>🎲 &nbsp;Timed quizzes track score, streaks, and what to review.")
        how.setMaximumWidth(600); v.addWidget(how, 0, Qt.AlignmentFlag.AlignCenter); v.addSpacing(10)
        self.stats_lbl = QLabel(); self.stats_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); self.stats_lbl.setTextFormat(Qt.TextFormat.RichText); self.stats_lbl.setWordWrap(True); v.addWidget(self.stats_lbl); v.addSpacing(10)
        row = QHBoxLayout(); row.addStretch(1)
        quiz_btn = QPushButton("🎲  Start a quiz"); quiz_btn.setObjectName("primary"); quiz_btn.clicked.connect(lambda: self.goto("quiz"))
        drill_btn = QPushButton("🩹  Weak-spot drill"); drill_btn.clicked.connect(lambda: self.goto("weak"))
        sheet_btn = QPushButton("📋  Cheat sheet"); sheet_btn.clicked.connect(lambda: self.goto("sheet"))
        trick_btn = QPushButton("✨  Show me a trick"); trick_btn.clicked.connect(lambda: self.goto("first"))
        row.addWidget(quiz_btn); row.addWidget(drill_btn); row.addWidget(sheet_btn); row.addWidget(trick_btn); row.addStretch(1); v.addLayout(row); v.addStretch(2); self.refresh()
    def refresh(self):
        att, cor, best = self.store.totals(); acc = f"{cor * 100 // att}%" if att else "—"; q = self.store.data["quiz"]
        weak = len(self.store.weak_tricks())
        weak_txt = f" &nbsp;•&nbsp; Weak spots: <b>{weak}</b>" if att else ""
        self.stats_lbl.setText(f"Problems answered: <b>{att}</b> &nbsp;•&nbsp; Accuracy: <b>{acc}</b> &nbsp;•&nbsp; Best streak: <b>🔥 {best}</b>{weak_txt}<br>Quizzes played: <b>{q['played']}</b> &nbsp;•&nbsp; Best quiz score: <b>{q['best_score']}</b>")

class MainWindow(QMainWindow):
    HEADER_ROW = 4
    def __init__(self):
        super().__init__(); self.setWindowTitle("MathWiz — Mental Math Tricks"); self.resize(1200, 820); self.setMinimumSize(1040, 700)
        self.store = ProgressStore()
        central = QWidget(); h = QHBoxLayout(central); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0); h.addWidget(self._build_sidebar())
        self.stack = QStackedWidget()
        self.home = HomePage(self.store, self.goto); self.quiz = QuizPage(TRICKS, self.store); self.progress = ProgressPage(TRICKS, self.store); self.sheet = CheatSheetPage(TRICKS, self.goto_trick)
        self.stack.addWidget(self.home); self.stack.addWidget(self.quiz); self.stack.addWidget(self.progress); self.stack.addWidget(self.sheet)
        for trick in TRICKS: self.stack.addWidget(TrickPage(trick, self.store))
        h.addWidget(self.stack, 1); self.setCentralWidget(central); self.list.currentRowChanged.connect(self._on_row); self.list.setCurrentRow(0)
    def _build_sidebar(self) -> QWidget:
        side = QWidget(); side.setObjectName("sidebar"); side.setFixedWidth(246); v = QVBoxLayout(side); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        brand = QLabel("🧮 MathWiz"); brand.setObjectName("brand"); self.list = QListWidget(); self.list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.list.addItem("🏠  Home"); self.list.addItem("🎲  Quiz Mode"); self.list.addItem("📈  Progress"); self.list.addItem("📋  Cheat Sheet")
        header = QListWidgetItem("LESSONS"); header.setFlags(Qt.ItemFlag.ItemIsEnabled); header.setData(Qt.ItemDataRole.ForegroundRole, QColor("#6d7488"))
        f = QFont(); f.setPointSize(9); f.setBold(True); header.setData(Qt.ItemDataRole.FontRole, f); self.list.addItem(header)
        for t in TRICKS: self.list.addItem(f"{t.emoji}  {t.name}")
        note = QLabel("💾 progress saved locally"); note.setObjectName("sideNote"); v.addWidget(brand); v.addWidget(self.list, 1); v.addWidget(note); return side
    def _on_row(self, row: int):
        if row < 0 or row == self.HEADER_ROW: return
        idx = row if row <= 3 else row - 1; self.stack.setCurrentIndex(idx); page = self.stack.widget(idx)
        if hasattr(page, "refresh"): page.refresh()
    def goto(self, key: str):
        if key == "weak":
            weak = self.store.weak_tricks()
            self.quiz.preset_and_start(weak or None)
            if self.list.currentRow() != 1: self.list.setCurrentRow(1)
            return
        row = {"home": 0, "quiz": 1, "progress": 2, "sheet": 3, "first": 5}[key]
        self.list.setCurrentRow(row)
    def goto_trick(self, trick_id: str):
        row = 5 + [t.id for t in TRICKS].index(trick_id); self.list.setCurrentRow(row)

def make_icon() -> QIcon:
    pix = QPixmap(64, 64); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#4c7df0")); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 14, 14)
    p.setPen(QColor("#ffffff")); p.setFont(_f(30))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "π")
    p.end()
    return QIcon(pix)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(make_icon())
    win = MainWindow(); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()