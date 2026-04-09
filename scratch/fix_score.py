import re

def fix():
    with open('../app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix backend rounding
    content = content.replace('"total_score": round(score, 1),', '"total_score": round(score, 2),')
    
    # Fix frontend rendering
    content = content.replace('x-text="perf.total_score"', 'x-text="perf.total_score.toFixed(2)"')
    
    with open('../app.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    fix()
