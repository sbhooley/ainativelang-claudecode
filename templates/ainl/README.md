# AINL Template Library

Pre-built AINL workflow templates for common use cases.

## Available Templates

### 1. API Endpoint (`api_endpoint.ainl`)
Creates a REST API endpoint that fetches and processes data.

**Use when:**
- Building API services
- Creating data fetch endpoints
- Need authenticated API calls

**Frame variables:**
- `api_key`: Authentication token
- `base_url`: API base URL

### 2. Monitor Workflow (`monitor_workflow.ainl`)
Checks a service health endpoint and alerts if unhealthy.

**Use when:**
- Monitoring service health
- Need recurring checks
- Want automated alerts

**Frame variables:**
- `health_url`: Health check endpoint
- `alert_webhook`: Where to send alerts

**Schedule:** Every 5 minutes (`*/5 * * * *`)

### 3. Data Pipeline (`data_pipeline.ainl`)
ETL workflow: Extract from API, Transform, Load to warehouse.

**Use when:**
- Building data pipelines
- Daily data exports
- Need scheduled ETL

**Frame variables:**
- `source_api`: Data source URL
- `warehouse_url`: Data warehouse URL
- `api_key`: API authentication

**Schedule:** Daily at 2 AM (`0 2 * * *`)

### 4. Blockchain Monitor (`blockchain_monitor.ainl`)
Monitors Solana wallet balance and alerts if below threshold.

**Use when:**
- Monitoring crypto wallets
- Need balance alerts
- Working with Solana

**Frame variables:**
- `wallet_address`: Solana wallet address
- `threshold_sol`: Alert threshold in SOL
- `alert_webhook`: Where to send alerts

**Schedule:** Hourly (`0 * * * *`)

### 5. LLM Workflow (`llm_workflow.ainl`)
AI-powered content moderation workflow.

**Use when:**
- Content moderation
- AI classification tasks
- Need LLM in workflows

**Frame variables:**
- `content`: Content to moderate
- `webhook_url`: Where to send flags

**Requirements:** AINL_CONFIG with LLM provider setup

### 6. Multi-Step Automation (`multi_step_automation.ainl`)
Approval workflow with conditional logic.

**Use when:**
- Multi-step processes
- Approval workflows
- Conditional automation

**Frame variables:**
- `request_id`: Request to process
- `api_base_url`: API base URL
- `approval_webhook`: Manual approval URL

## Using Templates

### Method 1: Copy and Customize

```bash
# Copy template
cp templates/ainl/monitor_workflow.ainl my_monitor.ainl

# Edit frame variables and logic
nano my_monitor.ainl

# Validate
ainl validate my_monitor.ainl --strict

# Run
ainl run my_monitor.ainl --frame '{"health_url":"https://api.example.com/health","alert_webhook":"https://hooks.slack.com/..."}'
```

### Method 2: Ask Claude

```
"Create a health monitor based on the monitor_workflow.ainl template for https://api.example.com/health"
```

Claude will customize the template for your use case.

## Template Structure

All templates follow this structure:

```ainl
# Title and description
# Frame variable declarations (# frame: name: type)

workflow_name [@cron "schedule" | @api "/path"]:
  in: parameters
  
  # Steps
  result = adapter.operation args
  
  # Conditional logic (if needed)
  if condition:
    # then branch
  
  # Output
  out {result: value}
```

## Frame Variables

Templates use **frame variables** for configuration. These are passed at runtime:

```javascript
// In ainl_run MCP call
{
  source: "...",
  frame: {
    api_key: "sk-...",
    webhook_url: "https://...",
    threshold: 100
  }
}
```

Declare frame variables in comments:
```ainl
# frame: api_key: string
# frame: threshold: number
```

## Adapters Used

Templates use these adapters (enable in `ainl_run`):

- **http**: `api_endpoint.ainl`, `monitor_workflow.ainl`, `data_pipeline.ainl`, `multi_step_automation.ainl`
- **solana**: `blockchain_monitor.ainl`
- **llm**: `llm_workflow.ainl` (requires config)
- **core**: All templates (always available)

Example `ainl_run` call:

```javascript
ainl_run({
  source: "...",
  frame: {...},
  adapters: {
    enable: ["http"],
    http: {
      allow_hosts: ["api.example.com"],
      timeout_s: 30
    }
  }
})
```

## Best Practices

1. **Always validate first**: `ainl validate template.ainl --strict`
2. **Test with sample data**: Use `ainl_run` with test frame variables
3. **Start simple**: Copy a template, test it, then customize
4. **Use frame hints**: Add `# frame:` comments for all variables
5. **Set timeouts**: Specify timeout for HTTP calls (3rd argument)
6. **Handle errors**: Use `if` conditions to check for failures

## Token Savings

Using these templates for recurring tasks:

| Template | Traditional (Python) | AINL | Savings |
|----------|---------------------|------|---------|
| Monitor (hourly) | 12,000 tokens/day | 120 tokens/day | 99% |
| Pipeline (daily) | 500 tokens/run | 5 tokens/run | 99% |
| API endpoint | 300 tokens/call | 5 tokens/call | 98% |

**Compile once, run many times** = massive token savings!

## Contributing

To add a new template:

1. Create `.ainl` file following the structure
2. Add frame variable comments
3. Test with `ainl validate` and `ainl run`
4. Document in this README
5. Submit PR

## Resources

- **AINL Language Guide**: `../docs/AINL_LANGUAGE_GUIDE.md`
- **MCP Tools**: Use `ainl_capabilities` to see available adapters
- **AINL Spec**: https://ainativelang.com/docs
