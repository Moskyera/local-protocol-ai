from telegram_engine import send_full_ai_briefing
from master_market_brain import generate_master_report
import os

# Δημιουργία φακέλου αν δεν υπάρχει
briefings_dir = "simplex_briefings"
os.makedirs(briefings_dir, exist_ok=True)

print("🚀 Generating Full AI Briefing for Simplex Channel...\n")

briefing = generate_master_report("BTC/USDT")

print("\n" + "="*80)
print("FULL AI BRIEFING - READY FOR SIMPLEX CHANNEL")
print("="*80 + "\n")

print(briefing)

# Αποθήκευση σε ξεχωριστό φάκελο
filename = f"{briefings_dir}/briefing_simplex_{{date}}.md".format(date="TODAY")  # μπορείς να βάλεις ημερομηνία αν θες

with open(f"{briefings_dir}/briefing_simplex.md", "w", encoding="utf-8") as f:
    f.write(briefing)

print(f"\n✅ Briefing saved to folder: {briefings_dir}\\briefing_simplex.md")
print("Μπορείς να το ανοίξεις και να κάνεις copy-paste στο Simplex Channel.")