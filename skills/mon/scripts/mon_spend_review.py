#!/usr/bin/env python3
"""Review Monarch transactions for shared-expense reimbursements.

This script is intentionally local-only: it reads JSON produced by `mon
transactions --json` and emits a compact spending review. It never reads tokens
or calls Monarch directly.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SPEND_CATEGORIES = {
    "Restaurants & Bars",
    "Groceries",
    "Entertainment & Recreation",
    "Travel & Vacation",
    "Shopping",
    "Coffee Shops",
    "Public Transit",
    "Internet & Cable",
    "Insurance",
    "Office Supplies & Expenses",
    "Miscellaneous",
    "Cash & ATM",
}

NON_CONSUMPTION_OUTFLOW = {
    "Transfer",
    "Credit Card Payment",
    "Rent",
}

NON_REIMBURSEMENT_INFLOW = {
    "Paychecks",
    "Interest",
    "Credit Card Payment",
}

DEFAULT_OWN_NAMES = {
    "yupei tian",
}

INFRA_NAMES = {
    "carnegie mellon",
    "chase",
    "discover",
}


@dataclass
class Tx:
    id: str
    date: dt.date
    amount: float
    category: str
    merchant: str
    raw_name: str
    account: str
    pending: bool
    hidden: bool

    @classmethod
    def from_monarch(cls, value: dict[str, Any]) -> "Tx":
        category = (value.get("category") or {}).get("name") or ""
        merchant = (value.get("merchant") or {}).get("name") or ""
        raw_name = value.get("plaidName") or ""
        account = (value.get("account") or {}).get("displayName") or ""
        return cls(
            id=str(value.get("id") or ""),
            date=dt.date.fromisoformat(value["date"]),
            amount=float(value["amount"]),
            category=category,
            merchant=merchant,
            raw_name=raw_name,
            account=account,
            pending=bool(value.get("pending")),
            hidden=bool(value.get("hideFromReports")),
        )

    @property
    def name(self) -> str:
        return self.merchant or self.raw_name

    @property
    def abs_amount(self) -> float:
        return abs(self.amount)


@dataclass
class Event:
    date: dt.date
    expenses: list[Tx]
    reimbursements: list[Tx] = field(default_factory=list)

    @property
    def gross(self) -> float:
        return sum(tx.abs_amount for tx in self.expenses)

    @property
    def reimbursement_total(self) -> float:
        return sum(tx.amount for tx in self.reimbursements)

    @property
    def net(self) -> float:
        return self.gross - self.reimbursement_total

    @property
    def confidence(self) -> str:
        if not self.reimbursements:
            return "none"
        ratio = self.reimbursement_total / self.gross if self.gross else 0
        if 0.55 <= ratio <= 1.05:
            return "high"
        if 0.25 <= ratio < 0.55 or 1.05 < ratio <= 1.25:
            return "medium"
        return "low"


def money(value: float) -> str:
    return f"${value:,.2f}"


def load_transactions(path: Path) -> list[Tx]:
    data = json.loads(path.read_text())
    values = data.get("allTransactions", {}).get("results", [])
    txs = [Tx.from_monarch(value) for value in values]
    seen: set[str] = set()
    unique: list[Tx] = []
    for tx in txs:
        key = tx.id or f"{tx.date}:{tx.amount}:{tx.name}:{tx.account}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(tx)
    return sorted(unique, key=lambda tx: (tx.date, tx.amount, tx.name))


def compact_name(tx: Tx) -> str:
    text = tx.raw_name or tx.merchant
    match = re.search(r"zelle payment from\s+(.+?)(?:\s+[A-Z0-9]{8,}|\s+\d{8,}|$)", text, re.I)
    if match:
        return f"Zelle from {match.group(1).strip()}"
    match = re.search(r"payment from\s+(.+)", text, re.I)
    if match:
        return f"Payment from {match.group(1).strip()}"
    return tx.name


def text_has_any(text: str, needles: set[str]) -> bool:
    low = text.lower()
    return any(needle in low for needle in needles)


def is_visible_settled(tx: Tx, include_pending: bool) -> bool:
    if tx.hidden:
        return False
    if tx.pending and not include_pending:
        return False
    return True


def is_consumption_outflow(tx: Tx, include_pending: bool) -> bool:
    if not is_visible_settled(tx, include_pending) or tx.amount >= 0:
        return False
    if tx.category in NON_CONSUMPTION_OUTFLOW:
        return False
    return tx.category in SPEND_CATEGORIES or bool(tx.category)


def is_reimbursement_candidate(tx: Tx, include_pending: bool, own_names: set[str]) -> bool:
    if not is_visible_settled(tx, include_pending) or tx.amount <= 0:
        return False
    if tx.category in NON_REIMBURSEMENT_INFLOW:
        return False
    full_text = f"{tx.merchant} {tx.raw_name}"
    if text_has_any(full_text, own_names | INFRA_NAMES):
        return False
    if tx.category in {"Transfer", "Other Income", "Business Income", "Shopping"}:
        return True
    low = full_text.lower()
    return "zelle payment from" in low or "payment from" in low


def is_merchant_credit(tx: Tx, include_pending: bool, own_names: set[str]) -> bool:
    if not is_visible_settled(tx, include_pending) or tx.amount <= 0:
        return False
    if is_reimbursement_candidate(tx, include_pending, own_names):
        return False
    if tx.category in NON_REIMBURSEMENT_INFLOW:
        return False
    return tx.category in SPEND_CATEGORIES


def build_events(txs: list[Tx], min_anchor: float, include_pending: bool) -> list[Event]:
    by_day: dict[dt.date, list[Tx]] = {}
    for tx in txs:
        if is_consumption_outflow(tx, include_pending):
            by_day.setdefault(tx.date, []).append(tx)

    events: list[Event] = []
    for day, day_txs in sorted(by_day.items()):
        anchors = [
            tx
            for tx in day_txs
            if tx.category in {"Restaurants & Bars", "Groceries", "Entertainment & Recreation", "Travel & Vacation", "Shopping"}
            and tx.abs_amount >= min_anchor
        ]
        if not anchors:
            continue
        events.append(Event(date=day, expenses=sorted(anchors, key=lambda tx: tx.amount)))
    return events


def assign_reimbursements(events: list[Event], reimbursements: list[Tx], window_days: int) -> None:
    for reimb in sorted(reimbursements, key=lambda tx: (tx.date, tx.amount)):
        candidates = [
            event
            for event in events
            if dt.timedelta(days=0) <= reimb.date - event.date <= dt.timedelta(days=window_days)
        ]
        if not candidates:
            continue
        candidates.sort(
            key=lambda event: (
                (reimb.date - event.date).days,
                abs(event.net - reimb.amount),
                -event.gross,
            )
        )
        chosen = candidates[0]
        if chosen.reimbursement_total + reimb.amount <= chosen.gross * 1.25:
            chosen.reimbursements.append(reimb)


def summarize(txs: list[Tx], events: list[Event], reimbursements: list[Tx], merchant_credits: list[Tx], include_pending: bool) -> dict[str, Any]:
    consumption = [tx for tx in txs if is_consumption_outflow(tx, include_pending)]
    raw_spend = sum(tx.abs_amount for tx in consumption)
    assigned_reimbursements = {tx.id for event in events for tx in event.reimbursements}
    assigned_total = sum(tx.amount for tx in reimbursements if tx.id in assigned_reimbursements)
    merchant_credit_total = sum(tx.amount for tx in merchant_credits)
    adjusted = raw_spend - assigned_total
    cash_adjusted = adjusted - merchant_credit_total

    by_category: dict[str, float] = {}
    for tx in consumption:
        by_category[tx.category] = by_category.get(tx.category, 0.0) + tx.abs_amount

    reclassification_rows: list[dict[str, Any]] = []
    category_offsets: dict[str, float] = {}
    for event in events:
        for reimb in event.reimbursements:
            for category, amount in allocate_reimbursement_to_categories(event, reimb.amount):
                category_offsets[category] = category_offsets.get(category, 0.0) + amount
                reclassification_rows.append(
                    {
                        "date": reimb.date.isoformat(),
                        "source": compact_name(reimb),
                        "originalCategory": reimb.category,
                        "assignedEventDate": event.date.isoformat(),
                        "assignedCategory": category,
                        "signedAmount": round(-amount, 2),
                        "eventGross": round(event.gross, 2),
                        "eventMerchants": [tx.name for tx in event.expenses],
                    }
                )

    category_after = {
        category: amount - category_offsets.get(category, 0.0)
        for category, amount in by_category.items()
    }

    unresolved_large = [
        tx
        for tx in consumption
        if tx.abs_amount >= 80 and all(tx not in event.expenses for event in events if event.reimbursements)
    ]

    return {
        "transactionCount": len(txs),
        "rawConsumptionSpend": round(raw_spend, 2),
        "assignedReimbursements": round(assigned_total, 2),
        "merchantCreditTotal": round(merchant_credit_total, 2),
        "adjustedConsumptionSpend": round(adjusted, 2),
        "cashImpactAfterCredits": round(cash_adjusted, 2),
        "categorySpend": [
            {"category": category, "amount": round(amount, 2)}
            for category, amount in sorted(by_category.items(), key=lambda item: -item[1])
        ],
        "categorySpendAfterReimbursements": [
            {
                "category": category,
                "raw": round(by_category[category], 2),
                "aaOffset": round(-category_offsets.get(category, 0.0), 2),
                "adjusted": round(amount, 2),
            }
            for category, amount in sorted(category_after.items(), key=lambda item: -item[1])
        ],
        "reclassificationLedger": reclassification_rows,
        "events": [
            {
                "date": event.date.isoformat(),
                "gross": round(event.gross, 2),
                "reimbursements": round(event.reimbursement_total, 2),
                "net": round(event.net, 2),
                "confidence": event.confidence,
                "expenses": [
                    {
                        "amount": round(tx.abs_amount, 2),
                        "category": tx.category,
                        "merchant": tx.name,
                    }
                    for tx in event.expenses
                ],
                "matchedInflows": [
                    {
                        "date": tx.date.isoformat(),
                        "amount": round(tx.amount, 2),
                        "category": tx.category,
                        "source": compact_name(tx),
                    }
                    for tx in event.reimbursements
                ],
            }
            for event in events
            if event.reimbursements
        ],
        "unresolvedLargeOutflows": [
            {
                "date": tx.date.isoformat(),
                "amount": round(tx.abs_amount, 2),
                "category": tx.category,
                "merchant": tx.name,
            }
            for tx in unresolved_large
        ],
        "merchantCredits": [
            {
                "date": tx.date.isoformat(),
                "amount": round(tx.amount, 2),
                "category": tx.category,
                "merchant": tx.name,
                "pending": tx.pending,
            }
            for tx in merchant_credits
        ],
    }


def allocate_reimbursement_to_categories(event: Event, amount: float) -> list[tuple[str, float]]:
    by_category: dict[str, float] = {}
    for tx in event.expenses:
        by_category[tx.category] = by_category.get(tx.category, 0.0) + tx.abs_amount

    if len(by_category) == 1:
        category = next(iter(by_category))
        return [(category, round(amount, 2))]

    allocations: list[tuple[str, float]] = []
    remaining = round(amount, 2)
    categories = sorted(by_category.items(), key=lambda item: -item[1])
    for index, (category, gross) in enumerate(categories):
        if index == len(categories) - 1:
            allocated = remaining
        else:
            allocated = round(amount * gross / event.gross, 2)
            remaining = round(remaining - allocated, 2)
        allocations.append((category, allocated))
    return allocations


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Monarch Spend Review",
        "",
        f"- Transactions: {summary['transactionCount']}",
        f"- Raw consumption spend: {money(summary['rawConsumptionSpend'])}",
        f"- Matched reimbursements / AA: {money(summary['assignedReimbursements'])}",
        f"- Adjusted consumption spend: {money(summary['adjustedConsumptionSpend'])}",
        f"- Merchant credits / refunds, listed separately: {money(summary['merchantCreditTotal'])}",
        f"- Cash impact after credits: {money(summary['cashImpactAfterCredits'])}",
        "",
        "## Matched Shared-Spend Events",
    ]
    for event in summary["events"]:
        lines.append(
            f"- {event['date']}: gross {money(event['gross'])}, reimbursed {money(event['reimbursements'])}, net {money(event['net'])}, confidence {event['confidence']}"
        )
        for tx in event["expenses"]:
            lines.append(f"  - expense: {money(tx['amount'])} {tx['category']} at {tx['merchant']}")
        for tx in event["matchedInflows"]:
            lines.append(f"  - inflow: {money(tx['amount'])} on {tx['date']} from {tx['source']} ({tx['category']})")

    lines.extend(["", "## Category Spend Before Reimbursements"])
    for row in summary["categorySpend"]:
        lines.append(f"- {row['category']}: {money(row['amount'])}")

    lines.extend(["", "## Category Spend After AA Reclassification"])
    for row in summary["categorySpendAfterReimbursements"]:
        lines.append(
            f"- {row['category']}: raw {money(row['raw'])}, AA offset {money(row['aaOffset'])}, adjusted {money(row['adjusted'])}"
        )

    lines.extend(["", "## Reclassification Ledger"])
    for row in summary["reclassificationLedger"]:
        merchants = ", ".join(row["eventMerchants"])
        lines.append(
            f"- {row['date']}: {money(row['signedAmount'])} from {row['source']} -> {row['assignedCategory']} for {row['assignedEventDate']} event ({merchants})"
        )

    lines.extend(["", "## Unresolved Large Outflows"])
    for tx in summary["unresolvedLargeOutflows"]:
        lines.append(f"- {tx['date']}: {money(tx['amount'])} {tx['category']} at {tx['merchant']}")

    if summary["merchantCredits"]:
        lines.extend(["", "## Merchant Credits / Refunds"])
        for tx in summary["merchantCredits"]:
            pending = " pending" if tx["pending"] else ""
            lines.append(f"- {tx['date']}: {money(tx['amount'])} {tx['category']} from {tx['merchant']}{pending}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Review Monarch transaction JSON for shared-spend reimbursements.")
    parser.add_argument("--input", required=True, type=Path, help="JSON file from `mon transactions --json`.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--min-anchor", type=float, default=45.0, help="Minimum outflow amount to treat as a shared-spend anchor.")
    parser.add_argument("--window-days", type=int, default=3, help="Days after an expense to match incoming reimbursements.")
    parser.add_argument("--include-pending", action="store_true", help="Include pending transactions.")
    parser.add_argument("--own-name", action="append", default=[], help="Name fragment to treat as own/internal transfer. Repeatable.")
    args = parser.parse_args()

    own_names = DEFAULT_OWN_NAMES | {value.lower() for value in args.own_name}
    txs = load_transactions(args.input)
    reimbursements = [tx for tx in txs if is_reimbursement_candidate(tx, args.include_pending, own_names)]
    merchant_credits = [tx for tx in txs if is_merchant_credit(tx, args.include_pending, own_names)]
    events = build_events(txs, args.min_anchor, args.include_pending)
    assign_reimbursements(events, reimbursements, args.window_days)
    summary = summarize(txs, events, reimbursements, merchant_credits, args.include_pending)

    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        sys.stdout.write(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
