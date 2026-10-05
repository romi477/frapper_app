# Keep this package import-free: `python -m app` must run ensure_db before
# app.db / app.models bind the SQLite file and check the tables.
