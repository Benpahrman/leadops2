# ✅ Production Refactoring & Modularization Checklist

Use this checklist before, during, and after any refactoring or modularization operation. Every check must pass before considering a refactor complete.

---

## 🚦 Phase 1: Pre-Flight Safety Checks (Before Touching Code)

- [ ] **1.1 Test Baseline Verified**:
  - Run the existing test suite (`pytest` or `npm test`).
  - Verify all existing unit and integration tests pass cleanly.
  - If test coverage for the target module is < 50%, write a baseline integration test verifying current live behavior *before* modifying code.
- [ ] **1.2 Scope & Boundary Frozen**:
  - Identified the exact file(s) and lines being decomposed (e.g., decomposing `run_server.py` lines 200–450).
  - Listed all afferent callers (who calls this module?) and efferent dependencies (what does this module import?).
- [ ] **1.3 Data Contract Definition**:
  - Defined explicit Pydantic request/response schemas or TypeScript interfaces for all data crossing the boundary.
  - No untyped dictionaries (`dict`, `any`, generic `Object`) crossing new package boundaries.
- [ ] **1.4 Zero-Mock Commitment**:
  - Refactored components will consume real live data sources or test harnesses; no mock data or hardcoded stubs will be introduced into production code.

---

## ⚙️ Phase 2: In-Flight Modularization Execution

- [ ] **2.1 Pure Logic First**:
  - Extracted pure calculation, validation, and parsing logic into isolated functions with no side effects or I/O.
- [ ] **2.2 Service Extraction**:
  - Moved business logic, database queries, and agent orchestration into dedicated domain service classes.
  - Route handlers or UI controllers retain only request validation and status response handling.
- [ ] **2.3 Facade & Backward-Compatibility Preservation**:
  - Kept the original entrypoint file intact as a delegating facade if external callers exist.
  - Added `@deprecated` docstrings pointing callers to the new module path.
  - Ensured zero breaking changes for existing callers during transition.
- [ ] **2.4 Clean Encapsulation**:
  - Exposed only public classes/functions via `__all__` in `__init__.py` or barrel exports in `index.js`.
  - Marked internal helpers as private (`_helper_func` or non-exported).
- [ ] **2.5 No Circular Dependencies**:
  - Verified import hierarchy is strictly unidirectional (e.g., Router -> Service -> Repository/Client).
  - No sibling circular imports.
- [ ] **2.6 Complete Code Standard**:
  - Zero placeholder functions, zero `TODO: implement later`, zero `pass` stubs.
  - Full production error handling and typed exceptions across all code paths.

---

## 📝 Phase 3: Documentation & Type Hygiene

- [ ] **3.1 Google / TSDoc Docstrings**:
  - Every new public module, class, and method has a complete docstring with `Args:`, `Returns:`, and `Raises:`.
- [ ] **3.2 Living Architecture Updated**:
  - Added or updated Mermaid sequence/architecture diagrams in the package `README.md`.
  - Added an ADR in `docs/adr/` if this refactor introduced a significant new pattern or broke architectural precedent.
- [ ] **3.3 Type Checking Pass**:
  - Ran `mypy` or `pyright` (Python) and `tsc --noEmit` (TypeScript).
  - Zero type errors on new or modified code.

---

## 🧪 Phase 4: Post-Refactor Verification & Clean-up

- [ ] **4.1 Automated Test Suite Pass**:
  - Ran `pytest tests/ -q` or `npm test`.
  - All existing and new tests pass with 100% success rate.
- [ ] **4.2 End-to-End Live Verification**:
  - Executed real live API request or agent run against staging/local environment.
  - Verified database transactions commit and rollback correctly.
  - Checked logs for deprecation warnings, unhandled exceptions, or performance regressions.
- [ ] **4.3 Dead Code Elimination**:
  - Removed orphaned imports, unused variables, and superseded functions in the original files.
  - Confirmed no dangling files or unused dependencies remain in the repository.
- [ ] **4.4 Git Commit Hygiene**:
  - Organized commits into logical, isolated units (e.g., `refactor(scout): extract ScoutDomainService behind facade`, `docs(scout): add package README and ADR`).
