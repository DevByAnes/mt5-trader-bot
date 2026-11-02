import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    error = {
        "description": "Authenticated local service error",
        "content": {
            "application/json": {
                "schema": {"$ref": "openapi.yaml#/components/schemas/ErrorEnvelope"}
            }
        },
    }
    result = {
        "openapi": "3.1.0",
        "info": {"title": "Aurum local session extensions", "version": "2.0.0"},
        "servers": [{"url": "http://127.0.0.1:8765/api/v2"}],
        "security": [{"session": []}],
        "paths": {
            "/session/ws-ticket": {
                "post": {
                    "operationId": "issueSocketTicket",
                    "parameters": [
                        {
                            "name": "Origin",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "One-use ticket; send only in first WS frame",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SocketTicketEnvelope"}
                                }
                            },
                        },
                        **{str(s): error for s in [401, 403, 422, 503]},
                    },
                }
            }
        },
        "components": {
            "securitySchemes": {"session": {"type": "http", "scheme": "bearer"}},
            "schemas": {
                "SocketTicket": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ticket", "expires_in_seconds"],
                    "properties": {
                        "ticket": {"type": "string", "minLength": 32, "maxLength": 128},
                        "expires_in_seconds": {"type": "integer", "const": 10},
                    },
                },
                "SocketTicketEnvelope": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["data", "error", "api_version", "server_time_utc"],
                    "properties": {
                        "data": {"$ref": "#/components/schemas/SocketTicket"},
                        "error": {"type": "null"},
                        "api_version": {"const": "1.0.0"},
                        "server_time_utc": {"type": "string", "format": "date-time"},
                    },
                },
            },
        },
    }
    (root / "schema/session.openapi.yaml").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
