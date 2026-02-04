# Claude Code Troubleshooting Guide

Quick solutions for common Claude Code issues related to telemetry and ROI measurement.

## Telemetry Issues

### Telemetry Not Working

**Problem**: Metrics not appearing in Prometheus/Grafana after setup.

**Solutions**:
1. Verify telemetry is enabled:
   ```bash
   export CLAUDE_CODE_ENABLE_TELEMETRY=1
   ```

2. Test with console output first:
   ```bash
   export OTEL_METRICS_EXPORTER=console
   export OTEL_METRIC_EXPORT_INTERVAL=1000
   claude -p "test"
   ```
   You should see metric output in the console.

3. Check your OTLP endpoint is accessible:
   ```bash
   curl -v http://localhost:4317
   ```

4. Verify all required environment variables:
   ```bash
   echo $CLAUDE_CODE_ENABLE_TELEMETRY  # Should be 1
   echo $OTEL_METRICS_EXPORTER          # Should be otlp
   echo $OTEL_EXPORTER_OTLP_ENDPOINT    # Should be your collector endpoint
   ```

### Claude Code Hanging After Enabling Telemetry

**Problem**: Claude Code becomes unresponsive after enabling telemetry.

**Solutions**:
1. Try a clean installation:
   ```bash
   npm uninstall -g @anthropic-ai/claude-code
   npm install -g @anthropic-ai/claude-code
   ```

2. Clear Claude Code cache and config:
   ```bash
   rm -rf ~/.config/claude-code/
   ```

3. Restart Claude Code with fresh configuration

## Installation Issues

### Permission Errors on Linux

**Problem**: `npm install -g` fails with permission errors.

**Solution**: Create a user-writable npm prefix:
```bash
# Save existing global packages
npm list -g --depth=0 > ~/npm-global-packages.txt

# Create user directory for npm
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global

# Add to PATH (use ~/.zshrc for zsh)
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Install Claude Code
npm install -g @anthropic-ai/claude-code
```

### Auto-Update Failures

**Problem**: Claude Code can't update automatically.

**Solutions**:
1. Follow the npm permission fix above
2. Or disable auto-updater:
   ```bash
   export DISABLE_AUTOUPDATER=1
   ```

## Authentication Issues

**Problem**: Repeated authentication prompts or login failures.

**Solutions**:
1. Force a clean logout and login:
   ```bash
   claude /logout
   # Close terminal
   # Open new terminal
   claude
   ```

2. If issues persist, clear auth data:
   ```bash
   rm -rf ~/.config/claude-code/auth.json
   claude
   ```

## Performance Issues

### High Memory Usage with Large Codebases

**Problem**: Claude Code consumes excessive resources.

**Solutions**:
1. Use `/compact` regularly to reduce context size
2. Close and restart between major tasks
3. Add build directories to `.gitignore`:
   ```gitignore
   node_modules/
   dist/
   build/
   .next/
   ```

### Commands Hanging or Freezing

**Problem**: Claude Code becomes unresponsive during operations.

**Solutions**:
1. Press `Ctrl+C` to cancel current operation
2. If unresponsive, close terminal and restart
3. For JetBrains IDEs (IntelliJ, PyCharm):
   - Go to Settings → Tools → Terminal
   - Click "Configure terminal keybindings"
   - Remove "Switch focus to Editor" shortcut
   - This fixes ESC key not working

## Common Metric Collection Issues

### No Metrics in Prometheus

**Problem**: Prometheus shows no data despite telemetry being enabled.

**Solutions**:
1. Check docker containers are running:
   ```bash
   docker-compose ps
   ```

2. Verify Prometheus can reach the OTEL collector:
   ```bash
   curl http://localhost:8888/metrics
   ```

3. Check for firewall issues blocking port 4317

### Incorrect Cost Calculations

**Problem**: Cost metrics don't match expected values.

**Note**: Cost metrics are approximations. For official billing:
- Anthropic API users: Check Anthropic Console
- AWS users: Check AWS Cost Explorer
- Google Cloud users: Check GCP Billing

### Token Usage Shows Zero in Session JSONL Files

**Problem**: When using a custom `ANTHROPIC_BASE_URL` (proxy or custom endpoint), the session JSONL files at `~/.claude/projects/<session>.jsonl` show zero for all token counts:

```json
"usage":{"input_tokens":0,"output_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0}
```

**Cause**: This typically occurs when using a custom API endpoint or proxy that doesn't return the `usage` field in the API response, or returns it in a different format than the official Anthropic API. Claude Code relies on the API response to populate these values in the local session logs.

Common configurations that may cause this:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://your-proxy-server:port",
    "ANTHROPIC_AUTH_TOKEN": "your-token"
  }
}
```

**Solutions**:

1. **Check your proxy/endpoint is returning usage data**: The custom endpoint should return the `usage` object in API responses with the standard Anthropic format:
   ```json
   {
     "usage": {
       "input_tokens": 150,
       "output_tokens": 200,
       "cache_creation_input_tokens": 0,
       "cache_read_input_tokens": 0
     }
   }
   ```

2. **Use OTEL metrics instead**: Even if session JSONL files show zeros, OpenTelemetry metrics can still track token usage accurately. Configure OTEL to collect metrics:
   ```json
   {
     "env": {
       "ANTHROPIC_BASE_URL": "http://your-proxy-server:port",
       "ANTHROPIC_AUTH_TOKEN": "your-token",
       "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
       "OTEL_METRICS_EXPORTER": "otlp",
       "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
       "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
     }
   }
   ```
   
   Then query token usage from Prometheus:
   ```promql
   sum by (type)(claude_code_token_usage_tokens_total)
   ```

3. **Verify with console output**: Test if telemetry captures token data even when session JSONL doesn't:
   ```bash
   export CLAUDE_CODE_ENABLE_TELEMETRY=1
   export OTEL_METRICS_EXPORTER=console
   export OTEL_METRIC_EXPORT_INTERVAL=1000
   claude -p "test"
   ```
   
   Look for `claude_code.token.usage` metrics in the output.

4. **Contact your proxy provider**: If using a third-party proxy service, ensure it passes through the usage information from the upstream API responses.

**Note**: The session JSONL files are local logs that depend on API response content. OTEL metrics are often more reliable for tracking usage when using custom endpoints, as they can be instrumented independently of the API response format.

## Getting Help

If these solutions don't resolve your issue:

1. Run diagnostics:
   ```bash
   claude /doctor
   ```

2. Report bugs:
   ```bash
   claude /bug
   ```

3. Check the official documentation:
   - [Claude Code Troubleshooting](https://docs.anthropic.com/en/docs/claude-code/troubleshooting)
   - [Claude Code GitHub Issues](https://github.com/anthropics/claude-code/issues)

4. For telemetry-specific issues:
   - Review your OTEL collector logs
   - Check Prometheus targets at http://localhost:9090/targets
   - Verify your organization's firewall rules