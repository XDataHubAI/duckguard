# Notifications

Send alerts to Slack, Teams, or Email when data quality checks fail.

## Quick Start

```python
from duckguard import connect
from duckguard.notifications import SlackNotifier

data = connect("orders.csv")
result = data.amount.between(0, 10000)

if not result:
    slack = SlackNotifier(webhook_url="https://hooks.slack.com/services/...")
    slack.send_failure_alert(result)
```

## Slack

### Setup

1. Create a Slack Incoming Webhook at [api.slack.com/messaging/webhooks](https://api.slack.com/messaging/webhooks)
2. Copy the webhook URL

### Usage

```python
from duckguard.notifications import SlackNotifier

slack = SlackNotifier(
    webhook_url="https://hooks.slack.com/services/T00/B00/xxx"
)

# Send alert on failure
if not result:
    slack.send_failure_alert(result)

# Send quality score
score = data.score()
slack.send_score_alert(score)
```

### Environment Variable

```bash
export DUCKGUARD_SLACK_WEBHOOK="https://hooks.slack.com/services/..."
```

```python
import os
slack = SlackNotifier(webhook_url=os.environ["DUCKGUARD_SLACK_WEBHOOK"])
```

## Microsoft Teams

### Setup

1. Create an Incoming Webhook connector in your Teams channel
2. Copy the webhook URL

### Usage

```python
from duckguard.notifications import TeamsNotifier

teams = TeamsNotifier(
    webhook_url="https://outlook.office.com/webhook/..."
)

if not result:
    teams.send_failure_alert(result)
```

## Email

### Usage

```python
from duckguard.notifications import EmailNotifier

email = EmailNotifier(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="alerts@company.com",
    password="app-password",
    from_addr="alerts@company.com",
    to_addrs=["team@company.com"],
)

if not result:
    email.send_failure_alert(result)
```

### Environment Variables

```bash
export DUCKGUARD_SMTP_HOST="smtp.gmail.com"
export DUCKGUARD_SMTP_PORT="587"
export DUCKGUARD_SMTP_USER="alerts@company.com"
export DUCKGUARD_SMTP_PASS="app-password"
```

## Pipeline Pattern

```python
from duckguard import connect, load_rules, execute_rules
from duckguard.notifications import SlackNotifier

# Run checks
data = connect("s3://datalake/orders.parquet")
rules = load_rules("duckguard.yaml")
result = execute_rules(rules, dataset=data)

# Notify on failure
if not result.passed:
    slack = SlackNotifier(webhook_url=os.environ["SLACK_WEBHOOK"])
    slack.send_failure_alert(result)
    raise SystemExit(1)
```

## Airflow Integration

```python
def validate_and_notify():
    from duckguard import connect
    from duckguard.notifications import SlackNotifier

    data = connect("s3://lake/orders.parquet")
    result = data.order_id.null_percent == 0

    if not result:
        slack = SlackNotifier(webhook_url=os.environ["SLACK_WEBHOOK"])
        slack.send_failure_alert(result)
        raise ValueError("Quality check failed")
```

## Alert Content

Alerts include:

- Check name and status (PASS/FAIL)
- Actual vs expected values
- Failure count and sample
- Data source and timestamp
- Quality score (if available)

## Custom Notifications

Build your own notifier by posting to any webhook:

```python
import requests

def send_custom_alert(result, webhook_url):
    payload = {
        "text": f"DuckGuard: {result.message}",
        "passed": result.passed,
        "failures": result.total_failures,
    }
    requests.post(webhook_url, json=payload)
```
