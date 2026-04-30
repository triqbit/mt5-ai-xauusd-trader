# Research Summary: {{ report_id }}

**Period:** {{ period_start }} to {{ period_end }}
**Generated At:** {{ timestamp }}

## Executive Summary
{{ summary }}

{% if regime_analysis %}
## Regime Analysis
- **Current Regime:** {{ regime_analysis.current_regime }}
- **Volatility Profile:** {{ regime_analysis.volatility_profile }}
- **Distribution:**
{% for k, v in regime_analysis.regime_distribution.items() %}
  - {{ k }}: {{ (v * 100) | round(1) }}%
{% endfor %}
{% if regime_analysis.details %}

{{ regime_analysis.details }}
{% endif %}
{% endif %}

{% if stress_tests %}
## Stress Test Outcomes
| Scenario | Max DD | PnL Impact | Status |
| :--- | :--- | :--- | :--- |
{% for st in stress_tests %}
| {{ st.scenario_name }} | {{ (st.max_drawdown * 100) | round(2) }}% | {{ st.pnl_impact }} | {{ "✅ PASS" if st.passed else "❌ FAIL" }} |
{% endfor %}
{% endif %}

{% if hyperparameter_robustness %}
## Hyperparameter Robustness
| Parameter | Optimal Value | Stability | Recommendation |
| :--- | :--- | :--- | :--- |
{% for hr in hyperparameter_robustness %}
| {{ hr.parameter_name }} | {{ hr.optimal_value }} | {{ hr.stability_score | round(2) }} | {{ hr.recommendation }} |
{% endfor %}
{% endif %}

{% if trade_patterns %}
## Trade Pattern Findings
{% for tp in trade_patterns %}
### {{ tp.pattern_name }} (Freq: {{ tp.frequency }})
- **Impact:** {{ (tp.win_rate_impact * 100) | round(2) }}% win rate
- **Score:** {{ tp.significance_score | round(2) }}
- {{ tp.description }}
{% endfor %}
{% endif %}

{% if model_drift %}
## Model Drift Observations
| Model ID | Metric | Baseline | Current | Drift Score |
| :--- | :--- | :--- | :--- | :--- |
{% for md_obs in model_drift %}
| {{ md_obs.model_id }} {{ "⚠️" if md_obs.drift_detected else "" }} | {{ md_obs.metric_name }} | {{ md_obs.baseline_value | round(4) }} | {{ md_obs.current_value | round(4) }} | {{ md_obs.drift_score | round(2) }} |
{% endfor %}
{% endif %}

{% if allocation_insights %}
## Allocation Insights
| Strategy | Weight | Contribution | Marginal Sharpe |
| :--- | :--- | :--- | :--- |
{% for ai in allocation_insights %}
| {{ ai.strategy_id }} {{ "🚨" if ai.over_allocated else "" }} | {{ (ai.allocated_weight * 100) | round(2) }}% | {{ (ai.performance_contribution * 100) | round(2) }}% | {{ ai.marginal_sharpe | round(2) }} |
{% endfor %}
{% endif %}

{% if benchmarks %}
## Benchmark Comparisons
| Benchmark | Alpha | Beta | Strategy Return | Benchmark Return |
| :--- | :--- | :--- | :--- | :--- |
{% for bc in benchmarks %}
| {{ bc.benchmark_name }} | {{ bc.alpha | round(2) }} | {{ bc.beta | round(2) }} | {{ (bc.strategy_return * 100) | round(2) }}% | {{ (bc.benchmark_return * 100) | round(2) }}% |
{% endfor %}
{% endif %}
