import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "catquant"))
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from catquant.resolve import resolve, check_available

# Step 0a: Resolve 茅台 to code
code, name = resolve("茅台")
print(f"Resolved: {name} -> {code}")

# Step 0b: Check data availability
ok, source, hint = check_available(code)
print(f"Data check: ok={ok}, source={source}")
if not ok:
    print(f"Hint: {hint}")
    sys.exit(1)
else:
    print("Data is available, proceeding with backtest...")
