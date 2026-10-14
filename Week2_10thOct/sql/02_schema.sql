CREATE TABLE Googlepay (
    transaction_id VARCHAR(20) PRIMARY KEY,
    sender VARCHAR(100) NOT NULL,
    receiver VARCHAR(100) NOT NULL
    amount NUMERIC(12, 2) NOT NULL,
    status VARCHAR(30) NOT NULL
);
