# Contributing to SAT Decisions RAG

This document outlines how to contribute to the project and our workflow process.

## 🛠️ Branching Strategy
- `main` → Stable release branch
- `dev` → Integration/testing branch
- `feature/*` → New features
- `bugfix/*` → Fixes
- `hotfix/*` → Urgent production fixes

## 🚀 Step-by-Step Guide for Team Members

### 1️⃣ Create a New Feature Branch

Before working on a feature, always pull the latest dev branch.

```bash
git checkout dev
git pull origin dev
git checkout -b feature/your-feature-name
```

Example:
```bash
git checkout -b feature/sat-scraper
```

### 2️⃣ Work on the Feature and Commit Changes

After making changes, commit regularly with meaningful messages.

```bash
git add .
git commit -m "feat: implemented SAT decision scraper"
```

### 3️⃣ Push the Branch to Remote Repository

```bash
git push origin feature/sat-scraper
```

### 4️⃣ Create a Pull Request (PR) to dev

- Go to GitHub → Pull Requests → Click New Pull Request.
- Select `feature/sat-scraper` → `dev`.
- Add a clear title and description.
- Assign reviewers and set appropriate labels.
- Click Create Pull Request.

### 5️⃣ Review & Merge into dev

- Team members review the PR.
- CI/CD runs tests automatically.
- Once approved, merge into dev:

```bash
git checkout dev
git merge feature/sat-scraper
git push origin dev
```

Delete the branch after merging:

```bash
git branch -d feature/sat-scraper
git push origin --delete feature/sat-scraper
```

### 6️⃣ Periodic Merge dev → main for Releases

Once dev is stable and tested, a Lead Developer or PM will:

```bash
git checkout main
git merge dev
git push origin main
```

This is usually done before an official release.

## 📌 Best Practices

### ✅ Use Meaningful Branch Names
❌ `dev-will` → Not good  
✅ `feature/scraper` → Better

### ✅ Use PR Templates
Create `.github/PULL_REQUEST_TEMPLATE.md` to guide PR descriptions.

### ✅ Enable PR Reviews
Require at least one approval before merging.

### ✅ CI/CD Integration
Set up GitHub Actions to automatically run tests on PRs.

### ✅ Use GitHub Project Board
Track progress:  
🚀 To Do → 🔨 In Progress → ✅ Merged into dev

## 🌱 How to Work on a Feature

1. Checkout `dev`:
   ```bash
   git checkout dev && git pull origin dev
   ```

2. Create a new feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Work on your feature, commit changes, then push:
   ```bash
   git add .
   git commit -m "feat: added new feature"
   git push origin feature/your-feature-name
   ```

4. Open a Pull Request to `dev` and request a review.
5. After approval, merge into `dev` and delete the feature branch.

## 🔄 Merging dev → main

Once `dev` is stable, a Lead Developer will merge into `main`.

## 🎯 Conclusion

1. Document the process in `CONTRIBUTING.md`.
2. Use GitHub Project Boards to track work.
3. Create feature branches (`feature/*`) and PR into `dev`.
4. After testing, merge `dev` into `main`.
5. Automate CI/CD to test before merging.
