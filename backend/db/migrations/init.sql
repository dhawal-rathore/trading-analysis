CREATE TABLE ohlcv (
    id          BIGSERIAL PRIMARY KEY,
    symbol      VARCHAR(20)     NOT NULL,
    timeframe   VARCHAR(10)     NOT NULL,  -- '1min','5min','15min','1hr','4hr','1day','1wk'
    timestamp   TIMESTAMPTZ     NOT NULL,
    open        NUMERIC(20, 8)  NOT NULL,
    high        NUMERIC(20, 8)  NOT NULL,
    low         NUMERIC(20, 8)  NOT NULL,
    close       NUMERIC(20, 8)  NOT NULL,
    volume      NUMERIC(30, 8)  NOT NULL,
    created_at  TIMESTAMPTZ     DEFAULT NOW(),
    CONSTRAINT uq_ohlcv UNIQUE (symbol, timeframe, timestamp)
);

CREATE INDEX idx_ohlcv_lookup ON ohlcv (symbol, timeframe, timestamp);
