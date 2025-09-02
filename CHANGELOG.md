# Changelog
All notable changes to **Agentic Curie** will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/) and follows the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

> **Baseline:** We start recording changes from tag `v0.1.1`. Everything before that tag is considered the initial baseline.

## [Unreleased]

### Added
-

### Changed
-

### Fixed
-

### Removed
-

### Docs
-

### Chore
-

---

## [0.1.2] - 2025-09-02
### Added
- **Resume matching tool**: compare a Job Description (text or file) against one or more resumes and download a CSV report.
- **Contextual input panels** that appear inline only when needed (merge docs / resume match), instead of persistent upload controls.
- **Professional light theme** (off-white background with office blue accents) and a loading spinner overlay for long operations.

### Changed
- **File picker UX**: clearer captions next to buttons (e.g., “No files chosen — Resumes (.pdf, .docx, .txt)”, “Template (.docx, optional)”).
- Assistant guidance can auto-open the right panel when it asks for specific uploads.

### Fixed
- Chat window no longer stretches the page; messages now scroll inside the chat area.
- Long text and URLs wrap inside bubbles to prevent overflow.

### Chore
- Ensure local/runtime artifacts like `data/`, `logs/`, and `.env` are ignored by Git (if not already).

---

<!-- Template to use when cutting a release:
## [X.Y.Z] - YYYY-MM-DD
### Added
-
### Changed
-
### Fixed
-
### Removed
-
### Docs
-
### Chore
-
-->

<!-- Compare links -->
[Unreleased]: https://github.com/grey-ethics/agentic-curie/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/grey-ethics/agentic-curie/compare/v0.1.1...v0.1.2
