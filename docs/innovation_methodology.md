# Innovation methodology

Similarity asks which profiles use similar language. Complementarity asks whether specific capabilities can provide inputs, execution context, infrastructure or security for one another.

## Algorithm

1. Extract original descriptions while retaining evidence.
2. Normalise candidate capability terms against a small explicit taxonomy.
3. Admit only source-reviewed FACT capabilities to the complementary matching layer. Inferences and user interests never become company capabilities.
4. Rank up to 12 partner candidates by complementary pair strength. Search pairs and triples with the top 8 partners.
5. Require a coherent shared application domain. Every participant must connect; triples require at least two distinct company links.
6. Require at least two capabilities from a defined innovation concept. The selected company must contribute at least one required capability.
7. Compute research/funding bridges with TF-IDF cosine and tag overlap; use locally cached Sentence Transformers only when explicitly enabled.
8. Score, expose gaps and label the result HYPOTHESIS.

Pair C is zero without an explicit relationship and shared domain; otherwise min(100,45+15×relationship count). A combination's C combines mean pair complementarity (65%), required-capability coverage (25%) and focal-company priority alignment (10%). Missing integration capability is shown rather than invented.

Bridge relevance is 55% text cosine + 45% record-tag overlap. Closed/upcoming funding is excluded from current bridges. Unknown/stale funding is downweighted to 40% and clearly marked; it is never eligibility evidence.

Default S = .35C + .25O + .20R + .20E. Session ranking preferences can adjust these weights; they must be finite, nonnegative and sum to one. Each recommendation and exported blueprint retains the applied weights. Each component lies in 0–100. Missing O/R is None in storage and zero in scoring; weights are not renormalised. Coverage reports available components out of four. Evidence quality is the fraction of reviewed supporting capability claims weighted by freshness (100% fresh, 40% stale). The scores are initial engineering heuristics and are not probabilities.

## Evaluation

21 developer-authored synthetic candidate pairs, with 10 positive labels based on manually specified plausible dependencies. Labels were authored during implementation; they are not independent human judgments or a held-out real company dataset. Exact Precision@5, Recall@5 and top-five set differentiation are calculated by core/evaluation.py and saved by scripts/validate.py. This checks algorithm mechanics and cannot establish commercial usefulness.

The UI also stores actual user ratings and reports them only if submitted. A credible pilot needs independently labelled combinations, inter-rater agreement, wider sectors, temporal holdout and ablations of taxonomy/domain/evidence signals.

## Limits

The taxonomy and concept templates constrain discovery to known patterns. Text matching cannot validate engineering compatibility. Domains are analyst-inferred application categories or user refinements; company confirmation is still required. Lexical similarity is the available fallback; no neural model was executed in the development runtime.

