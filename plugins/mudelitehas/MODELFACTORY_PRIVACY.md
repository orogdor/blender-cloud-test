# ModelFactory Beta — privacy and data handling

Publisher: **Tõnu Marandi**. This notice describes the distributed skills and scripts, not the separate data practices of ChatGPT, Codex, GitHub or Blender.

## Local work

The package has no publisher-operated MCP server, account sign-in, payment system or automatic telemetry. Prompts and files are processed by the host environment chosen by the user. The pipeline writes reference inputs, point clouds, caches, logs, model exports and validation reports into the selected working directory. These local files are kept until the user or execution environment removes them. The package does not automatically send them to the publisher.

ChatGPT/Codex and the chosen execution environment process information under their own terms and privacy settings. The publisher does not control those services' retention policies.

## Downloads

Runtime setup contacts Blender download servers or mirrors and Python package indexes. These providers receive normal download requests and associated network information under their own policies.

## Optional public feedback

The helper creates a local ZIP with the workflow/run version, run ID, hashes, selected runtime and validation details, and the description supplied by the user. Model files, screenshots, raw logs and environment variables are excluded by default. It produces a prefilled GitHub issue link and does not submit anything automatically.

If the user chooses to submit an issue or attachment, GitHub processes that material and it is public in this repository. Avoid private information. Users can manage their own local files and their own GitHub contributions through the relevant environment or GitHub controls. For a request about content the publisher controls, use the support page and identify the public issue or file without adding further sensitive data; this notice does not promise deletion of third-party copies or backups.

[Support](MODELFACTORY_SUPPORT.md) · [Product information](MODELFACTORY.md) · [Beta terms](MODELFACTORY_TERMS.md)
