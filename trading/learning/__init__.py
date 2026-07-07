"""Recursive learning loop (built in Phase 5).

Logs every closed trade against its original reasoning, keeps a performance
ledger per agent and per strategy book, adjusts agent confidence weights from
that ledger, and produces the weekly plain-English self-review. This is
pattern-reinforcement and adaptive weighting stored in a local database —
NOT model retraining.
"""
