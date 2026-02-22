from __future__ import annotations

from fastapi import HTTPException


DASHBOARD_PAYLOAD = {
    "learner": {
        "name": "Амина",
        "track": "Алгебра + Геометрия",
        "streak_days": 12,
        "weekly_goal": 5,
        "lessons_done": 3,
        "mastery_percent": 68,
    },
    "learning_path": [
        {
            "id": "lesson-linear-equations",
            "title": "Линейные уравнения: одна переменная",
            "topic": "Алгебра",
            "difficulty": "Начальный",
            "duration_min": 30,
            "status": "в_процессе",
        },
        {
            "id": "lesson-quadratic-intro",
            "title": "Квадратичные функции: интуиция",
            "topic": "Алгебра",
            "difficulty": "Средний",
            "duration_min": 40,
            "status": "рекомендуется",
        },
        {
            "id": "lesson-triangles-core",
            "title": "Треугольники и подобие",
            "topic": "Геометрия",
            "difficulty": "Средний",
            "duration_min": 35,
            "status": "заблокировано",
        },
    ],
    "practice_queue": [
        {
            "id": "set-linear-drill-01",
            "title": "Тренировка по линейным уравнениям №1",
            "focus": "Решение уравнений",
            "problems": 12,
            "due_date": "2026-02-10",
        },
        {
            "id": "set-geometry-angles-01",
            "title": "Углы в треугольниках",
            "focus": "База геометрии",
            "problems": 10,
            "due_date": "2026-02-12",
        },
    ],
    "recent_activity": [
        "Завершён квиз: разминка по дробям",
        "Точность в линейных уравнениях выросла до 86%",
        "Проведено 28 минут в режиме фокусной практики",
    ],
    "mastery_trend": [61, 62, 64, 65, 67, 68],
    "weak_topics": ["Разложение квадратных выражений", "Погоня за углами", "Преобразование неравенств"],
    "quick_actions": [
        {"id": "resume_lesson", "label": "Продолжить урок"},
        {"id": "start_practice", "label": "Начать практику"},
        {"id": "review_mistakes", "label": "Разобрать ошибки"},
    ],
    "formulas": ["a^2 - b^2 = (a-b)(a+b)", "sin^2(x) + cos^2(x) = 1", "(a+b)^2 = a^2 + 2ab + b^2"],
    "next_lesson_id": "lesson-quadratic-intro",
    "assignments": [
        {"title": "Набор B: линейные уравнения", "due_date": "2026-02-11"},
        {"title": "Контрольная: треугольники", "due_date": "2026-02-13"},
    ],
}

LESSON_PAYLOADS = {
    "lesson-linear-equations": {
        "id": "lesson-linear-equations",
        "title": "Линейные уравнения: одна переменная",
        "topic": "Алгебра",
        "estimated_min": 30,
        "objectives": [
            "Поэтапно изолировать переменную",
            "Проверять решения подстановкой",
            "Переводить текстовые условия в уравнения",
        ],
        "theory_points": [
            "Равенство сохраняется, если одинаково менять обе части уравнения.",
            "Перед изоляцией переменной объединяйте подобные слагаемые.",
            "Всегда проверяйте ответ в исходном уравнении.",
        ],
        "exercises": [
            {"id": "ex-1", "prompt": "Решите: 3x + 7 = 25", "type": "numeric"},
            {"id": "ex-2", "prompt": "Решите: 5(x - 2) = 20", "type": "numeric"},
            {
                "id": "ex-3",
                "prompt": "Число плюс 9 равно удвоенному числу минус 3. Найдите это число.",
                "type": "word_problem",
            },
        ],
    },
    "lesson-quadratic-intro": {
        "id": "lesson-quadratic-intro",
        "title": "Квадратичные функции: интуиция",
        "topic": "Алгебра",
        "estimated_min": 40,
        "objectives": [
            "Определять направление ветвей параболы",
            "Оценивать вершину по виду уравнения",
            "Связывать корни с пересечениями оси X",
        ],
        "theory_points": [
            "Квадратичная функция имеет вид ax^2 + bx + c.",
            "Знак a определяет, направлена парабола вверх или вниз.",
            "Корни — это значения x, при которых y равно нулю.",
        ],
        "exercises": [
            {"id": "ex-1", "prompt": "Для y = x^2 - 4x + 3 укажите корни", "type": "numeric"},
            {"id": "ex-2", "prompt": "Функция y = -2x^2 + 1 направлена вверх или вниз?", "type": "single_choice"},
        ],
    },
}


def get_dashboard_payload() -> dict:
    return DASHBOARD_PAYLOAD


def get_lesson_payload_or_404(lesson_id: str) -> dict:
    payload = LESSON_PAYLOADS.get(lesson_id)
    if not payload:
        raise HTTPException(status_code=404, detail="урок не найден")
    return payload
