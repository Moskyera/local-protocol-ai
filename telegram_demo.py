from master_market_brain import (
    generate_master_report
)

from telegram_engine import (
    send_telegram_message
)

report = generate_master_report()

send_telegram_message(
    report
)

print(
    "AI report sent to Telegram."
)