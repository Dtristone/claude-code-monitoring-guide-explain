# Claude Code Monitoring Usage Guide

This comprehensive guide explains how to configure, use, and troubleshoot the Claude Code monitoring stack using OpenTelemetry (OTEL) Collector, Prometheus, and Grafana.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Component Deep Dive](#component-deep-dive)
   - [OpenTelemetry Collector](#opentelemetry-collector)
   - [Prometheus](#prometheus)
   - [Grafana](#grafana)
5. [Configuration Files Explained](#configuration-files-explained)
6. [Claude Code Environment Variables](#claude-code-environment-variables)
7. [Available Metrics](#available-metrics)
8. [Verifying Your Setup](#verifying-your-setup)
9. [Querying Metrics](#querying-metrics)
10. [Using Grafana Dashboards](#using-grafana-dashboards)
11. [Common Use Cases](#common-use-cases)
12. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The monitoring stack consists of three main components working together:

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                     │     │                 │     │                 │
│   Claude Code   │────▶│  OTEL Collector     │────▶│   Prometheus    │────▶│    Grafana      │
│   (Your IDE)    │     │  (Port 4317/4318)   │     │   (Port 9090)   │     │   (Port 3000)   │
│                 │     │                     │     │                 │     │                 │
└─────────────────┘     └─────────────────────┘     └─────────────────┘     └─────────────────┘
        │                         │                         │                       │
        │   OTLP/gRPC or HTTP     │   Prometheus Format     │   PromQL Queries      │
        └─────────────────────────┘                         └───────────────────────┘
```

### Data Flow

1. **Claude Code** generates telemetry data (metrics, logs) and exports them via OTLP protocol
2. **OpenTelemetry Collector** receives, processes, and exports metrics in Prometheus format
3. **Prometheus** scrapes metrics from the OTEL Collector and stores them in its time-series database
4. **Grafana** queries Prometheus and visualizes the data in dashboards

---

## Prerequisites

- Docker and Docker Compose installed
- Claude Code CLI installed
- Network access to the monitoring endpoints

---

## Quick Start

### Step 1: Start the Monitoring Stack

```bash
# Clone the repository (if not already done)
git clone https://github.com/Dtristone/claude-code-monitoring-guide-explain.git
cd claude-code-monitoring-guide-explain

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Step 2: Configure Claude Code

Add these environment variables to your Claude Code configuration (`~/.claude.json` or `settings.json` in VS Code):

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    "OTEL_METRIC_EXPORT_INTERVAL": "1000",
    "OTEL_LOGS_EXPORT_INTERVAL": "5000",
    "OTEL_LOG_USER_PROMPTS": "1"
  }
}
```

Or export them in your shell:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_METRIC_EXPORT_INTERVAL=1000
export OTEL_LOGS_EXPORT_INTERVAL=5000
export OTEL_LOG_USER_PROMPTS=1
```

### Step 3: Access the Monitoring Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| **OTEL Metrics** | http://localhost:8889/metrics | N/A |
| **Prometheus** | http://localhost:9090 | N/A |
| **Grafana** | http://localhost:3000 | admin/admin |

---

## Component Deep Dive

### OpenTelemetry Collector

The OpenTelemetry (OTEL) Collector is the central hub that receives, processes, and exports telemetry data.

#### What It Does

- **Receives** telemetry data from Claude Code via OTLP protocol (gRPC on port 4317, HTTP on port 4318)
- **Processes** data through configured pipelines (batching, memory limiting)
- **Exports** metrics in Prometheus format (port 8889)

#### Key Endpoints

| Port | Protocol | Purpose |
|------|----------|---------|
| 4317 | gRPC | OTLP gRPC receiver - Claude Code sends data here |
| 4318 | HTTP | OTLP HTTP receiver - Alternative to gRPC |
| 8889 | HTTP | Prometheus metrics endpoint - Where Prometheus scrapes from |

#### Raw Metrics Endpoint

You can see the raw metrics that Claude Code sends by visiting:
```
http://localhost:8889/metrics
```

This shows metrics in Prometheus exposition format:
```
# HELP claude_code_token_usage_tokens_total 
# TYPE claude_code_token_usage_tokens_total counter
claude_code_token_usage_tokens_total{job="claude-code",model="model_max",type="input",user_id="xxx"} 110
claude_code_token_usage_tokens_total{job="claude-code",model="model_max",type="output",user_id="xxx"} 142
```

### Prometheus

Prometheus is a time-series database that scrapes and stores metrics.

#### What It Does

- **Scrapes** metrics from the OTEL Collector at regular intervals (every 15 seconds by default)
- **Stores** historical metric data
- **Provides** a powerful query language (PromQL) to analyze metrics
- **Supports** alerting rules (optional)

#### Key Features

| Feature | Description |
|---------|-------------|
| Time-series storage | Stores data with timestamps for historical analysis |
| PromQL | Query language for aggregation, filtering, and analysis |
| Service discovery | Automatically discovers targets to scrape |
| Retention | Configured to keep 200 hours (~8 days) of data |

#### Accessing Prometheus

1. Open http://localhost:9090
2. Use the **Graph** tab to run queries
3. Check **Status > Targets** to verify data collection

### Grafana

Grafana is a visualization platform for creating dashboards.

#### What It Does

- **Visualizes** Prometheus data in customizable dashboards
- **Provides** pre-built panels (charts, tables, stats)
- **Supports** alerting and notifications

#### Default Credentials

- Username: `admin`
- Password: `admin`

---

## Configuration Files Explained

### docker-compose.yml

```yaml
services:
  # OpenTelemetry Collector - Receives and exports telemetry data
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC receiver (Claude Code sends data here)
      - "4318:4318"   # OTLP HTTP receiver (alternative to gRPC)
      - "8889:8889"   # Prometheus metrics (scrape endpoint)
    depends_on:
      - prometheus

  # Prometheus - Time-series database for metrics
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"   # Web UI and API
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus  # Persistent storage
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=200h'  # Keep 200 hours of data
      - '--web.enable-lifecycle'              # Enable runtime config reload

  # Grafana - Visualization and dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"   # Web UI
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin  # Default password
    volumes:
      - grafana_data:/var/lib/grafana     # Persistent storage
      - ./grafana/provisioning:/etc/grafana/provisioning  # Auto-provision datasources
      - ./grafana/dashboards:/var/lib/grafana/dashboards  # Pre-built dashboards
    depends_on:
      - prometheus

volumes:
  prometheus_data:    # Persistent Prometheus data
  grafana_data:       # Persistent Grafana data
```

### otel-collector-config.yaml

```yaml
# Receivers - Define how to receive telemetry data
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317  # Listen on all interfaces, port 4317
      http:
        endpoint: 0.0.0.0:4318  # Listen on all interfaces, port 4318

# Processors - Transform data before exporting
processors:
  batch:
    timeout: 1s           # Send batches every 1 second
    send_batch_size: 1024 # Or when 1024 items accumulated
  memory_limiter:
    check_interval: 1s    # Check memory usage every 1 second
    limit_mib: 512        # Limit to 512 MB to prevent OOM

# Exporters - Define where to send processed data
exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"    # Expose metrics on port 8889
    send_timestamps: true       # Include timestamps in metrics
    metric_expiration: 180m     # Remove stale metrics after 180 minutes
    enable_open_metrics: true   # Use OpenMetrics format
    
  debug:
    verbosity: detailed         # Log detailed info for debugging
    sampling_initial: 5         # Log first 5 items
    sampling_thereafter: 200    # Then every 200th item

# Service - Wire together receivers, processors, and exporters
service:
  pipelines:
    metrics:
      receivers: [otlp]                     # Receive via OTLP
      processors: [memory_limiter, batch]   # Process with limits and batching
      exporters: [prometheus, debug]        # Export to Prometheus and debug logs
      
  telemetry:
    logs:
      level: "debug"  # Set to "info" in production
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s      # How often to collect metrics (every 15 seconds)
  evaluation_interval: 15s  # How often to evaluate alerting rules

scrape_configs:
  # Scrape metrics from the OpenTelemetry Collector
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']  # Container hostname:port

  # Scrape Prometheus's own metrics
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

---

## Claude Code Environment Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `CLAUDE_CODE_ENABLE_TELEMETRY` | Enable/disable telemetry collection | `1` (enabled) |
| `OTEL_METRICS_EXPORTER` | Metrics export method | `otlp`, `console`, or `none` |
| `OTEL_LOGS_EXPORTER` | Logs export method | `otlp`, `console`, or `none` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | OTLP protocol to use | `grpc` or `http/protobuf` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Collector endpoint URL | `http://localhost:4317` |
| `OTEL_METRIC_EXPORT_INTERVAL` | How often to export metrics (ms) | `1000` (1 second) |
| `OTEL_LOGS_EXPORT_INTERVAL` | How often to export logs (ms) | `5000` (5 seconds) |
| `OTEL_LOG_USER_PROMPTS` | Include user prompts in logs | `1` (enabled) |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth headers for collector | `Authorization=Bearer token` |

### Export Intervals Explained

- **`OTEL_METRIC_EXPORT_INTERVAL`**: Set to `1000` (1 second) for near real-time updates. For production, use `30000` or `60000` to reduce overhead.
- **`OTEL_LOGS_EXPORT_INTERVAL`**: Set to `5000` (5 seconds) for reasonable log batching.

### Exporter Values

- **`console`**: Outputs to terminal (useful for debugging)
- **`otlp`**: Sends to OTEL Collector (for production monitoring)
- **`none`**: Disabled

---

## Available Metrics

Claude Code exports the following metrics according to the [official monitoring guide](https://github.com/anthropics/claude-code-monitoring-guide/blob/main/claude_code_roi_full.md):

| Metric Name | Description | Unit | Prometheus Name |
|-------------|-------------|------|-----------------|
| `claude_code.session.count` | Count of CLI sessions started | count | `claude_code_session_count_total` |
| `claude_code.lines_of_code.count` | Count of lines of code modified | count | `claude_code_lines_of_code_count_total` |
| `claude_code.pull_request.count` | Number of pull requests created | count | `claude_code_pull_request_count_total` |
| `claude_code.commit.count` | Number of git commits created | count | `claude_code_commit_count_total` |
| `claude_code.cost.usage` | Cost of the Claude Code session | USD | `claude_code_cost_usage_USD_total` |
| `claude_code.token.usage` | Number of tokens used | tokens | `claude_code_token_usage_tokens_total` |
| `claude_code.code_edit_tool.decision` | Count of code editing tool permission decisions | count | `claude_code_code_edit_tool_decision_total` |
| `claude_code.active_time.total` | Total active time in seconds | s | `claude_code_active_time_total_seconds` |

### Metric Labels

Metrics include these labels for filtering and grouping:

| Label | Description | Example |
|-------|-------------|---------|
| `user_id` | Hashed user identifier | `9d5e2d20425102ac6bf66e04353a484242a49a203ff0527e6ec1e0fcfc996fc6` |
| `session_id` | Unique session identifier | `14f70ee9-4f03-4def-a06b-4c1689198192` |
| `model` | AI model used | `claude-4-sonnet`, `model_max` |
| `type` | Token type (for token.usage) | `input`, `output`, `cacheCreation`, `cacheRead` |
| `otel_scope_name` | Instrumentation scope | `com.anthropic.claude_code` |
| `otel_scope_version` | Claude Code version | `2.1.25` |

---

## Verifying Your Setup

### Step 1: Verify Docker Containers

```bash
docker-compose ps
```

Expected output:
```
NAME          IMAGE                                      STATUS
grafana       grafana/grafana:latest                     Up
prometheus    prom/prometheus:latest                     Up
otel-collector otel/opentelemetry-collector-contrib     Up
```

### Step 2: Check OTEL Collector Logs

```bash
docker-compose logs otel-collector
```

Look for:
```
Starting OpenTelemetry Collector...
Everything is ready.
```

### Step 3: Verify OTEL Metrics Endpoint

```bash
curl http://localhost:8889/metrics
```

Before any Claude Code activity, you'll see collector metrics. After Claude Code sessions, you'll see:
```
# HELP claude_code_token_usage_tokens_total
# TYPE claude_code_token_usage_tokens_total counter
claude_code_token_usage_tokens_total{...} 110
```

### Step 4: Check Prometheus Targets

1. Open http://localhost:9090/targets
2. Verify `otel-collector` target shows **UP** status
3. If DOWN, check network connectivity and container logs

### Step 5: Test with Claude Code

```bash
# Quick test with console output to verify Claude Code telemetry
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=console
export OTEL_METRIC_EXPORT_INTERVAL=1000
claude -p "hello world"
```

You should see telemetry output in the console, confirming Claude Code is generating metrics.

### Step 6: Test with OTEL Collector

```bash
# Now send to OTEL Collector
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_METRIC_EXPORT_INTERVAL=1000

claude -p "hello world"
```

Then check:
1. OTEL endpoint: http://localhost:8889/metrics (look for `claude_code_*` metrics)
2. Prometheus: http://localhost:9090 (query `claude_code_token_usage_tokens_total`)

---

## Querying Metrics

### Prometheus Query Interface

1. Open http://localhost:9090
2. Click the **Graph** tab
3. Enter a PromQL query in the **Expression** field
4. Click **Execute**
5. Switch between **Table** and **Graph** views

### Essential PromQL Queries

#### Total Cost

```promql
sum(claude_code_cost_usage_USD_total)
```

#### Cost by Model

```promql
sum by (model)(claude_code_cost_usage_USD_total)
```

#### Token Usage by Type

```promql
sum by (type)(claude_code_token_usage_tokens_total)
```

#### Cost Over Time (Last 24 hours)

```promql
sum(increase(claude_code_cost_usage_USD_total[24h]))
```

#### Token Usage Rate (Per Minute)

```promql
rate(claude_code_token_usage_tokens_total[5m]) * 60
```

#### Active Users

```promql
count(count by (user_id)(claude_code_cost_usage_USD_total))
```

#### Cost by User

```promql
sum by (user_id)(claude_code_cost_usage_USD_total)
```

#### Session Count

```promql
sum(claude_code_session_count_total)
```

#### Lines of Code Modified

```promql
sum(claude_code_lines_of_code_count_total)
```

#### Commits Created

```promql
sum(claude_code_commit_count_total)
```

#### Pull Requests Created

```promql
sum(claude_code_pull_request_count_total)
```

#### Input vs Output Token Ratio

```promql
sum(claude_code_token_usage_tokens_total{type="input"}) 
/ 
sum(claude_code_token_usage_tokens_total{type="output"})
```

#### Cache Efficiency Ratio

```promql
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
sum(claude_code_token_usage_tokens_total{type="cacheCreation"})
```

### PromQL Query Tips

| Operator | Description | Example |
|----------|-------------|---------|
| `sum()` | Aggregate all values | `sum(metric)` |
| `by (label)` | Group by label | `sum by (model)(metric)` |
| `rate()` | Per-second rate | `rate(metric[5m])` |
| `increase()` | Total increase over time | `increase(metric[24h])` |
| `{label="value"}` | Filter by label | `metric{type="input"}` |
| `count()` | Count time series | `count(metric)` |

---

## Using Grafana Dashboards

### Accessing Grafana

1. Open http://localhost:3000
2. Login with `admin` / `admin`
3. Skip password change (or set a new one)

### Finding the Pre-Built Dashboard

1. Click the hamburger menu (☰) in the top left
2. Click **Dashboards**
3. Click the **Claude Code** folder
4. Click **Claude Code - Working Dashboard**

### Dashboard Panels Explained

The pre-built dashboard includes these panels:

| Panel | Description | Query Used |
|-------|-------------|------------|
| **Total Cost** | Total USD spent on Claude Code | `sum(increase(claude_code_cost_usage_USD_total[$__range]))` |
| **Active Users** | Unique users in time range | `count(count by (user_id)(increase(claude_code_cost_usage_USD_total[$__range]) > 0))` |
| **Total Tokens** | Total tokens consumed | `sum(increase(claude_code_token_usage_tokens_total[$__range]))` |
| **Lines of Code** | Total lines modified | `sum(increase(claude_code_lines_of_code_count_total[$__range]))` |
| **Cost by Model** | Pie chart of costs per model | `sum by (model)(increase(claude_code_cost_usage_USD_total[$__range]))` |
| **Token Usage by Type** | Donut chart of token types | `sum by (type)(increase(claude_code_token_usage_tokens_total[$__range]))` |
| **Cost by User** | Table of costs per user | `sum by (user_id)(increase(claude_code_cost_usage_USD_total[$__range]))` |
| **Lines of Code by Type** | Table of LOC by type | `sum by (type)(increase(claude_code_lines_of_code_count_total[$__range]))` |

### Adjusting Time Range

1. Click the time picker in the top right (shows current range like "Last 6 hours")
2. Select a preset range (Last 1 hour, Last 24 hours, etc.)
3. Or set a custom absolute range

### Creating Custom Panels

1. Click the **Add panel** button (+ icon)
2. Click **Add a new panel**
3. Select visualization type (Stat, Graph, Table, etc.)
4. Enter your PromQL query
5. Configure options and click **Apply**

### Adding Prometheus as a Data Source (If Not Pre-Configured)

1. Go to **Configuration > Data sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL to `http://prometheus:9090`
5. Click **Save & test**

---

## Common Use Cases

### Use Case 1: Track Daily Spending

**Goal**: Monitor how much Claude Code costs per day

**Prometheus Query**:
```promql
sum(increase(claude_code_cost_usage_USD_total[24h]))
```

**Grafana Panel**: Stat panel showing current 24h spending

### Use Case 2: Compare Model Usage

**Goal**: See which AI models are being used most

**Prometheus Query**:
```promql
sum by (model)(claude_code_token_usage_tokens_total)
```

**Grafana Panel**: Pie chart with model breakdown

### Use Case 3: Identify Heavy Users

**Goal**: Find users consuming the most tokens/cost

**Prometheus Query**:
```promql
topk(10, sum by (user_id)(claude_code_cost_usage_USD_total))
```

**Grafana Panel**: Table sorted by cost descending

### Use Case 4: Monitor Session Activity

**Goal**: Track active Claude Code sessions

**Prometheus Query**:
```promql
sum(claude_code_session_count_total)
```

### Use Case 5: Calculate Cost per PR

**Goal**: Determine average cost per pull request

**Prometheus Query**:
```promql
sum(claude_code_cost_usage_USD_total) 
/ 
sum(claude_code_pull_request_count_total)
```

### Use Case 6: Analyze Token Efficiency

**Goal**: Check cache hit ratio for cost optimization

**Prometheus Query**:
```promql
sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
/ 
(sum(claude_code_token_usage_tokens_total{type="cacheRead"}) 
 + sum(claude_code_token_usage_tokens_total{type="cacheCreation"}))
```

A higher ratio indicates better cache efficiency.

---

## Troubleshooting

### Problem: No Metrics Appearing

**Symptoms**: `http://localhost:8889/metrics` shows no `claude_code_*` metrics

**Solutions**:

1. **Verify telemetry is enabled**:
   ```bash
   echo $CLAUDE_CODE_ENABLE_TELEMETRY  # Should be "1"
   ```

2. **Check OTEL endpoint is reachable**:
   ```bash
   curl -v http://localhost:4317
   # Should connect (even if no response body)
   ```

3. **Test with console output first**:
   ```bash
   export OTEL_METRICS_EXPORTER=console
   export OTEL_METRIC_EXPORT_INTERVAL=1000
   claude -p "test"
   # Look for metric output in terminal
   ```

4. **Check OTEL Collector logs**:
   ```bash
   docker-compose logs otel-collector | grep -i error
   ```

### Problem: Prometheus Shows "No Data"

**Symptoms**: Queries return empty results in Prometheus

**Solutions**:

1. **Check target status**:
   - Open http://localhost:9090/targets
   - Verify `otel-collector` target is **UP**

2. **Check scrape timing**:
   - Prometheus scrapes every 15 seconds
   - Wait at least 30 seconds after generating metrics

3. **Verify metric exists in OTEL**:
   ```bash
   curl http://localhost:8889/metrics | grep claude_code
   ```

4. **Check Prometheus logs**:
   ```bash
   docker-compose logs prometheus | grep -i error
   ```

### Problem: Grafana Dashboard is Empty

**Symptoms**: Panels show "No data"

**Solutions**:

1. **Check data source connection**:
   - Go to **Configuration > Data sources > Prometheus**
   - Click **Save & test**
   - Should show "Data source is working"

2. **Verify time range**:
   - Metrics may not exist for the selected time range
   - Try "Last 24 hours" or "Last 7 days"

3. **Check panel query**:
   - Edit the panel
   - Run the query directly in Prometheus to verify it returns data

4. **Check datasource UID**:
   - The dashboard uses `uid: "PBFA97CFB590B2093"`
   - May need to update to match your Prometheus datasource UID

### Problem: Claude Code Hangs with Telemetry Enabled

**Symptoms**: Claude Code becomes unresponsive

**Solutions**:

1. **Clean installation**:
   ```bash
   npm uninstall -g @anthropic-ai/claude-code
   npm install -g @anthropic-ai/claude-code
   ```

2. **Clear cache**:
   ```bash
   rm -rf ~/.config/claude-code/
   ```

3. **Check endpoint accessibility**:
   - Ensure OTEL endpoint is reachable
   - Check for firewall blocking port 4317

### Problem: Remote Server Access

**Symptoms**: Can't access metrics from another machine

**Solutions**:

1. **Update endpoint to server IP**:
   ```bash
   export OTEL_EXPORTER_OTLP_ENDPOINT=http://YOUR_SERVER_IP:4317
   ```

2. **Open firewall ports**:
   ```bash
   # Linux (ufw)
   sudo ufw allow 4317/tcp
   sudo ufw allow 9090/tcp
   sudo ufw allow 3000/tcp
   sudo ufw allow 8889/tcp
   ```

3. **Bind to all interfaces**:
   - The default config already binds to `0.0.0.0`
   - Ensure docker isn't restricting access

### Problem: Metrics Disappear After Restart

**Symptoms**: Prometheus data is lost after container restart

**Solutions**:

1. **Check volume mounts**:
   ```bash
   docker volume ls | grep prometheus
   ```

2. **Verify data persistence**:
   - `prometheus_data` volume should persist data
   - Don't use `docker-compose down -v` (removes volumes)

3. **Use proper shutdown**:
   ```bash
   docker-compose stop   # Preserves volumes
   docker-compose start
   ```

---

## Additional Resources

- [Official Claude Code Monitoring Guide](https://github.com/anthropics/claude-code-monitoring-guide/blob/main/claude_code_roi_full.md)
- [OpenTelemetry Collector Documentation](https://opentelemetry.io/docs/collector/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)

---

## Summary

### Key Endpoints to Remember

| Service | URL | Purpose |
|---------|-----|---------|
| OTEL Receiver | `http://localhost:4317` | Claude Code sends data here (gRPC) |
| OTEL Metrics | `http://localhost:8889/metrics` | Raw Prometheus-format metrics |
| Prometheus | `http://localhost:9090` | Query interface and targets |
| Prometheus Targets | `http://localhost:9090/targets` | Verify scraping is working |
| Grafana | `http://localhost:3000` | Visualization dashboards |

### Quick Verification Checklist

1. ✅ All Docker containers running (`docker-compose ps`)
2. ✅ OTEL Collector accepting connections (port 4317)
3. ✅ Metrics visible at http://localhost:8889/metrics
4. ✅ Prometheus target is UP at http://localhost:9090/targets
5. ✅ Queries return data in Prometheus
6. ✅ Grafana dashboard shows metrics

### Environment Variables Quick Reference

```bash
# Essential
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Optional tuning
export OTEL_METRIC_EXPORT_INTERVAL=1000
export OTEL_LOGS_EXPORTER=otlp
export OTEL_LOGS_EXPORT_INTERVAL=5000
export OTEL_LOG_USER_PROMPTS=1
```
