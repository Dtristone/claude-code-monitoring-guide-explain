# Prefix Cache Monitoring Guide

This guide explains how to monitor and optimize prefix cache (KV cache) performance in Claude Code, similar to monitoring approaches used in vLLM and other LLM serving systems.

## Table of Contents

1. [What is Prefix Caching?](#what-is-prefix-caching)
2. [Why Monitor Prefix Cache?](#why-monitor-prefix-cache)
3. [Key Metrics Explained](#key-metrics-explained)
4. [Dashboard Panels](#dashboard-panels)
5. [Optimization Strategies](#optimization-strategies)
6. [Real-World Examples](#real-world-examples)
7. [Troubleshooting](#troubleshooting)

---

## What is Prefix Caching?

Prefix caching (also called KV cache or context cache) is a technique where the LLM reuses previously computed key-value pairs from earlier parts of a conversation or context. Instead of reprocessing the same context every time, the model can "read" from the cache, significantly reducing:

- **Processing time**: Cached tokens are retrieved instantly
- **Compute costs**: No need to reprocess the same context
- **Latency**: Faster response times for users

### How It Works in Claude Code

```
First Request:
┌─────────────────────────────────────┐
│ System Prompt + Code Context        │ ← cacheCreation (2000 tokens)
│ + User Question                     │ ← input (100 tokens)
└─────────────────────────────────────┘
                ↓
        [LLM Processing]
                ↓
        Response (output: 500 tokens)

Second Request (same session):
┌─────────────────────────────────────┐
│ System Prompt + Code Context        │ ← cacheRead (2000 tokens) ✓ Cached!
│ + New User Question                 │ ← input (120 tokens)
└─────────────────────────────────────┘
                ↓
        [Minimal Processing]
                ↓
        Response (output: 450 tokens)
```

---

## Why Monitor Prefix Cache?

Monitoring prefix cache performance helps you:

1. **Quantify Cost Savings**: Understand how much money you're saving through cache reuse
2. **Optimize Usage Patterns**: Identify workflows that benefit most from caching
3. **Detect Issues**: Spot when cache isn't being utilized effectively
4. **Make Informed Decisions**: Decide whether to adjust conversation structure or session management
5. **Benchmark Performance**: Compare cache efficiency across teams, models, or time periods

---

## Key Metrics Explained

### 1. Cache Hit Ratio

**What it measures**: The ratio of cache reads to total cache operations (reads + creations).

**Formula**: `cacheRead / (cacheRead + cacheCreation)`

**Good values**: 80-95%

**Interpretation**:
- **90%+**: Excellent - Most requests reuse cached context
- **70-90%**: Good - Substantial cache reuse
- **50-70%**: Moderate - Mixed patterns
- **< 50%**: Low - Frequent context changes or short sessions

**Example**:
```
cacheRead: 50,000 tokens
cacheCreation: 2,000 tokens
Cache Hit Ratio = 50,000 / (50,000 + 2,000) = 96.2% ✓ Excellent!
```

### 2. Cache Efficiency Percentage

**What it measures**: What percentage of your total input is served from cache vs. processed as new tokens.

**Formula**: `cacheRead / (cacheRead + input) × 100`

**Good values**: 70-90%

**Interpretation**:
- **85%+**: Most of your context is cached - very efficient
- **60-85%**: Good balance of cached and new content
- **40-60%**: Moderate efficiency - room for improvement
- **< 40%**: Low efficiency - consider session management changes

**Example**:
```
cacheRead: 45,000 tokens
input: 5,000 tokens
Cache Efficiency = 45,000 / (45,000 + 5,000) × 100 = 90% ✓ Excellent!
```

### 3. Cache Cost Savings

**What it measures**: Actual dollars saved by using cached tokens instead of processing them as new input.

**Formula**: `cacheRead × input_token_cost × 0.9`

**Notes**:
- Cache reads typically cost ~10% of regular input token processing
- Formula calculates the 90% cost reduction from using cache
- Based on Sonnet pricing: ~$0.003 per 1K input tokens

**Example**:
```
cacheRead: 50,000 tokens
Input token cost: $0.003 per 1K tokens
Full processing cost would be: 50 × $0.003 = $0.15
Cache read actual cost: 50 × $0.003 × 0.1 = $0.015
Savings: $0.15 - $0.015 = $0.135 per session
```

### 4. Cache Read:Creation Ratio

**What it measures**: How many tokens you read from cache for every token you write to cache.

**Formula**: `cacheRead / cacheCreation`

**Good values**: 20:1 to 50:1

**Interpretation**:
- **40:1+**: Excellent cache reuse - context is used many times
- **20:1-40:1**: Good reuse - healthy pattern
- **10:1-20:1**: Moderate reuse - acceptable
- **< 10:1**: Low reuse - cache entries may be underutilized

**Example**:
```
cacheRead: 78,000 tokens
cacheCreation: 2,000 tokens
Ratio = 78,000 / 2,000 = 39:1 ✓ Excellent reuse!
```

### 5. Cache ROI (Return on Investment)

**What it measures**: The return on the overhead of creating cache entries, measured over a time period.

**Formula**: `increase(cacheRead[period]) / increase(cacheCreation[period])`

**Good values**: > 10:1

**Interpretation**:
- **20:1+**: Strong ROI - cache creation overhead is well justified
- **10:1-20:1**: Good ROI - cache is beneficial
- **5:1-10:1**: Moderate ROI - cache is helpful but could improve
- **< 5:1**: Low ROI - consider adjusting caching strategy

### 6. Cache Waste Ratio

**What it measures**: The inverse of cache utilization - how much cache is created but never read.

**Formula**: `cacheCreation / cacheRead`

**Good values**: < 0.1 (10%)

**Interpretation**:
- **< 0.05 (5%)**: Excellent - minimal waste
- **0.05-0.10**: Good - acceptable overhead
- **0.10-0.20**: Moderate - some optimization possible
- **> 0.20 (20%)**: High waste - review session management

---

## Dashboard Panels

The Grafana dashboard includes these prefix cache panels:

### Cache Cost Savings (Stat Panel)
- **Type**: Single stat with trend
- **Shows**: Total USD saved from cache hits
- **Use**: Track cumulative cost savings over time
- **Action**: Higher values prove cache value to stakeholders

### Cache Efficiency % (Gauge Panel)
- **Type**: Gauge (0-100%)
- **Shows**: Percentage of input served from cache
- **Use**: Quick health check of cache utilization
- **Action**: Aim for 70%+ efficiency

### Cache Read:Creation Ratio (Stat Panel)
- **Type**: Single stat
- **Shows**: Ratio of tokens read per token cached
- **Use**: Measure cache reuse effectiveness
- **Action**: Target 20:1 or higher

### Cache ROI (Stat Panel)
- **Type**: Single stat
- **Shows**: Return on caching investment
- **Use**: Justify caching overhead
- **Action**: Maintain > 10:1 ratio

### Cache Efficiency by Model (Time Series)
- **Type**: Line graph
- **Shows**: Cache efficiency % for each model
- **Use**: Compare models' cache behavior
- **Action**: Identify which models benefit most

### Cache Cost Savings Over Time (Time Series)
- **Type**: Line graph
- **Shows**: Hourly cost savings trend
- **Use**: Track savings patterns
- **Action**: Correlate with usage patterns

---

## Optimization Strategies

### 1. Maximize Cache Hit Ratio

**Problem**: Cache hit ratio below 70%

**Solutions**:
- Keep sessions alive longer to benefit from accumulated cache
- Structure prompts to reuse common context
- Avoid unnecessary context changes mid-session
- Use consistent system prompts across requests

**Example**:
```bash
# Bad: New session for each question (no cache benefit)
claude "Question 1 about file.py"
claude "Question 2 about file.py"  # No shared cache

# Good: Single session with multiple turns
claude  # Start session
> Question 1 about file.py
> Question 2 about file.py  # Shares cached context ✓
```

### 2. Reduce Cache Waste

**Problem**: High cache creation but low reuse (waste ratio > 0.15)

**Solutions**:
- End sessions that won't have follow-up questions
- Avoid caching one-off contexts
- Group related tasks in single sessions
- Monitor session duration vs cache usage

### 3. Improve Cache Efficiency Percentage

**Problem**: Low cache efficiency (< 60%)

**Solutions**:
- Include stable context (file contents, documentation) that won't change
- Minimize dynamic content in prompts
- Reuse code context across multiple questions
- Structure conversations to maximize context reuse

### 4. Increase Cache ROI

**Problem**: Cache ROI below 10:1

**Solutions**:
- Ensure cached context is relevant for multiple queries
- Avoid caching content that changes frequently
- Balance context size vs. likelihood of reuse
- Extend session duration for complex tasks

---

## Real-World Examples

### Example 1: Code Review Session

```
Scenario: Reviewing a 500-line Python file

Request 1:
- cacheCreation: 2,500 tokens (system prompt + file)
- input: 50 tokens ("Review this code")
- output: 800 tokens

Request 2-5 (follow-up questions):
- cacheRead: 2,500 tokens each (4 × 2,500 = 10,000)
- input: 60 tokens each (4 × 60 = 240)
- output: 600 tokens each (4 × 600 = 2,400)

Total cache usage:
- cacheCreation: 2,500 tokens
- cacheRead: 10,000 tokens
- Cache Hit Ratio: 10,000 / 12,500 = 80% ✓
- Cache ROI: 10,000 / 2,500 = 4:1

Cost savings: 10,000 × 0.000003 × 0.9 = $0.027 saved
```

### Example 2: Long Development Session

```
Scenario: 2-hour coding session with file edits

Session stats:
- cacheCreation: 15,000 tokens (initial context)
- cacheRead: 600,000 tokens (40 requests × 15,000)
- input: 8,000 tokens (new questions/instructions)
- output: 25,000 tokens (responses)

Metrics:
- Cache Hit Ratio: 600,000 / 615,000 = 97.6% ✓ Excellent!
- Cache Efficiency: 600,000 / 608,000 = 98.7% ✓ Outstanding!
- Cache ROI: 600,000 / 15,000 = 40:1 ✓ Exceptional!
- Cost savings: 600,000 × 0.000003 × 0.9 = $1.62 saved

Analysis: This session demonstrates ideal cache usage - 
long session with consistent context and many iterations.
```

### Example 3: Poor Cache Usage

```
Scenario: Multiple short, unrelated questions

5 separate sessions:
- Each session: cacheCreation 2,000, cacheRead 0
- Total cacheCreation: 10,000 tokens
- Total cacheRead: 0 tokens
- Cache Hit Ratio: 0% ✗ No benefit!

Problem: Starting new sessions prevents cache reuse
Solution: Combine related work into single sessions
```

---

## Troubleshooting

### Issue: Cache Hit Ratio is 0% or Very Low

**Possible Causes**:
1. Starting new sessions for each request
2. Sessions ending too quickly
3. Context changing completely between requests
4. Configuration issue with cache settings

**Debug Steps**:
```promql
# Check if cache is being created at all
sum(claude_code_token_usage_tokens_total{type="cacheCreation"})

# Check session patterns
sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheCreation"})
```

**Solutions**:
- Keep sessions alive longer
- Group related work together
- Verify cache is enabled in Claude Code settings

### Issue: Cache Efficiency Below 50%

**Possible Causes**:
1. Lots of new unique context in each request
2. Short sessions with little follow-up
3. Rapidly changing code context

**Debug Steps**:
```promql
# Compare cache reads to new input
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
vs 
sum(claude_code_token_usage_tokens_total{type="input"})
```

**Solutions**:
- Structure prompts to reuse stable context
- Minimize dynamic content changes
- Consider conversation flow redesign

### Issue: High Cache Waste (Ratio > 0.2)

**Possible Causes**:
1. Creating cache entries that aren't reused
2. Sessions ending prematurely
3. One-off questions with large context

**Debug Steps**:
```promql
# Check cache waste ratio by session
sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheCreation"})
/
sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheRead"})
```

**Solutions**:
- Extend sessions for multi-turn conversations
- Avoid caching for one-off queries
- End sessions promptly when done

### Issue: Cost Savings Don't Match Expectations

**Possible Causes**:
1. Using incorrect pricing in calculations
2. Model pricing changed
3. Cache read costs different than expected

**Debug Steps**:
- Verify model being used: `sum by (model)(claude_code_cost_usage_USD_total)`
- Check actual costs vs. estimated savings
- Review pricing documentation for current rates

**Solutions**:
- Update cost calculation formula with current pricing
- Factor in your specific plan pricing
- Include cache read costs (typically 10% of input cost)

---

## Advanced Queries for Deep Analysis

### Cache Performance by User
```promql
# Which users get the most cache benefit?
(
  sum by (user_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) 
  / 
  (sum by (user_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum by (user_id)(claude_code_token_usage_tokens_total{type="input"}))
) * 100
```

### Session-Level Cache Analysis
```promql
# Cache efficiency for each session
(
  sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) 
  / 
  (sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheCreation"}))
) * 100
```

### Cache Utilization Trend
```promql
# Cache hit ratio over 5-minute windows
sum(rate(claude_code_token_usage_tokens_total{type="cacheRead"}[5m])) 
/ 
(sum(rate(claude_code_token_usage_tokens_total{type="cacheRead"}[5m])) + sum(rate(claude_code_token_usage_tokens_total{type="cacheCreation"}[5m])))
```

### Cumulative Savings Over Time
```promql
# Total savings accumulated
sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[24h])) * 0.000003 * 0.9
```

---

## Best Practices Summary

1. ✓ **Keep sessions alive** - Longer sessions = more cache benefit
2. ✓ **Group related work** - Combine similar tasks in one session
3. ✓ **Monitor metrics** - Track cache efficiency weekly
4. ✓ **Aim for 70%+ efficiency** - Target high cache utilization
5. ✓ **Measure ROI** - Quantify savings to justify usage
6. ✓ **Learn from patterns** - Identify what works and replicate
7. ✓ **End stale sessions** - Don't keep sessions open unnecessarily
8. ✓ **Optimize prompts** - Structure for context reuse

---

## Additional Resources

- [FAQ: KV Cache Hit Ratio](FAQ-METRICS-AND-TRACES.md#kv-cache-hit-ratio)
- [FAQ: Prefix Cache Statistics](FAQ-METRICS-AND-TRACES.md#prefix-cache-statistics)
- [Usage Guide: Prefix Cache Monitoring Queries](USAGE-GUIDE.md#prefix-cache-monitoring-queries)
- [Anthropic Documentation: Prompt Caching](https://docs.anthropic.com/claude/docs/prompt-caching)

---

**Questions or Issues?** See [troubleshooting.md](troubleshooting.md) or check the [FAQ](FAQ-METRICS-AND-TRACES.md).
