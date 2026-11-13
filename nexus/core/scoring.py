from math import isfinite
WEIGHTS = {"C":0.35,"O":0.25,"R":0.20,"E":0.20}
def score(components, weights=None):
    weights = WEIGHTS if weights is None else weights
    if set(weights) != set(WEIGHTS) or any(not isfinite(w) or w<0 for w in weights.values()) or abs(sum(weights.values())-1)>1e-8:
        raise ValueError("Weights must cover C/O/R/E, be nonnegative and sum to 1")
    values = {k: 0.0 if components.get(k) is None else float(components[k]) for k in WEIGHTS}
    if any(not 0<=v<=100 for v in values.values()):
        raise ValueError("Components must be finite values in 0–100")
    return round(sum(values[k]*weights[k] for k in weights),2)

