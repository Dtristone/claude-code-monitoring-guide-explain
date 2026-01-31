# Frequently Asked Questions: Metrics, Traces, and Statistics

This document addresses common questions about Claude Code telemetry, including why metrics may appear limited, how to collect detailed traces, and how to achieve specific statistical goals.

## Table of Contents

1. [Why Do Metrics Show Only a Few Lines?](#1-why-do-metrics-show-only-a-few-lines)
2. [How to Collect Detailed Session Traces](#2-how-to-collect-detailed-session-traces)
3. [Target Statistics Collection](#3-target-statistics-collection)
   - [Input/Output Tokens per Request/Session/Total](#input-output-tokens-per-request-session-total)
   - [Time Breakdown of Each Loop](#time-breakdown-of-each-loop-llm-calling-tool-use-others)
   - [KV Cache Hit Ratio](#kv-cache-hit-ratio)

---

## 1. Why Do Metrics Show Only a Few Lines?

### Understanding the Metrics Endpoint

When you visit `http://localhost:8889/metrics` (or your configured endpoint), you might see only a few `claude_code_*` metrics. This is **expected behavior** for several reasons:

### Reasons for Limited Metrics

#### A. Metrics Are Created On-Demand

Claude Code only exports metrics when the corresponding events occur:

| Metric | When It Appears |
|--------|-----------------|
| `claude_code_token_usage_tokens_total` | After an LLM request completes |
| `claude_code_cost_usage_USD_total` | After a session incurs cost |
| `claude_code_session_count_total` | When a new session starts |
| `claude_code_commit_count_total` | When a git commit is made during a session |
| `claude_code_pull_request_count_total` | When a PR is created during a session |
| `claude_code_lines_of_code_count_total` | When code is modified |
| `claude_code_code_edit_tool_decision_total` | When a code edit tool permission is granted/denied |

**If you haven't performed these actions, the corresponding metrics won't exist.**

#### B. Metric Expiration

The OTEL Collector is configured with `metric_expiration: 180m` (3 hours). This means:
- Metrics that haven't received new data in 180 minutes are removed from the endpoint
- This prevents stale metrics from accumulating
- After periods of inactivity, you'll see fewer metrics

#### C. Not Sampling-Related

**This is NOT a sampling issue.** Unlike distributed tracing where sampling reduces data volume, Claude Code metrics use **counters** that track **all** events:

```yaml
# The debug exporter does use sampling for logging purposes only:
debug:
  sampling_initial: 5         # Logs first 5 items
  sampling_thereafter: 200    # Then every 200th item

# BUT the Prometheus exporter exports ALL metrics without sampling
prometheus:
  endpoint: "0.0.0.0:8889"
  # No sampling - all data is exported
```

The `sampling_initial` and `sampling_thereafter` settings in the debug exporter only affect what gets logged to the console, NOT what gets exported to Prometheus.

#### D. All Configured Metrics Are Collected

Claude Code exports a **fixed set of metrics** (listed above). These are ALL the metrics available - there are no "hidden" metrics that require special configuration.

### What You Should See

After active Claude Code usage, your metrics endpoint should show entries like:

```prometheus
# HELP claude_code_token_usage_tokens_total 
# TYPE claude_code_token_usage_tokens_total counter
claude_code_token_usage_tokens_total{job="claude-code",model="claude-4-sonnet",type="input",user_id="xxx",session_id="yyy"} 750
claude_code_token_usage_tokens_total{job="claude-code",model="claude-4-sonnet",type="output",user_id="xxx",session_id="yyy"} 1200
claude_code_token_usage_tokens_total{job="claude-code",model="claude-4-sonnet",type="cacheRead",user_id="xxx",session_id="yyy"} 50000
claude_code_token_usage_tokens_total{job="claude-code",model="claude-4-sonnet",type="cacheCreation",user_id="xxx",session_id="yyy"} 2000

# HELP claude_code_cost_usage_USD_total
# TYPE claude_code_cost_usage_USD_total counter
claude_code_cost_usage_USD_total{job="claude-code",model="claude-4-sonnet",user_id="xxx",session_id="yyy"} 0.05
```

### How to Verify All Metrics Are Being Collected

1. **Enable Console Export for Debugging**:
   ```bash
   export OTEL_METRICS_EXPORTER=console
   export OTEL_METRIC_EXPORT_INTERVAL=1000
   claude -p "test message"
   ```
   This will print ALL metrics to your terminal as they're generated.

2. **Check OTEL Collector Logs**:
   ```bash
   docker-compose logs otel-collector | grep -i metric
   ```

3. **Generate Activity**: Run a few Claude Code sessions with actual work (code edits, commits) to generate all metric types.

---

## 2. How to Collect Detailed Session Traces

Claude Code supports exporting detailed logs that include session traces, user prompts, and assistant responses.

### Basic Log Collection Setup

#### Step 1: Enable Log Export in Claude Code

Add these environment variables to your configuration:

```bash
# Enable telemetry
export CLAUDE_CODE_ENABLE_TELEMETRY=1

# Enable logs exporter
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Set log export interval (milliseconds)
export OTEL_LOGS_EXPORT_INTERVAL=5000

# Include user prompts in logs (optional - privacy consideration)
export OTEL_LOG_USER_PROMPTS=1
```

Or in `~/.claude.json`:

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    "OTEL_LOGS_EXPORT_INTERVAL": "5000",
    "OTEL_LOG_USER_PROMPTS": "1"
  }
}
```

#### Step 2: Configure OTEL Collector for Log Export

Update your `otel-collector-config.yaml` to include log processing and file export:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
    send_timestamps: true
    metric_expiration: 180m
    enable_open_metrics: true
    
  debug:
    verbosity: detailed
    sampling_initial: 5
    sampling_thereafter: 200

  # File exporter for detailed logs
  file/logs:
    path: /var/log/otel/claude-code-traces.jsonl
    rotation:
      max_megabytes: 100
      max_days: 7
      max_backups: 5

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus, debug]
    
    # Add logs pipeline
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [file/logs, debug]
      
  extensions: []
  
  telemetry:
    logs:
      level: "debug"
```

#### Step 3: Update Docker Compose for Log Volume

Add a volume mount for log files in `docker-compose.yml`:

```yaml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
      - ./logs:/var/log/otel  # Add this line for log files
    ports:
      - "4317:4317"
      - "4318:4318"
      - "8889:8889"
    depends_on:
      - prometheus
```

#### Step 4: Access Your Traces

After configuration, your traces will be saved to `./logs/claude-code-traces.jsonl`. Each line is a JSON object containing:

```json
{
  "Timestamp": "2025-01-15T10:30:00.000Z",
  "SeverityText": "INFO",
  "Body": "User prompt: How do I implement...",
  "Attributes": {
    "session.id": "abc-123",
    "user.id": "user-hash",
    "service.name": "claude-code"
  }
}
```

### Alternative: Console Output for Real-time Viewing

For debugging or real-time monitoring without file storage:

```bash
export OTEL_LOGS_EXPORTER=console
export OTEL_LOG_USER_PROMPTS=1
claude
```

This prints all traces directly to your terminal.

### Alternative: Send to Loki for Grafana Visualization

For advanced log analysis and visualization in Grafana:

```yaml
exporters:
  loki:
    endpoint: http://loki:3100/loki/api/v1/push
    labels:
      attributes:
        service.name: "service_name"
        session.id: "session_id"
```

Then query logs in Grafana using LogQL.

---

## 3. Target Statistics Collection

### Input/Output Tokens per Request/Session/Total

#### Per-Request Tokens

Claude Code reports tokens at the **request level**. Each LLM API call updates the `claude_code_token_usage_tokens_total` counter.

**PromQL Query - Tokens per Request (Rate)**:
```promql
# Input tokens rate (tokens per minute)
rate(claude_code_token_usage_tokens_total{type="input"}[5m]) * 60

# Output tokens rate (tokens per minute)
rate(claude_code_token_usage_tokens_total{type="output"}[5m]) * 60
```

#### Per-Session Tokens

Tokens are already labeled with `session_id`, allowing per-session analysis.

**PromQL Query - Tokens by Session**:
```promql
# Total input tokens per session
sum by (session_id)(claude_code_token_usage_tokens_total{type="input"})

# Total output tokens per session
sum by (session_id)(claude_code_token_usage_tokens_total{type="output"})

# All token types per session
sum by (session_id, type)(claude_code_token_usage_tokens_total)
```

**PromQL Query - Average Tokens per Session**:
```promql
# Average input tokens per session
avg(sum by (session_id)(claude_code_token_usage_tokens_total{type="input"}))

# Average output tokens per session
avg(sum by (session_id)(claude_code_token_usage_tokens_total{type="output"}))
```

#### Total Tokens

**PromQL Query - Total Tokens**:
```promql
# Total input tokens (all time)
sum(claude_code_token_usage_tokens_total{type="input"})

# Total output tokens (all time)
sum(claude_code_token_usage_tokens_total{type="output"})

# Total all tokens (all time)
sum(claude_code_token_usage_tokens_total)

# Total tokens over a specific time range
sum(increase(claude_code_token_usage_tokens_total[24h]))
```

#### Input/Output Ratio

**PromQL Query - I/O Ratio**:
```promql
# Input to output token ratio (lower means more output per input)
sum(claude_code_token_usage_tokens_total{type="input"}) 
/ 
sum(claude_code_token_usage_tokens_total{type="output"})
```

### Time Breakdown of Each Loop (LLM Calling, Tool Use, Others)

⚠️ **Current Limitation**: Claude Code's built-in telemetry does **not** directly export timing metrics for individual loop phases (LLM calling, tool execution, etc.).

#### Available Timing Metric

Claude Code provides:
- `claude_code.active_time.total` - Total active time in seconds per session

**PromQL Query - Active Time**:
```promql
# Total active time across all sessions
sum(claude_code_active_time_total_seconds)

# Active time per session
sum by (session_id)(claude_code_active_time_total_seconds)

# Average session duration
avg(sum by (session_id)(claude_code_active_time_total_seconds))
```

#### Workarounds for Detailed Timing

##### Option 1: Analyze Log Timestamps

If you enable detailed logging (`OTEL_LOG_USER_PROMPTS=1`), you can parse the log timestamps to calculate durations between events:

```bash
# Example: Parse JSONL logs to extract timing
cat ./logs/claude-code-traces.jsonl | jq -r '[.Timestamp, .Body] | @tsv' | while read ts body; do
  echo "$ts: $body"
done
```

##### Option 2: Use External APM

For detailed timing breakdowns, consider using an Application Performance Monitoring (APM) tool that can instrument the Claude Code process:
- **Datadog APM**
- **New Relic**
- **Jaeger/OpenTelemetry Tracing**

##### Option 3: Estimate from Token Rates

You can approximate LLM processing time based on token throughput:

```promql
# Estimate: If average throughput is ~50 tokens/second for output
# Total output time ≈ total_output_tokens / 50
sum(increase(claude_code_token_usage_tokens_total{type="output"}[1h])) / 50
```

##### Option 4: Request Feature

The Claude Code team may add more granular timing metrics in the future. You can:
1. Check the [Claude Code GitHub issues](https://github.com/anthropics/claude-code/issues) for existing feature requests
2. Submit a feature request for detailed timing telemetry

### KV Cache Hit Ratio

Claude Code exports cache-related token metrics that allow you to calculate the KV cache hit ratio.

#### Understanding Cache Metrics

| Token Type | Description |
|------------|-------------|
| `cacheRead` | Tokens retrieved from the KV cache (cache hits) |
| `cacheCreation` | Tokens stored in the KV cache (new cache entries) |
| `input` | Regular input tokens (not from cache) |
| `output` | Generated output tokens |

#### KV Cache Hit Ratio Calculation

**PromQL Query - Cache Hit Ratio**:
```promql
# Cache hit ratio: cacheRead / (cacheRead + cacheCreation)
# Higher value = better cache utilization
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
(sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="cacheCreation"}))
```

**PromQL Query - Cache Efficiency over Time**:
```promql
# Cache hit ratio over the last hour
sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[1h])) 
/ 
(sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[1h])) + sum(increase(claude_code_token_usage_tokens_total{type="cacheCreation"}[1h])))
```

**PromQL Query - Cache Hit Ratio by Session**:
```promql
# Cache ratio per session
sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
(sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheCreation"}))
```

**PromQL Query - Cache Read to Input Ratio**:
```promql
# How much of total "input" is served from cache
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
(sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="input"}))
```

#### Interpreting Cache Ratios

| Ratio | Interpretation |
|-------|----------------|
| 0.9+ (90%+) | Excellent cache efficiency - most context is reused |
| 0.7-0.9 | Good efficiency - substantial cache reuse |
| 0.5-0.7 | Moderate efficiency - mixed reuse patterns |
| < 0.5 | Low efficiency - frequent context changes |

**Typical observed ratio**: According to real telemetry data, ratios of 39:1 (cacheRead:cacheCreation) are common, indicating excellent cache utilization in conversational workflows.

### Prefix Cache Statistics

Beyond basic cache hit ratios, you can calculate comprehensive prefix cache statistics similar to those available in vLLM monitoring setups. These metrics help you understand the cost savings and efficiency gains from prefix caching.

#### Cache Cost Savings

One of the most valuable metrics is understanding how much money you're saving through cache hits. Cache reads are significantly cheaper than full input token processing.

**PromQL Query - Total Cost Savings from Cache**:
```promql
# Estimated cost savings (USD) from cache hits
# Assuming cache reads cost 10% of regular input tokens
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) * 0.000003 * 0.9
```

**PromQL Query - Cost Savings Percentage**:
```promql
# What percentage of potential input costs were saved by cache
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
(sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="input"}))
```

**PromQL Query - Cache Savings Over Time**:
```promql
# Cost savings trend over the last 24 hours
sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[1h])) * 0.000003 * 0.9
```

#### Cache Efficiency Percentage

This metric shows what percentage of your total input context is being served from cache rather than processed as new tokens.

**PromQL Query - Overall Cache Efficiency**:
```promql
# Percentage of total input served from cache
(
  sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
  / 
  (sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="input"}))
) * 100
```

**PromQL Query - Cache Efficiency by Session**:
```promql
# Per-session cache efficiency percentage
(
  sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) 
  / 
  (sum by (session_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum by (session_id)(claude_code_token_usage_tokens_total{type="input"}))
) * 100
```

**PromQL Query - Cache Efficiency by Model**:
```promql
# Compare cache efficiency across different models
(
  sum by (model)(claude_code_token_usage_tokens_total{type="cacheRead"}) 
  / 
  (sum by (model)(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum by (model)(claude_code_token_usage_tokens_total{type="input"}))
) * 100
```

#### Cache Token Distribution

Understand the distribution of cache reads vs cache creation to identify optimization opportunities.

**PromQL Query - Cache Read vs Creation Ratio**:
```promql
# How many tokens are read from cache for every token written to cache
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
sum(claude_code_token_usage_tokens_total{type="cacheCreation"})
```

**PromQL Query - Total Cached Tokens**:
```promql
# Total tokens involved in caching operations
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="cacheCreation"})
```

**PromQL Query - Cache Operations Over Time**:
```promql
# Track cache read and creation patterns over time
sum by (type)(rate(claude_code_token_usage_tokens_total{type=~"cacheRead|cacheCreation"}[5m])) * 60
```

#### Cache Performance by User

Identify which users are getting the most benefit from caching.

**PromQL Query - Cache Efficiency by User**:
```promql
# Per-user cache efficiency
(
  sum by (user_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) 
  / 
  (sum by (user_id)(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum by (user_id)(claude_code_token_usage_tokens_total{type="input"}))
) * 100
```

**PromQL Query - Top Users by Cache Savings**:
```promql
# Users with highest absolute cache token usage
topk(10, sum by (user_id)(claude_code_token_usage_tokens_total{type="cacheRead"}))
```

#### Advanced Cache Metrics

**PromQL Query - Cache Waste Ratio**:
```promql
# Tokens cached but never read (potential waste)
# Lower is better - indicates cache is being utilized
sum(claude_code_token_usage_tokens_total{type="cacheCreation"}) 
/ 
sum(claude_code_token_usage_tokens_total{type="cacheRead"})
```

**PromQL Query - Effective Cache Utilization**:
```promql
# Ratio of cache reads to total tokens processed
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
sum(claude_code_token_usage_tokens_total)
```

**PromQL Query - Cache ROI**:
```promql
# Return on investment: how many tokens read per token cached
# Higher values indicate better ROI
sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[$__range])) 
/ 
sum(increase(claude_code_token_usage_tokens_total{type="cacheCreation"}[$__range]))
```

#### Interpreting Prefix Cache Statistics

| Metric | Good Range | Interpretation |
|--------|-----------|----------------|
| Cache Hit Ratio | 80-95% | High reuse of cached context |
| Cache Efficiency % | 70-90% | Most input served from cache |
| Cache Savings % | 60-85% | Significant cost reduction |
| Cache Read:Creation Ratio | 20:1 - 50:1 | Excellent cache reuse |
| Cache Waste Ratio | < 0.1 (10%) | Minimal unused cache entries |
| Cache ROI | > 10:1 | Strong return on caching overhead |

**Best Practices for Prefix Cache Optimization**:
1. **Monitor cache efficiency by session** - Identify which workflows benefit most from caching
2. **Track cache savings** - Quantify the cost benefits of your caching strategy
3. **Analyze by model** - Different models may have different cache behaviors
4. **Watch for waste** - If cache creation >> cache reads, consider adjusting your caching strategy
5. **Compare users** - Learn from high-efficiency users' patterns

---

## Summary: Grafana Dashboard Queries

Here's a summary of all the recommended PromQL queries you can add to your Grafana dashboard:

### Token Metrics Panel

```promql
# Total Tokens by Type
sum by (type)(increase(claude_code_token_usage_tokens_total[$__range]))

# Tokens per Session
sum by (session_id)(claude_code_token_usage_tokens_total)

# Token Rate (per minute)
rate(claude_code_token_usage_tokens_total[5m]) * 60
```

### Cache Efficiency Panel

```promql
# Cache Hit Ratio (Gauge)
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
(sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="cacheCreation"}))

# Cache Efficiency Over Time (Graph)
sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[$__interval])) 
/ 
(sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[$__interval])) + sum(increase(claude_code_token_usage_tokens_total{type="cacheCreation"}[$__interval])))
```

### Prefix Cache Statistics Panel

```promql
# Cache Cost Savings (USD)
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) * 0.000003 * 0.9

# Cache Efficiency Percentage
(sum(claude_code_token_usage_tokens_total{type="cacheRead"}) / (sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="input"}))) * 100

# Cache Read:Creation Ratio
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) / sum(claude_code_token_usage_tokens_total{type="cacheCreation"})

# Cache Efficiency by Model
(sum by (model)(claude_code_token_usage_tokens_total{type="cacheRead"}) / (sum by (model)(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum by (model)(claude_code_token_usage_tokens_total{type="input"}))) * 100

# Cache ROI (tokens read per token created)
sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[$__range])) / sum(increase(claude_code_token_usage_tokens_total{type="cacheCreation"}[$__range]))
```

### Session Duration Panel

```promql
# Average Session Duration
avg(sum by (session_id)(claude_code_active_time_total_seconds))

# Session Duration by User
sum by (user_id)(claude_code_active_time_total_seconds)
```

### Cost Analysis Panel

```promql
# Cost per Token
sum(claude_code_cost_usage_USD_total) 
/ 
sum(claude_code_token_usage_tokens_total)

# Cost per Session
sum by (session_id)(claude_code_cost_usage_USD_total)
```

---

## Quick Reference Card

| Goal | Environment Variables |
|------|----------------------|
| Enable telemetry | `CLAUDE_CODE_ENABLE_TELEMETRY=1` |
| Export metrics to OTEL | `OTEL_METRICS_EXPORTER=otlp` |
| Export logs/traces to OTEL | `OTEL_LOGS_EXPORTER=otlp` |
| Set OTEL endpoint | `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` |
| Include user prompts | `OTEL_LOG_USER_PROMPTS=1` |
| Debug to console | `OTEL_METRICS_EXPORTER=console` |

| Goal | PromQL Query |
|------|--------------|
| Total tokens | `sum(claude_code_token_usage_tokens_total)` |
| Tokens by session | `sum by (session_id)(claude_code_token_usage_tokens_total)` |
| Cache hit ratio | `sum(claude_code_token_usage_tokens_total{type="cacheRead"}) / clamp_min(sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="cacheCreation"}), 1)` |
| Cache efficiency % | `(sum(claude_code_token_usage_tokens_total{type="cacheRead"}) / (sum(claude_code_token_usage_tokens_total{type="cacheRead"}) + sum(claude_code_token_usage_tokens_total{type="input"}))) * 100` |
| Cache cost savings | `sum(claude_code_token_usage_tokens_total{type="cacheRead"}) * 0.000003 * 0.9` |
| Cache ROI | `sum(increase(claude_code_token_usage_tokens_total{type="cacheRead"}[$__range])) / sum(increase(claude_code_token_usage_tokens_total{type="cacheCreation"}[$__range]))` |
| I/O ratio | `sum(claude_code_token_usage_tokens_total{type="input"}) / sum(claude_code_token_usage_tokens_total{type="output"})` |
