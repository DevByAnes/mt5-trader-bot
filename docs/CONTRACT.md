# Aurum bridge contract v1.0.0

Normative sources: schema/openapi.yaml (JSON syntax is valid YAML 1.2), schema/events.json and schema/settings.schema.json. Generated TypeScript must never be edited manually. Fixtures contain simulated, reusable examples, not market evidence or profitability claims.

## Boundary and authentication

Dashboard → Python → EA only. EA owns order sizing, risk calculations, execution, trade-day boundaries and all displayed risk capacity. Python validates inputs, handles HMAC signing and forwards restricted management commands. No HMAC material enters JS. Use loopback only, bearer session token held in memory, trusted-origin validation and constant-time token checks. Development MSW bypasses authentication intentionally. The current Rust token command has no backend handshake: native production integration is NOT complete.

## Transport guarantees

All responses, including errors, use {data,error,server_time_utc,api_version}; error responses have data:null. UTC timestamps use RFC3339 with Z. Null means Unavailable, never zero. Protocol version is exactly 1.0.0. Errors are typed by Error.code; field is optional. No hidden browser fallback or direct MT5 connection.

REST timeout is 5 seconds. Accepted mutations return HTTP 202 with PENDING, not success. Poll GET /requests/{id} every 300ms for up to 10 seconds; TIMEOUT means outcome unknown. APPLIED requires an EA-origin acknowledgement timestamp. If transport fails after dispatch, retain the request/key and reconcile rather than resubmit blindly. Acknowledgement retention and idempotency retention must be at least 24 hours (ASSUMPTION, backend to confirm).

Idempotency-Key is a UUID, scoped to session/operator and endpoint. Same key and canonical payload returns the original request ID and result without a second EA action; changed payload returns 409 IDEMPOTENCY_CONFLICT. Requests that fail validation or version checks are not accepted. Disable mutation retries in Query. Concurrent settings applications must atomically compare base_version; reserve the version until the EA result is resolved.

Lists expose items and next_cursor (null at end), stable newest-first ordering, opaque cursors and limit 1–100, default 50. Never infer daily aggregates from one page. Positions are a complete current snapshot. Chart candles are UTC epoch seconds, ascending and unique; all Entry/SL/TP overlays come from backend. Telemetry contains server-produced history samples.

## Settings workflow

CLEAN → DIRTY → VALIDATING → REVIEWING_DIFF or CONFIRMING_LOOSEN → SUBMITTING → AWAITING_ACK → APPLIED / REJECTED / TIMEOUT. Reviewed values and base version are immutable until discard. MT5-only fields remain visible and unchanged; Python must enforce locks independently of the UI. Schema metadata alone determines numeric strictness; NONE means no numeric risk ordering. LIVE requires all server prerequisites and MT5 opt-in. COLD acceptance and actual effective time must be distinguished by backend; APPLIED must mean actual EA application, never merely scheduled.

Rollback endpoint returns a proposal only. It never changes current settings. Validate and apply that proposal with current base_version and a fresh idempotency key through exactly the same second-confirmation/Ack flow. Audit rows include the previous settings snapshot.

## Endpoints

### GET /status

Purpose: getStatus. Return or operate on the named bridge resource.

Response HTTP 200:

```json
{
  "data": {
    "backend": {
      "state": "healthy",
      "heartbeat_utc": "2026-11-02T10:00:00Z",
      "latency_ms": 12
    },
    "ea": {
      "state": "healthy",
      "heartbeat_utc": "2026-11-02T10:00:00Z",
      "latency_ms": 28
    },
    "mt5": {
      "state": "healthy",
      "heartbeat_utc": "2026-11-02T10:00:00Z",
      "latency_ms": 41
    },
    "broker_offset_minutes": 120
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /ea/state

Purpose: getEaState. Return or operate on the named bridge resource.

Response HTTP 200:

```json
{
  "data": {
    "mode": "PAPER",
    "equity": 10042.16,
    "pnl_today": 42.16,
    "risk_active": true,
    "risk_reason": null,
    "session": "London / New York",
    "trend_h1": "Bullish",
    "trend_h4": "Neutral",
    "h1_strength": 72,
    "h4_strength": 48,
    "atr": 18.4,
    "spread": 21,
    "trades_today": 2,
    "last_rejection": "SPREAD_LIMIT · 41 > 35",
    "live_prerequisites": [
      {
        "key": "demo",
        "ok": true,
        "reason": "Demo evidence reviewed"
      },
      {
        "key": "forward",
        "ok": true,
        "reason": "Forward evidence reviewed"
      },
      {
        "key": "real_account_opt_in",
        "ok": false,
        "reason": "MT5 permission disabled"
      }
    ]
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /positions

Purpose: getPositions. Return or operate on the named bridge resource.

Response HTTP 200:

```json
{
  "data": [
    {
      "id": "XAU-1042",
      "side": "BUY",
      "entry": 2688.4,
      "sl": 2679.1,
      "tp": 2707,
      "lot": 0.12,
      "r": 0.74,
      "status": "OPEN",
      "risk_free": false,
      "time_exit_utc": null
    }
  ],
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /signals

Purpose: getSignals. Return or operate on the named bridge resource.

Parameters: cursor (query); limit (query).

Response HTTP 200:

```json
{
  "data": {
    "items": [
      {
        "id": "sig-31",
        "time_utc": "2026-11-02T10:00:00Z",
        "decision": "WAIT",
        "reasons": [
          "Spread above configured limit"
        ],
        "price": 2691.2,
        "reason_code": "SPREAD_LIMIT",
        "actual": 41,
        "limit": 35
      },
      {
        "id": "sig-30",
        "time_utc": "2026-11-02T10:00:00Z",
        "decision": "BUY",
        "reasons": [
          "H1 trend confirmed"
        ],
        "price": 2688.4,
        "reason_code": null,
        "actual": null,
        "limit": null
      }
    ],
    "next_cursor": null,
    "rejection_counts": [
      {
        "code": "SPREAD_LIMIT",
        "count": 3
      },
      {
        "code": "SESSION_FILTER",
        "count": 1
      }
    ]
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /chart

Purpose: getChart. Return or operate on the named bridge resource.

Response HTTP 200:

```json
{
  "data": {
    "candles": [
      {
        "time": 1793613600,
        "open": 2680,
        "high": 2684,
        "low": 2677,
        "close": 2680
      },
      {
        "time": 1793614500,
        "open": 2681.6560968006224,
        "high": 2685.6560968006224,
        "low": 2678.6560968006224,
        "close": 2683.3390387702384
      },
      {
        "time": 1793615400,
        "open": 2683.2888475110544,
        "high": 2687.2888475110544,
        "low": 2680.2888475110544,
        "close": 2685.107442364706
      },
      {
        "time": 1793616300,
        "open": 2684.8752703490327,
        "high": 2688.8752703490327,
        "low": 2681.8752703490327,
        "close": 2685.1575103651526
      },
      {
        "time": 1793617200,
        "open": 2686.39310646325,
        "high": 2690.39310646325,
        "low": 2683.39310646325,
        "close": 2684.8795014726343
      },
      {
        "time": 1793618100,
        "open": 2687.821167275286,
        "high": 2691.821167275286,
        "low": 2684.821167275286,
        "close": 2685.9033187259597
      },
      {
        "time": 1793619000,
        "open": 2689.13966512028,
        "high": 2693.13966512028,
        "low": 2686.13966512028,
        "close": 2688.580834123882
      },
      {
        "time": 1793619900,
        "open": 2690.330522026832,
        "high": 2694.330522026832,
        "low": 2687.330522026832,
        "close": 2691.6444952242696
      },
      {
        "time": 1793620800,
        "open": 2691.377651817695,
        "high": 2695.377651817695,
        "low": 2688.377651817695,
        "close": 2693.356368310942
      },
      {
        "time": 1793621700,
        "open": 2692.267211129189,
        "high": 2696.267211129189,
        "low": 2689.267211129189,
        "close": 2693.0914480996726
      },
      {
        "time": 1793622600,
        "open": 2692.987815432267,
        "high": 2696.987815432267,
        "low": 2689.987815432267,
        "close": 2691.899773210488
      },
      {
        "time": 1793623500,
        "open": 2693.530716684278,
        "high": 2697.530716684278,
        "low": 2690.530716684278,
        "close": 2691.530736271177
      },
      {
        "time": 1793624400,
        "open": 2693.8899398392487,
        "high": 2697.8899398392487,
        "low": 2690.8899398392487,
        "close": 2692.8167940032477
      },
      {
        "time": 1793625300,
        "open": 2694.062376086478,
        "high": 2698.062376086478,
        "low": 2691.062376086478,
        "close": 2694.902710160131
      },
      {
        "time": 1793626200,
        "open": 2694.047831362487,
        "high": 2698.047831362487,
        "low": 2691.047831362487,
        "close": 2696.029046073877
      },
      {
        "time": 1793627100,
        "open": 2693.8490293793166,
        "high": 2697.8490293793166,
        "low": 2690.8490293793166,
        "close": 2695.1496050596306
      },
      {
        "time": 1793628000,
        "open": 2693.471569121908,
        "high": 2697.471569121908,
        "low": 2690.471569121908,
        "close": 2692.895762488578
      },
      {
        "time": 1793628900,
        "open": 2692.923837477821,
        "high": 2696.923837477821,
        "low": 2689.923837477821,
        "close": 2691.001042494062
      },
      {
        "time": 1793629800,
        "open": 2692.2168783626553,
        "high": 2696.2168783626553,
        "low": 2689.2168783626553,
        "close": 2690.714903869112
      },
      {
        "time": 1793630700,
        "open": 2691.3642203834393,
        "high": 2695.3642203834393,
        "low": 2688.3642203834393,
        "close": 2691.663974802765
      },
      {
        "time": 1793631600,
        "open": 2690.3816657292473,
        "high": 2694.3816657292473,
        "low": 2687.3816657292473,
        "close": 2692.2075562307027
      },
      {
        "time": 1793632500,
        "open": 2689.287043583321,
        "high": 2693.287043583321,
        "low": 2686.287043583321,
        "close": 2690.960354860393
      },
      {
        "time": 1793633400,
        "open": 2688.0999319046277,
        "high": 2692.0999319046277,
        "low": 2685.0999319046277,
        "close": 2688.082229286047
      },
      {
        "time": 1793634300,
        "open": 2686.841351920361,
        "high": 2690.841351920361,
        "low": 2683.841351920361,
        "close": 2685.1489111120104
      },
      {
        "time": 1793635200,
        "open": 2685.5334400967186,
        "high": 2689.5334400967186,
        "low": 2682.5334400967186,
        "close": 2683.722283372705
      },
      {
        "time": 1793636100,
        "open": 2684.199102706752,
        "high": 2688.199102706752,
        "low": 2681.199102706752,
        "close": 2683.9343992065565
      },
      {
        "time": 1793637000,
        "open": 2682.8616583856387,
        "high": 2686.8616583856387,
        "low": 2679.8616583856387,
        "close": 2684.386775286598
      },
      {
        "time": 1793637900,
        "open": 2681.544474251176,
        "high": 2685.544474251176,
        "low": 2678.544474251176,
        "close": 2683.4572261079848
      },
      {
        "time": 1793638800,
        "open": 2680.2706012677245,
        "high": 2684.2706012677245,
        "low": 2677.2706012677245,
        "close": 2680.81241284434
      },
      {
        "time": 1793639700,
        "open": 2679.0624145436204,
        "high": 2683.0624145436204,
        "low": 2676.0624145436204,
        "close": 2677.7351467751946
      },
      {
        "time": 1793640600,
        "open": 2677.941264175092,
        "high": 2681.941264175092,
        "low": 2674.941264175092,
        "close": 2675.965200926906
      },
      {
        "time": 1793641500,
        "open": 2676.9271420851474,
        "high": 2680.9271420851474,
        "low": 2673.9271420851474,
        "close": 2676.119066794501
      },
      {
        "time": 1793642400,
        "open": 2676.0383700563048,
        "high": 2680.0383700563048,
        "low": 2673.0383700563048,
        "close": 2677.1412234187883
      },
      {
        "time": 1793643300,
        "open": 2675.2913138253043,
        "high": 2679.2913138253043,
        "low": 2672.2913138253043,
        "close": 2677.2911375455187
      },
      {
        "time": 1793644200,
        "open": 2674.700127701257,
        "high": 2678.700127701257,
        "low": 2671.700127701257,
        "close": 2675.758293073497
      },
      {
        "time": 1793645100,
        "open": 2674.2765336923885,
        "high": 2678.2765336923885,
        "low": 2671.2765336923885,
        "close": 2673.420168353396
      },
      {
        "time": 1793646000,
        "open": 2674.029638588019,
        "high": 2678.029638588019,
        "low": 2671.029638588019,
        "close": 2672.046080881133
      },
      {
        "time": 1793646900,
        "open": 2673.9657918501625,
        "high": 2677.9657918501625,
        "low": 2670.9657918501625,
        "close": 2672.6787155834486
      },
      {
        "time": 1793647800,
        "open": 2674.0884865322955,
        "high": 2678.0884865322955,
        "low": 2671.0884865322955,
        "close": 2674.6812236897144
      },
      {
        "time": 1793648700,
        "open": 2674.3983047714264,
        "high": 2678.3983047714264,
        "low": 2671.3983047714264,
        "close": 2676.3258955439946
      },
      {
        "time": 1793649600,
        "open": 2674.8929087040424,
        "high": 2678.8929087040424,
        "low": 2671.8929087040424,
        "close": 2676.383135025001
      },
      {
        "time": 1793650500,
        "open": 2675.567076947685,
        "high": 2679.567076947685,
        "low": 2672.567076947685,
        "close": 2675.2498316100755
      },
      {
        "time": 1793651400,
        "open": 2676.412786078881,
        "high": 2680.412786078881,
        "low": 2673.412786078881,
        "close": 2674.5797429830495
      },
      {
        "time": 1793652300,
        "open": 2677.419335835979,
        "high": 2681.419335835979,
        "low": 2674.419335835979,
        "close": 2675.755786350722
      },
      {
        "time": 1793653200,
        "open": 2678.5735160931554,
        "high": 2682.5735160931554,
        "low": 2675.5735160931554,
        "close": 2678.6089199433663
      },
      {
        "time": 1793654100,
        "open": 2679.859813000009,
        "high": 2683.859813000009,
        "low": 2676.859813000009,
        "close": 2681.561620049077
      },
      {
        "time": 1793655000,
        "open": 2681.260651070009,
        "high": 2685.260651070009,
        "low": 2678.260651070009,
        "close": 2683.0642277653064
      },
      {
        "time": 1793655900,
        "open": 2682.756667440081,
        "high": 2686.756667440081,
        "low": 2679.756667440081,
        "close": 2683.0038136855715
      }
    ],
    "overlays": [
      {
        "label": "Entry",
        "price": 2688.4
      },
      {
        "label": "SL",
        "price": 2679.1
      },
      {
        "label": "TP",
        "price": 2707
      }
    ]
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /risk/daily

Purpose: getDailyRisk. Return or operate on the named bridge resource.

Response HTTP 200:

```json
{
  "data": {
    "state": "ACTIVE",
    "reason": null,
    "start_equity": 10000,
    "current_equity": 10042.16,
    "loss_limit_amount": 200,
    "loss_remaining": 200,
    "loss_remaining_percent": 100,
    "profit_target_amount": 300,
    "profit_remaining": 257.84,
    "profit_remaining_percent": 86,
    "trades_remaining": 6,
    "next_day_utc": "2026-11-03T00:00:00Z"
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /telemetry

Purpose: getTelemetry. Return or operate on the named bridge resource.

Response HTTP 200:

```json
{
  "data": {
    "equity": [
      10000,
      9992,
      10006,
      10002,
      10024,
      10015,
      10042.16
    ],
    "spread": [
      18,
      21,
      24,
      19,
      22,
      20,
      21
    ],
    "atr": [
      17,
      17.4,
      17.8,
      18.1,
      18.3,
      18.2,
      18.4
    ]
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /settings

Purpose: getSettingsData. Return or operate on the named bridge resource.

Response HTTP 200:

```json
{
  "data": {
    "version": 7,
    "values": {
      "executionMode": "PAPER",
      "riskPerTrade": 0.5,
      "dailyLossLimit": 2,
      "maxSpread": 35,
      "allowRemoteConfig": true,
      "allowRealAccount": false
    },
    "pending_next_day": false
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /journal

Purpose: getJournal. Return or operate on the named bridge resource.

Parameters: cursor (query); limit (query).

Response HTTP 200:

```json
{
  "data": {
    "items": [
      {
        "id": "1041",
        "time_utc": "2026-11-02T10:00:00Z",
        "side": "BUY",
        "r": 1.7,
        "session": "London",
        "result": "CLOSED"
      }
    ],
    "next_cursor": null
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /validation

Purpose: getValidation. Return or operate on the named bridge resource.

Parameters: cursor (query); limit (query).

Response HTTP 200:

```json
{
  "data": {
    "items": [
      {
        "id": "v1",
        "test": "Walk-forward",
        "status": "REVIEW",
        "period": "2024–2026",
        "evidence": "Simulated evidence only; backend report required"
      }
    ],
    "next_cursor": null
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /logs

Purpose: getLogs. Return or operate on the named bridge resource.

Parameters: cursor (query); limit (query).

Response HTTP 200:

```json
{
  "data": {
    "items": [
      {
        "id": "l1",
        "time_utc": "2026-11-02T10:00:00Z",
        "level": "INFO",
        "source": "bridge",
        "message": "Simulated heartbeat received"
      }
    ],
    "next_cursor": null
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /audit

Purpose: getAudit. Return or operate on the named bridge resource.

Parameters: cursor (query); limit (query).

Response HTTP 200:

```json
{
  "data": {
    "items": [
      {
        "id": "audit-7",
        "time_utc": "2026-11-02T10:00:00Z",
        "actor": "mock-operator",
        "action": "SETTINGS_APPLIED",
        "version": 7,
        "result": "APPLIED",
        "previous_values": {
          "executionMode": "PAPER",
          "riskPerTrade": 0.5,
          "dailyLossLimit": 2,
          "maxSpread": 30,
          "allowRemoteConfig": true,
          "allowRealAccount": false
        }
      }
    ],
    "next_cursor": null
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### GET /requests/{id}

Purpose: getAck. Resolve accepted operation by request ID.

Parameters: id (path, required).

Response HTTP 200:

```json
{
  "data": {
    "request_id": "fixture-request",
    "status": "APPLIED",
    "reason": null,
    "version": 8,
    "ea_ack_utc": "2026-11-02T10:00:00Z"
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### POST /settings/validate

Purpose: settingsvalidate. Return or operate on the named bridge resource.

Request body:

```json
{
  "base_version": 7,
  "values": {
    "executionMode": "PAPER",
    "riskPerTrade": 0.5,
    "dailyLossLimit": 2,
    "maxSpread": 35,
    "allowRemoteConfig": true,
    "allowRealAccount": false
  }
}
```

Response HTTP 200:

```json
{
  "data": {
    "base_version": 7,
    "values": {
      "executionMode": "PAPER",
      "riskPerTrade": 0.5,
      "dailyLossLimit": 2,
      "maxSpread": 30,
      "allowRemoteConfig": true,
      "allowRealAccount": false
    },
    "diff": [
      {
        "key": "maxSpread",
        "old_value": 35,
        "new_value": 30,
        "apply": "HOT",
        "risk_level": "MEDIUM",
        "direction": "TIGHTER"
      }
    ]
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### POST /settings/apply

Purpose: settingsapply. Return or operate on the named bridge resource.

Request body:

```json
{
  "base_version": 7,
  "values": {
    "executionMode": "PAPER",
    "riskPerTrade": 0.5,
    "dailyLossLimit": 2,
    "maxSpread": 35,
    "allowRemoteConfig": true,
    "allowRealAccount": false
  }
}
```

Parameters: Idempotency-Key (required UUID header).

Response HTTP 202:

```json
{
  "data": {
    "request_id": "fixture-request",
    "status": "APPLIED",
    "reason": null,
    "version": 8,
    "ea_ack_utc": "2026-11-02T10:00:00Z"
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### POST /commands/{command}

Purpose: commandscommand. Return or operate on the named bridge resource.

Request body:

```json
{}
```

Parameters: command (path, required); Idempotency-Key (required UUID header).

Response HTTP 202:

```json
{
  "data": {
    "request_id": "fixture-request",
    "status": "APPLIED",
    "reason": null,
    "version": 8,
    "ea_ack_utc": "2026-11-02T10:00:00Z"
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

### POST /audit/{id}/rollback

Purpose: auditidrollback. Prepare historical values for review; no mutation.

Parameters: id (path, required).

Response HTTP 200:

```json
{
  "data": {
    "base_version": 7,
    "values": {
      "executionMode": "PAPER",
      "riskPerTrade": 0.5,
      "dailyLossLimit": 2,
      "maxSpread": 30,
      "allowRemoteConfig": true,
      "allowRealAccount": false
    },
    "diff": [
      {
        "key": "maxSpread",
        "old_value": 35,
        "new_value": 30,
        "apply": "HOT",
        "risk_level": "MEDIUM",
        "direction": "TIGHTER"
      }
    ]
  },
  "error": null,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "api_version": "1.0.0"
}
```

Errors: 400/422 VALIDATION_ERROR; 401 UNAUTHORIZED; 403 MT5_ONLY or LIVE_LOCKED; 404 NOT_FOUND; 409 VERSION_CONFLICT or IDEMPOTENCY_CONFLICT; 503 EA_OFFLINE or UNAVAILABLE, as applicable. Expected REST response <1s locally, hard client deadline 5s; accepted EA results target <10s. Read endpoints never change execution state.

## Events / WebSocket

Connect ws://127.0.0.1:8765/ws. Session authentication must use a Rust/Python-provisioned same-origin mechanism; do not put tokens in URLs. This handshake remains an explicit native integration question. Every event has type, positive integer seq, server_time_utc and the typed payload below. Heartbeat every 2s; stale after 6s, disconnect after 15s without a frame. Exponential reconnect 1/2/4/8/16/30s plus jitter. Invalidate active HTTP queries on open and gaps; discard duplicate/older seq values. New socket establishes a new sequence baseline. HTTP snapshots are authoritative. Recovered stream is not sufficient proof of an in-flight mutation; resolve request_id.

### ea_state

Payload: EaState. Refresh the corresponding HTTP resource; never perform trading calculations. Delivered in seq order within a socket; target latency under 1s, heartbeat 2s. Invalid frames trigger snapshot reconciliation, not UI success.

```json
{
  "type": "ea_state",
  "seq": 42,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "payload": {
    "mode": "PAPER",
    "equity": 10042.16,
    "pnl_today": 42.16,
    "risk_active": true,
    "risk_reason": null,
    "session": "London / New York",
    "trend_h1": "Bullish",
    "trend_h4": "Neutral",
    "h1_strength": 72,
    "h4_strength": 48,
    "atr": 18.4,
    "spread": 21,
    "trades_today": 2,
    "last_rejection": "SPREAD_LIMIT · 41 > 35",
    "live_prerequisites": [
      {
        "key": "demo",
        "ok": true,
        "reason": "Demo evidence reviewed"
      },
      {
        "key": "forward",
        "ok": true,
        "reason": "Forward evidence reviewed"
      },
      {
        "key": "real_account_opt_in",
        "ok": false,
        "reason": "MT5 permission disabled"
      }
    ]
  }
}
```

### position

Payload: Positions. Refresh the corresponding HTTP resource; never perform trading calculations. Delivered in seq order within a socket; target latency under 1s, heartbeat 2s. Invalid frames trigger snapshot reconciliation, not UI success.

```json
{
  "type": "position",
  "seq": 42,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "payload": [
    {
      "id": "XAU-1042",
      "side": "BUY",
      "entry": 2688.4,
      "sl": 2679.1,
      "tp": 2707,
      "lot": 0.12,
      "r": 0.74,
      "status": "OPEN",
      "risk_free": false,
      "time_exit_utc": null
    }
  ]
}
```

### signal

Payload: Signal. Refresh the corresponding HTTP resource; never perform trading calculations. Delivered in seq order within a socket; target latency under 1s, heartbeat 2s. Invalid frames trigger snapshot reconciliation, not UI success.

```json
{
  "type": "signal",
  "seq": 42,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "payload": {
    "id": "sig-31",
    "time_utc": "2026-11-02T10:00:00Z",
    "decision": "WAIT",
    "reasons": [
      "Spread above configured limit"
    ],
    "price": 2691.2,
    "reason_code": "SPREAD_LIMIT",
    "actual": 41,
    "limit": 35
  }
}
```

### risk_mode

Payload: DailyRisk. Refresh the corresponding HTTP resource; never perform trading calculations. Delivered in seq order within a socket; target latency under 1s, heartbeat 2s. Invalid frames trigger snapshot reconciliation, not UI success.

```json
{
  "type": "risk_mode",
  "seq": 42,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "payload": {
    "state": "ACTIVE",
    "reason": null,
    "start_equity": 10000,
    "current_equity": 10042.16,
    "loss_limit_amount": 200,
    "loss_remaining": 200,
    "loss_remaining_percent": 100,
    "profit_target_amount": 300,
    "profit_remaining": 257.84,
    "profit_remaining_percent": 86,
    "trades_remaining": 6,
    "next_day_utc": "2026-11-03T00:00:00Z"
  }
}
```

### log

Payload: LogRecord. Refresh the corresponding HTTP resource; never perform trading calculations. Delivered in seq order within a socket; target latency under 1s, heartbeat 2s. Invalid frames trigger snapshot reconciliation, not UI success.

```json
{
  "type": "log",
  "seq": 42,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "payload": {
    "id": "l1",
    "time_utc": "2026-11-02T10:00:00Z",
    "level": "INFO",
    "source": "bridge",
    "message": "Simulated heartbeat received"
  }
}
```

### command_ack

Payload: Ack. Correlate request_id with submitted operation; apply only with EA ack. Delivered in seq order within a socket; target latency under 1s, heartbeat 2s. Invalid frames trigger snapshot reconciliation, not UI success.

```json
{
  "type": "command_ack",
  "seq": 42,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "payload": {
    "request_id": "fixture-request",
    "status": "APPLIED",
    "reason": null,
    "version": 8,
    "ea_ack_utc": "2026-11-02T10:00:00Z"
  }
}
```

### config_ack

Payload: Ack. Correlate request_id with submitted operation; apply only with EA ack. Delivered in seq order within a socket; target latency under 1s, heartbeat 2s. Invalid frames trigger snapshot reconciliation, not UI success.

```json
{
  "type": "config_ack",
  "seq": 42,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "payload": {
    "request_id": "fixture-request",
    "status": "APPLIED",
    "reason": null,
    "version": 8,
    "ea_ack_utc": "2026-11-02T10:00:00Z"
  }
}
```

### heartbeat

Payload: Status. Refresh the corresponding HTTP resource; never perform trading calculations. Delivered in seq order within a socket; target latency under 1s, heartbeat 2s. Invalid frames trigger snapshot reconciliation, not UI success.

```json
{
  "type": "heartbeat",
  "seq": 42,
  "server_time_utc": "2026-11-02T10:00:00Z",
  "payload": {
    "backend": {
      "state": "healthy",
      "heartbeat_utc": "2026-11-02T10:00:00Z",
      "latency_ms": 12
    },
    "ea": {
      "state": "healthy",
      "heartbeat_utc": "2026-11-02T10:00:00Z",
      "latency_ms": 28
    },
    "mt5": {
      "state": "healthy",
      "heartbeat_utc": "2026-11-02T10:00:00Z",
      "latency_ms": 41
    },
    "broker_offset_minutes": 120
  }
}
```

## Open backend questions

1. Confirm parameter names, units, exact limits and EA-supported HOT/COLD semantics. Defaults are proposed fixture values, not recommendations.
2. Confirm SIGNAL_ONLY/PAPER/LIVE mapping to existing EA modes and gating evidence.
3. Confirm trade-day timezone/reset and broker DST offset, risk-headroom semantics and rejection aggregation boundaries.
4. Confirm transactional version reservation, Ack retention (24h), late Ack reconciliation and COLD effective-time reporting.
5. Supply Python sidecar binary/protocol, Rust-owned start/stop/restart and authenticated readiness handshake. Current app has no native sidecar lifecycle implementation.
6. Agree OS keyring provisioning and HMAC ownership in Rust/Python. No HMAC secret provisioning is currently implemented.
7. Confirm production WebSocket authentication with WebView2: bearer HTTP alone does not authenticate WebSocket.
8. Supply signed updater endpoint/public key, installer signing process and supported native toolchain; release configuration intentionally disables placeholder updater/binary packaging.

Request reconciliation also accepts the original Idempotency-Key as /requests/{id}, allowing recovery when HTTP acceptance was lost. The mock simulates COLD day boundaries in 700ms and is not a production scheduler. Signals includes rejection_counts from the EA for the current trading day; the UI sums supplied counts only.
