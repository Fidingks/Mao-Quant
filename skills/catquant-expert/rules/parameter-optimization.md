---
name: parameter-optimization
description: Parameter optimization methods for A-share strategy tuning
metadata:
  tags: optimization, grid-search, heatmap, parameters
  last_verified: "2026-03-15"
---

# Parameter Optimization

## Loop-Based Grid Search (Recommended)

```python
from tqdm import tqdm
import itertools

results = []
param_grid = list(itertools.product(range(5, 51, 5), range(10, 61, 5)))

for fast, slow in tqdm(param_grid, desc="Optimizing"):
    if fast >= slow:
        continue
    # ... generate signals and run backtest ...
    results.append({
        "fast": fast, "slow": slow,
        "total_return": pf.total_return(),
        "sharpe": pf.sharpe_ratio(),
        "max_dd": pf.max_drawdown(),
        "trades": pf.trades.count(),
    })

df_results = pd.DataFrame(results)
```

## Output: Top 10 by Total Return AND Sharpe

```python
print("Top 10 by Total Return:")
print(df_results.nlargest(10, "total_return").to_string())

print("\nTop 10 by Sharpe Ratio:")
print(df_results.nlargest(10, "sharpe").to_string())
```

## Heatmap Visualization

```python
import plotly.express as px

pivot = df_results.pivot(index="slow", columns="fast", values="total_return")
fig = px.imshow(pivot, template="plotly_dark", color_continuous_scale="RdYlGn",
                title="Total Return Heatmap", labels={"x": "Fast EMA", "y": "Slow EMA"})
fig.show()
```
