# Gateway Modularization Requirements

Goal: keep the Weixin platform entry stable and move business-specific behavior into router and bridge layers.

Target structure:

- `gateway/platforms/weixin.py`: receive, normalize, route, and send messages only
- `gateway/router.py`: route messages to business bridges with clear priority
- `gateway/bridges/express_bridge.py`: express query integration migrated from the Weixin entry
- `gateway/bridges/train_bridge.py`: train-ticket bridge with the same interface
- `gateway/bridges/reminder_bridge.py`: reminder bridge with the same interface
- `gateway/bridges/chat_bridge.py`: fallback chat bridge

Bridge interface:

```python
async def handle(user_id: str, message: str) -> str:
    ...
```

Troubleshooting order to document in code or docs:

entry layer -> router layer -> bridge layer -> business layer
