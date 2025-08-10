from packages.smart_money.engine import SmartMoneyEngine

if __name__ == "__main__":
    eng = SmartMoneyEngine()
    eng.train_if_needed()
    print("Training (if needed) completed.")
