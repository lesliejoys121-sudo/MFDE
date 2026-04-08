import requests
import json

BASE_URL = "http://127.0.0.1:8080"

def test():
    print("--- Testing Score Normalization ---")
    
    # 1. Reset
    requests.post(f"{BASE_URL}/reset", json={"task": "easy"})
    res = requests.get(f"{BASE_URL}/api/performance")
    print(f"Initial XP: {res.json()['total_score']}") # Should be 0.01
    
    # 2. Step (Correct)
    # Easy correct: decision='reply', priority='medium'
    payload = {"decision": "reply", "priority": "medium", "email_id": 0}
    requests.post(f"{BASE_URL}/step", json=payload)
    
    res = requests.get(f"{BASE_URL}/api/performance")
    print(f"Step 1 XP: {res.json()['total_score']}") # Should be 0.01 + 0.99 = 1.0 roughly
    
    # Check Grader Score via /state (This is what validator usually sees)
    res = requests.get(f"{BASE_URL}/schema") # Just to check schema
    res = requests.get(f"{BASE_URL}/state")
    history = res.json()["history"]
    from grader import grade
    print(f"Grader Final Score: {grade(history)}")

if __name__ == "__main__":
    test()
