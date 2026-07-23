-- Vervangt het "Nightscout Data"-tabblad
CREATE TABLE IF NOT EXISTS nightscout_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  type TEXT NOT NULL,       -- 'glucose' of 'treatment'
  glucose REAL,             -- mmol/L, alleen bij type='glucose'
  amount REAL,              -- carbs (g), alleen bij type='treatment'
  bolus REAL,               -- insuline (E), alleen bij type='treatment'
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_nightscout_timestamp ON nightscout_data(timestamp);

-- Vervangt het "Food log"-tabblad
CREATE TABLE IF NOT EXISTS food_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  description TEXT NOT NULL,
  tags TEXT,
  amount REAL,              -- khd (g) of bolus-eenheden (E), afhankelijk van 'type'
  context TEXT,
  type TEXT                 -- 'khd', 'bolus', of 'beweging'
);
CREATE INDEX IF NOT EXISTS idx_food_log_timestamp ON food_log(timestamp);
