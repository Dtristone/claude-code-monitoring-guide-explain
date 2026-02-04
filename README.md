# Claude Code ROI Measurement Guide

A comprehensive guide to measuring the return on investment for Claude Code implementation in your development organization.

## Overview

This repository contains a complete walkthrough for setting up telemetry, measuring costs, tracking productivity, and calculating ROI for Claude Code usage. Whether you're an individual developer or managing a large engineering team, this guide provides the tools and metrics needed to make data-driven decisions about AI coding assistance.

> 📘 **New to the monitoring stack?** Start with the [**Comprehensive Usage Guide**](USAGE-GUIDE.md) for detailed explanations of how to configure OTEL Collector, Prometheus, and Grafana, including step-by-step verification and troubleshooting.

## What's Included

- **Telemetry Setup**: Complete Prometheus and OpenTelemetry configuration
- **Cost Analysis**: Real usage patterns and pricing breakdowns across different plans
- **Productivity Metrics**: Key indicators for measuring developer efficiency
- **ROI Calculations**: Framework for calculating return on investment
- **Automated Reporting**: Integration with Linear for comprehensive productivity reports

## Key Metrics Tracked

- **Cost Metrics**: Total spend, cost per session, cost by model, cache cost savings
- **Token Usage**: Input/output tokens, cache efficiency
- **Prefix Cache Statistics**: Cache hit ratio, cache efficiency %, cache ROI, cost savings from cache
- **Productivity**: PR count, commit frequency, session duration
- **Team Analytics**: Usage by developer, adoption rates

## Prefix Cache Monitoring

> 🚀 **New!** Comprehensive prefix cache statistics similar to vLLM monitoring examples

Track and optimize your Claude Code prefix cache performance with detailed metrics:

- **Cache Cost Savings**: See exactly how much money you're saving through cache reuse
- **Cache Efficiency**: Monitor what percentage of context is served from cache
- **Cache ROI**: Measure return on investment (tokens read per token cached)
- **Model Comparison**: Compare cache performance across different models
- **Real-time Tracking**: Dashboard panels showing cache trends over time

**Typical cache efficiency**: 80-95% hit ratio with 20:1 to 50:1 read:creation ratios can save significant costs on long development sessions.

📖 See the **[Prefix Cache Monitoring Guide](PREFIX-CACHE-GUIDE.md)** for detailed explanations, optimization strategies, and real-world examples.

## Contents

- [`USAGE-GUIDE.md`](USAGE-GUIDE.md) - **Comprehensive usage guide** explaining how to configure, use, and troubleshoot the monitoring stack (OTEL Collector, Prometheus, Grafana)
- [`PREFIX-CACHE-GUIDE.md`](PREFIX-CACHE-GUIDE.md) - **Prefix cache monitoring guide** with detailed explanations of cache metrics, optimization strategies, and real-world examples
- [`FAQ-METRICS-AND-TRACES.md`](FAQ-METRICS-AND-TRACES.md) - **FAQ** answering common questions about metrics, traces, and statistics (token usage, cache hit ratio, session traces, **zero tokens with custom endpoints**)
- [`claude_code_roi_full.md`](claude_code_roi_full.md) - Complete implementation guide
- [`docker-compose.yml`](docker-compose.yml), [`prometheus.yml`](prometheus.yml), [`otel-collector-config.yaml`](otel-collector-config.yaml) - Docker Compose and metrics collection setup
- [`sample-report-output.md`](sample-report-output.md) - Example automated reports
- [`report-generation-prompt.md`](report-generation-prompt.md) - Prompt template for generating productivity reports
- [`troubleshooting.md`](troubleshooting.md) - Quick solutions for common issues (including **zero token usage with custom ANTHROPIC_BASE_URL**)

## Getting Started

### Quick Setup

1. **Start the monitoring stack:**
   ```bash
   git clone https://github.com/Dtristone/claude-code-monitoring-guide-explain.git
   cd claude-code-monitoring-guide-explain
   docker-compose up -d
   ```

2. **Configure Claude Code** (add to your `~/.claude.json` or VS Code settings):
   ```json
   {
     "env": {
       "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
       "OTEL_METRICS_EXPORTER": "otlp",
       "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
       "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
     }
   }
   ```

3. **Access the dashboards:**
   - **Prometheus**: http://localhost:9090
   - **Grafana**: http://localhost:3000 (admin/admin)
   - **Raw Metrics**: http://localhost:8889/metrics

### Documentation

- **[USAGE-GUIDE.md](USAGE-GUIDE.md)** - Complete guide on configuring and using OTEL Collector, Prometheus, and Grafana
- **[PREFIX-CACHE-GUIDE.md](PREFIX-CACHE-GUIDE.md)** - In-depth guide to monitoring prefix cache performance and optimizing cost savings
- **[FAQ-METRICS-AND-TRACES.md](FAQ-METRICS-AND-TRACES.md)** - Frequently asked questions about metrics and traces
- **[claude_code_roi_full.md](claude_code_roi_full.md)** - ROI measurement strategies and advanced queries
- **[troubleshooting.md](troubleshooting.md)** - Solutions for common issues

## Contributing

This guide is based on real-world implementation experience. If you have additional insights or improvements, please feel free to create an issue / PR.

This guide was written by [Kashyap Coimbatore Murali](https://www.linkedin.com/in/kashyap-murali/)
