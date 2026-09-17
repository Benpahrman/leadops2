# 🔔 LeadOps Multi-Channel Notification Engine

The `agents/notifications/` package provides centralized, real-time telemetry, mission-control alerts, and operational event reporting across Discord Webhooks and Telegram Bot APIs in strict compliance with [ADR-0002](file:///c:/Users/ben/Documents/leadops2/docs/adr/ADR-0002-strangler-fig-modularization-protocol.md).

---

## 🏛️ Architecture & Routing Topology

```mermaid
flowchart TD
    subgraph Triggering_Services ["Triggering Swarm Services"]
        WF["agents.swarm.workflow"]
        Pitcher["agents.pitcher"]
        Portal["agents.routes.portal"]
        Admin["agents.routes.admin.*"]
        Deliverability["agents.email.deliverability_suite"]
    end

    subgraph Notification_Engine ["agents/notifications/"]
        Facade["__init__.py\nnotification_manager Singleton"]
        Mgr["manager.py\nNotificationManager"]
        Settings["settings.py\nNotificationSettings"]
        Discord["discord.py\nDiscordNotifier"]
        Telegram["telegram.py\nTelegramNotifier"]
    end

    subgraph Endpoints ["Outbound Channels"]
        D_Outreach["Discord: #outreach"]
        D_Inbox["Discord: #inbox"]
        D_Revenue["Discord: #revenue"]
        D_Dev["Discord: #dev-swarm"]
        D_Alerts["Discord: #mission-control"]
        TG_Bot["Telegram Bot: Private / Group Channel"]
    end

    Triggering_Services --> Facade
    Facade --> Mgr
    Mgr --> Settings
    Mgr --> Discord
    Mgr --> Telegram

    Discord --> D_Outreach & D_Inbox & D_Revenue & D_Dev & D_Alerts
    Telegram --> TG_Bot
```

---

## 📦 Domain Modules

| Module | Responsibility | Key Classes / Functions |
|---|---|---|
| [`settings.py`](file:///c:/Users/ben/Documents/leadops2/agents/notifications/settings.py) | Environment resolution & timeout configurations | `NotificationSettings.from_env()` |
| [`discord.py`](file:///c:/Users/ben/Documents/leadops2/agents/notifications/discord.py) | Rich embeds formatting, color palettes, and webhook POSTs | `DiscordNotifier.send_embed()` |
| [`telegram.py`](file:///c:/Users/ben/Documents/leadops2/agents/notifications/telegram.py) | HTML/Markdown chat alerts and Bot API delivery | `TelegramNotifier.send_message()` |
| [`manager.py`](file:///c:/Users/ben/Documents/leadops2/agents/notifications/manager.py) | Event payload construction, thread dispatching, and error isolation | `NotificationManager` methods |
| [`__init__.py`](file:///c:/Users/ben/Documents/leadops2/agents/notifications/__init__.py) | Backward-compatible facade and global singleton export | `notification_manager` |

---

## ⚡ Operational Rules & Safety

1. **Non-Blocking Execution**: All notifications dispatch on dedicated daemon threads (`threading.Thread(daemon=True)`) to ensure API request handlers and scraper workers are never blocked by slow webhook responses.
2. **Strict Test Environment Isolation**: When `PYTEST_CURRENT_TEST` or `MOCK_NOTIFICATIONS=true` is detected, external HTTP dispatches are safely bypassed unless `force_dispatch_in_test=True` is explicitly requested by integration fixtures.
3. **Channel-Specific Webhooks**: The manager automatically routes alerts to dedicated Discord channels (`outreach`, `inbox`, `revenue`, `dev`, `alerts`) based on event classification.
