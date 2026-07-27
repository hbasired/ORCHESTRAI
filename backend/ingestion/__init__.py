"""Stage 13 — CDC ingestion: DB writes (INSERT incidents / UPDATE stages.status) flow into the live SimWorld.

Transactional-outbox CDC (research §22): a Postgres trigger writes a durable `cdc_outbox` row + `pg_notify` signal;
`cdc_listener.CDCListener` LISTENs, drains the outbox (catching anything missed while offline), and converts each
change into a `SimWorld` inject — closing the bidirectional loop (KB_05 §97, KB_25, G-023).
"""
