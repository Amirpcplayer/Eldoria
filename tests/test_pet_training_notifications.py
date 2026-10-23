from services.pet_training_service import build_training_notification_message


def test_training_notification_uses_real_line_breaks():
    message = build_training_notification_message("اژدها", level=7, start_level=6)

    assert "\\n" not in message
    assert message.splitlines() == [
        "🐾 آموزش پت «اژدها» به پایان رسید!",
        "✨ XP دریافت‌شده: +100",
        "⭐ سطح فعلی پت: Lv.7",
        "🎉 پت لول‌آپ کرد: Lv.6 → Lv.7",
    ]


def test_training_notification_without_level_up():
    message = build_training_notification_message("گرگ", level=6, start_level=6)

    assert "لول‌آپ" not in message
    assert message.splitlines() == [
        "🐾 آموزش پت «گرگ» به پایان رسید!",
        "✨ XP دریافت‌شده: +100",
        "⭐ سطح فعلی پت: Lv.6",
    ]
