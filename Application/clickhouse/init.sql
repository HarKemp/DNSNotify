CREATE TABLE IF NOT EXISTS dns_logs
(
    log_time      DateTime64(3, 'Europe/Riga'),
    client_ip     Nullable(IPv4),
    client_port   Nullable(UInt16),
    query_id      Nullable(UInt64),
    query_type    Nullable(String),
    domain        String,
    protocol      Nullable(String),
    response_code Nullable(String),
    flags         Nullable(String),
    response_time Nullable(Float64),
    prediction            Nullable(Int8),
    malicious_probability Nullable(Float64),
    raw_log       String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(log_time)
ORDER BY (log_time, domain);