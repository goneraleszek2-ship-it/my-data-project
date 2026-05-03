import json
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker('pl_PL')
random.seed(42)

ACCOUNTS = [fake.iban() for _ in range(20)]
CURRENCIES = ['PLN', 'USD', 'EUR', 'CHF']

def random_date(days_back=90):
    return datetime.now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

def generate_transactions(n=500):
    txns = []
    for _ in range(int(n * 0.80)):
        txns.append({
            "txn_id": fake.uuid4(),
            "timestamp": random_date().isoformat(),
            "account_from": random.choice(ACCOUNTS),
            "account_to": random.choice(ACCOUNTS),
            "amount": round(random.uniform(10, 8000), 2),
            "currency": random.choice(CURRENCIES),
            "country": "PL",
            "channel": random.choice(["ONLINE", "BRANCH", "ATM"]),
            "flagged": False
        })
    structuring_account = random.choice(ACCOUNTS)
    base_date = random_date(days_back=10)
    for i in range(8):
        txns.append({
            "txn_id": fake.uuid4(),
            "timestamp": (base_date + timedelta(hours=i*3)).isoformat(),
            "account_from": structuring_account,
            "account_to": random.choice(ACCOUNTS),
            "amount": round(random.uniform(13500, 14900), 2),
            "currency": "PLN",
            "country": "PL",
            "channel": "ONLINE",
            "flagged": False
        })
    roundtrip_account = random.choice(ACCOUNTS)
    rt_date = random_date(days_back=5)
    amount = round(random.uniform(50000, 200000), 2)
    for country in ['PL', 'RU', 'CY', 'PL']:
        txns.append({
            "txn_id": fake.uuid4(),
            "timestamp": (rt_date + timedelta(days=1)).isoformat(),
            "account_from": roundtrip_account,
            "account_to": fake.iban(),
            "amount": round(amount * random.uniform(0.97, 1.0), 2),
            "currency": "USD",
            "country": country,
            "channel": "WIRE",
            "flagged": False
        })
        rt_date += timedelta(days=1)
    random.shuffle(txns)
    return txns

if __name__ == "__main__":
    txns = generate_transactions(500)
    with open("transactions.json", "w") as f:
        json.dump(txns, f, indent=2, ensure_ascii=False)
    print(f"Wygenerowano {len(txns)} transakcji -> transactions.json")
