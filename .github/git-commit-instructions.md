### Conventional Commits v1.0.0 — **Strict Header Generator (Enhanced)**

Generate **ONLY ONE** Conventional Commits v1.0.0 compliant **commit message HEADER**.

Your job is to **accurately infer the intent of the change** and express it **clearly and specifically**.

---

## HARD OUTPUT RULES (ABSOLUTE)

* Output **exactly ONE line**
* **Header only** (no body, no footer, no blank lines)
* Format:
  `<type>: <concise but specific description>`
* **Do NOT** include scope, parentheses, emojis, quotes, or markdown
* Use **imperative, present tense** (e.g. “add”, “fix”, “update”, not “added”)
* Max length: **72 characters**
* Avoid vague verbs: `update`, `change`, `modify`
  → replace with **what actually changed**

❌ Bad: `docs: update README`
✅ Good: `docs: add usage example for local S3 sync`

---

## TYPE SELECTION RULES (MANDATORY & STRICT)

### 1. docs

Use **ONLY IF**:

* **All changed files are documentation**

  * e.g. `README.md`, `*.md`, `docs/**`
* No code, config, or behavior change

🚫 **FORBIDDEN**:

* Using `feat` or `chore` for documentation-only changes

---

### 2. feat

Use **ONLY IF**:

* Introduces **new user-facing functionality**
* Changes observable behavior or adds a new capability

Examples:

* New CLI option
* New config feature
* New API behavior

---

### 3. fix

Use **ONLY IF**:

* Corrects **incorrect behavior**
* Prevents a bug, crash, or wrong result

Must imply something was broken before.

---

### 4. refactor

Use **ONLY IF**:

* Internal code restructuring
* **Zero behavior change**
* Improves readability, structure, or maintainability

---

### 5. chore

Use **ONLY IF**:

* Maintenance or meta work
* No user-facing impact

Examples:

* File reorganization
* Dependency bumps (non-functional)
* Repo housekeeping

---

### Other allowed types

* `style` → formatting, linting, whitespace
* `perf` → performance improvement
* `test` → add or improve tests
* `build` → build system or dependencies
* `ci` → CI/CD pipeline changes

---

## DESCRIPTION QUALITY RULES (VERY IMPORTANT)

The description **MUST**:

* Clearly state **what changed**
* Implicitly answer **“why does this matter?”**
* Be specific enough that it’s understandable **without context**

### Prefer:

* Object + action + constraint

  * `add automatic local cache sync for S3 objects`
  * `fix race condition in file watcher shutdown`

### Avoid:

* Generic phrases:

  * `minor fixes`
  * `various updates`
  * `cleanup`
  * `improvements`

---

## FINAL SELF-CHECK (BEFORE OUTPUT)

Before producing the line, verify:

1. Is the type **forced by file type or behavior change**?
2. Would a reviewer understand the change **from the header alone**?
3. Is it still ≤ 72 characters?

If not, rewrite.