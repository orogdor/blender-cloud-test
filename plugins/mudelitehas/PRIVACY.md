# Mudelitehas Beta: data handling

This package contains skills, Python scripts, reviewed source images and listing assets. It does not declare an MCP server, account sign-in or background telemetry.

The model pipeline writes inputs, caches, logs, exported models and validation reports into the work directory chosen for a run. ChatGPT/Codex and the execution environment process prompts and files under their own applicable terms and settings; this package does not change those services' policies.

Runtime installation contacts Blender download servers or mirrors and Python package indexes. These services receive ordinary download requests, including network metadata. Blender itself has its own behavior and license.

The feedback helper creates a local ZIP containing the engine version, run ID, hashes and selected validation results. It excludes model files, screenshots, raw logs and environment variables by default. It generates an issue link but does not submit an issue. A description entered into the helper is included in that ZIP and in the prefilled GitHub link. GitHub issues in this repository are public: review the description and any attachments before submitting them. Do not include credentials or private data.

Questions and reports: https://github.com/orogdor/blender-cloud-test/issues
