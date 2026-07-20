---
title: Umubyeyi Generator API
emoji: "🌿"
colorFrom: purple
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: CPU inference for Umubyeyi's fine-tuned BLOOMZ generator
---

# Umubyeyi fine-tuned generator

Docker/FastAPI service for the project's English ESConv LoRA adapter on the
public `bigscience/bloomz-560m` base model. The service is CPU-only, loads one
model instance, permits one generation at a time, and exposes `GET /health`
and `POST /generate`.

Request example:

```json
{"message":"I feel overwhelmed","language":"en","history":[]}
```
