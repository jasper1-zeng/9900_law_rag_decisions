
# 📄 How to Restore the `satdata` PostgreSQL Database

- **Database file:** `satdata.dump`, can be found at `https://drive.google.com/file/d/1iHJQ8Zrkh3eGYnpkrUiUvP4ifbfNNZQZ/view?usp=drive_link` 
- **PostgreSQL version used to export:** `psql (14.17 (Homebrew))`  
- **File format:** Custom format (not compressed)

---

## ✅ Steps to Restore

1. **Open your terminal.**

2. **Run this command to restore the database:**

```bash
pg_restore -U postgres -C -d postgres -F c satdata.dump
```

> This will create a new database called `satdata` and load the data into it.

---

## 📝 Notes

- If your PostgreSQL username is not `postgres`, replace it with your username:

```bash
pg_restore -U your_username -C -d postgres -F c satdata.dump
```

- This command assumes you already have PostgreSQL installed (version 14.17 or similar).
