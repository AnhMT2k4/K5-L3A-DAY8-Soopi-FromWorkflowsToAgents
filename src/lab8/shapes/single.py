"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace

SHAPE = "single"
MAX_STEPS = 8


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    run_id = make_run_id(SHAPE, claim_id, seed)
    trace = Trace(run_id)

    # Read the claim through the allowlisted view, never SELECT *: the raw claim
    # row carries parent_secret and raw_headers, which must never reach a trace.
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    if not claim.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    # No order id on the claim: ask the customer. Never mine the ticket text for
    # an order code (T04).
    if not claim.get("order_id"):
        complete(budget, seed=seed, purpose="draft", prompt=f"needs_info:{claim_id}")
        trace.add("decision", {"status": "needs_info", "reason": "missing_order_id"})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    # The ReAct loop below only ever reaches read tools (worker=True), so the
    # model cannot move money however the ticket is worded (T09).
    state: dict[str, Any] = {}
    try:
        loop = run_react(
            conn,
            budget,
            observation={"claim": {"claim_id": claim["claim_id"], "order_id": claim["order_id"]}},
            decide=_make_decide(claim, budget, trace, state, seed=seed),
            max_steps=MAX_STEPS,
            worker=True,
        )
    except Exception as exc:  # a rejected tool or an unreadable row, not a crash drill
        trace.add("error", {"reason": "react_failed", "exception": type(exc).__name__})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="react_failed",
        )

    final = loop["final"]
    trace.add("react", {"stopped": loop["stopped"], "tool_calls": budget.tool_calls})

    # The order is not ours or does not exist: hand to a human and leak nothing
    # about it (T05).
    if final["status"] == "escalated":
        complete(budget, seed=seed, purpose="draft", prompt=f"escalated:{claim_id}")
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("error_reason"),
        )

    if final["status"] != "quoted":
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("error_reason") or "no_quote",
        )

    # Money comes from compute_compensation, which read the order row and the
    # current policy. The model never picked this number.
    quote = final["quote"]
    proposal = int(quote["amount_vnd"])
    trace.add(
        "quote",
        {
            "amount_vnd": proposal,
            "reason": quote.get("reason"),
            "clause_ids": quote.get("clause_ids"),
            "parts": quote.get("parts"),
        },
    )
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    # Nothing is owed: deny without touching the host, so no policy_denied audit
    # is written (T02, T06, T09).
    if proposal <= 0:
        trace.add("decision", {"status": "denied", "reason": quote.get("reason")})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=quote.get("reason"),
        )

    # Pass the FULL quote. The host checks this claim's own approval and
    # subtracts what earlier claims already got for the same order (T13, T14).
    # Subtracting here would make the host subtract twice.
    try:
        host = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        # Flush the trace, then let the crash propagate: the ledger transaction,
        # not an except block, is what keeps this to one refund (T12).
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    trace.add("host", {"ok": bool(host["ok"]), "reason": host["reason"]})
    if not host["ok"]:
        # A different amount on a claim that already paid is a conflict, not a
        # policy denial. proposal_amount stays the full quote either way.
        status = "failed" if host["conflict"] else "denied"
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=host["reason"],
        )

    return finish(
        conn,
        shape=SHAPE,
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )


def _make_decide(
    claim: dict[str, Any],
    budget: Budget,
    trace: Trace,
    state: dict[str, Any],
    *,
    seed: int,
):
    """One ReAct step: fold in the last observation, think, pick the next read tool.

    run_react only hands back the most recent tool result, so the agent keeps its
    own `state`. The ticket is deliberately never read here: the order row and the
    current policy are the only sources of truth (T02, T06, T09).
    """
    order_id = claim["order_id"]
    principal_id = claim["principal_id"]

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        last_tool = seen.get("last_tool")
        if last_tool:
            state[last_tool] = seen.get("last_result")

        # One model call per reasoning step, so cost stays comparable to the
        # other shapes. The prompt carries ids only, never ticket text.
        complete(budget, seed=seed, purpose="react", prompt=f"{claim['claim_id']}|seen={len(state)}")

        if "lookup_order" not in state:
            return {"tool": "lookup_order", "args": {"order_id": order_id, "principal_id": principal_id}}

        order_view = state["lookup_order"] or {}
        if not order_view.get("visible"):
            trace.add("observe", {"tool": "lookup_order", "visible": False, "reason": order_view.get("reason")})
            return {"final": {"status": "escalated", "error_reason": order_view.get("reason")}}

        order = order_view["order"]
        if "lookup_refund_history" not in state:
            # Only allowlisted order fields go in the trace — no phone, address,
            # item name or internal note (T05, T10).
            trace.add(
                "observe",
                {
                    "tool": "lookup_order",
                    "visible": True,
                    "order_status": order["status"],
                    "delay_days": order["delay_days"],
                    "damage_verified": order["damage_verified"],
                    "shipping_fee_vnd": order["shipping_fee_vnd"],
                },
            )
            return {
                "tool": "lookup_refund_history",
                "args": {"order_id": order_id, "principal_id": principal_id},
            }

        history = state["lookup_refund_history"] or {}
        if "compute_compensation" not in state:
            # Context for the reply text only. The per-order cap is the host's
            # job, so this number is never subtracted from the quote.
            trace.add(
                "observe",
                {
                    "tool": "lookup_refund_history",
                    "refund_count": history.get("refund_count"),
                    "refunded_vnd": history.get("refunded_vnd"),
                },
            )
            return {"tool": "compute_compensation", "args": {"order": order}}

        return {"final": {"status": "quoted", "quote": state["compute_compensation"] or {}}}

    return decide
