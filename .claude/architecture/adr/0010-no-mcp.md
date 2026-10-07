# ADR-0010: No MCP

- Status: Accepted
- Date: 2026-10-07

## Context
MCP exposes tools to external LLM hosts. All QualifAI tools are internal and called in-process.

## Options considered
1. MCP servers for internal tools.
2. Direct function calls.

## Decision
Option 2. Revisit only to expose QualifAI to external assistants (V3 nicety).

## Consequences
Less indirection and latency.
