import os
import yaml
from functools import lru_cache
from typing import Optional


PERIODS = [
    (1, 3),
    (4, 7),
    (8, 14),
    (15, 30),
    (31, 60),
    (61, 90),
    (91, 99999),
]

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "content")
FACTS_DIR = os.path.join(os.path.dirname(__file__), "facts")


@lru_cache(maxsize=None)
def load_all_content() -> dict:
    content = {}
    for i in range(1, 8):
        path = os.path.join(CONTENT_DIR, f"period_{i}.yaml")
        with open(path, "r", encoding="utf-8") as f:
            content[i] = yaml.safe_load(f)
    return content


@lru_cache(maxsize=None)
def load_all_facts() -> dict:
    path = os.path.join(FACTS_DIR, "all_facts.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # индексируем по номеру периода
    result = {}
    for p in data["periods"]:
        result[p["period"]] = p
    return result


def get_period_index(day: int) -> int:
    for i, (start, end) in enumerate(PERIODS, start=1):
        if start <= day <= end:
            return i
    return 7


def get_period_start(period_idx: int) -> int:
    return PERIODS[period_idx - 1][0]


def get_content_for_day(day: int) -> Optional[dict]:
    idx = get_period_index(day)
    return load_all_content().get(idx)


def get_fact_for_day(day: int) -> Optional[dict]:
    idx = get_period_index(day)
    facts_data = load_all_facts().get(idx)
    if not facts_data:
        return None
    facts = facts_data["facts"]
    period_start = get_period_start(idx)
    fact_index = (day - period_start) % len(facts)
    return facts[fact_index]


def is_first_day_of_period(day: int) -> bool:
    idx = get_period_index(day)
    return day == get_period_start(idx)


def format_period_intro(day: int) -> str:
    """Полный контент периода — отправляется один раз при входе в период."""
    content = get_content_for_day(day)
    if not content:
        return ""

    symptoms_text = "\n".join(
        f"• {s['symptom']}\n  _{s['cause']}_"
        for s in content["symptoms"]["items"]
    )

    return (
        f"📋 *Новый период: {content['title']}* (дни {content['days']})\n"
        f"_{content['subtitle']}_\n\n"
        f"*{content['physiology']['heading']}*\n"
        f"{content['physiology']['body'].strip()}\n\n"
        f"*{content['symptoms']['heading']}*\n"
        f"{symptoms_text}\n\n"
        f"*{content['recovering']['heading']}*\n"
        f"{content['recovering']['body'].strip()}\n\n"
        f"*{content['tip']['heading']}*\n"
        f"{content['tip']['body'].strip()}"
    )


def format_daily_message(day: int) -> str:
    """Ежедневное сообщение — факт дня."""
    fact = get_fact_for_day(day)
    if not fact:
        return f"День {day}."

    return (
        f"*День {day}*\n\n"
        f"_{fact['scientific']}_\n\n"
        f"{fact['plain']}"
    )
