# taxglide (Python)

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Try a calc (Beides + Feuerwehr, no Church)
taxglide calc --year 2025 --income 150000 --pick BEIDES --pick FEUER --skip CHURCH --json

# Try optimize (exact steps)
taxglide optimize --year 2025 --income 150000 --max-deduction 50000 --step 1 \
  --pick BEIDES --pick FEUER --skip CHURCH --json

# Plot (optional PNG)
taxglide plot --year 2025 --min 20000 --max 250000 --step 100 \
  --pick BEIDES --pick FEUER --skip CHURCH --out curve.png
```

Configs live in `configs/2025/`. Rounding behavior is controlled by YAML and easy to tweak.