"""Generates sample_data/sample_reviews.csv (synthetic) to test the pipeline without any API keys."""
import random
from datetime import datetime, timedelta
import pandas as pd

random.seed(1)
pos = ["Love the product, amazing quality and the support team was so helpful.",
       "Great value for money, easy to use interface, would recommend to anyone.",
       "Fast delivery and excellent service. Thank you, very happy with Acme."]
neg = ["Terrible customer service, nobody replied to my ticket for weeks. Worst experience.",
       "Hidden fees and a nightmare to cancel my subscription. Felt like a scam.",
       "The app keeps crashing, very frustrating bug after the last update.",
       "Still waiting for my refund. Disappointed and angry about the billing."]
neu = ["Used Acme for a month, the dashboard has some features and an integration with Slack.",
       "Delivery took five days, package arrived as described."]
rows = []
for i in range(120):
    pl = random.choice(["trustpilot", "reddit", "g2", "linkedin", "google_reviews"])
    pool = random.choice([pos, neg, neg, neu])
    t = random.choice(pool) + f" (note {i})"
    rating = {"pos": 5, "neg": 1}.get("pos" if pool is pos else "neg" if pool is neg else "", 3)
    rows.append(dict(platform=pl, text=t, rating=rating if pl in ("trustpilot", "g2", "google_reviews") else "",
                     date=(datetime(2026, 1, 1) + timedelta(days=random.randint(0, 300))).date(),
                     author=f"person{random.randint(1, 40)}", url="https://example.com/r/" + str(i),
                     engagement=random.randint(0, 30)))
rows.append(dict(platform="trustpilot", text="BEST EVER!!! BUY NOW THE BEST COMPANY", rating=5, date="2026-03-03", author="x1", url="", engagement=0))
rows.append(dict(platform="trustpilot", text="BEST EVER!!! BUY NOW THE BEST COMPANY", rating=5, date="2026-03-03", author="x2", url="", engagement=0))
pd.DataFrame(rows).to_csv("sample_data/sample_reviews.csv", index=False)
print("written", len(rows))
