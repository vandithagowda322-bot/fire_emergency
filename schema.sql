CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'dispatcher'
);
CREATE TABLE IF NOT EXISTS stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    area TEXT NOT NULL,
    available_units INTEGER NOT NULL DEFAULT 3
);
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Reported',
    station_id INTEGER REFERENCES stations(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Default login users & initial fire stations for fresh /tmp database
INSERT OR IGNORE INTO users (id, username, password_hash, role)
VALUES (1, 'admin', 'scrypt:32768:8:1$qe2oaGLHElpLNFVv$f17d85ca41afd49f2e17fe829a7444af62e4706814d80c51187e2c5021842b1f0039dd2d18191f2242e5bb570659d99069f26f1963d5bca0a28c9c8bafe1570d', 'dispatcher');

INSERT OR IGNORE INTO stations (id, name, area, available_units)
VALUES
    (1, 'Central Fire Station', 'City Centre', 4),
    (2, 'North Fire Station', 'North Zone', 3),
    (3, 'South Fire Station', 'South Zone', 3);
