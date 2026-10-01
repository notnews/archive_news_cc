# Working on this data repository

This is a point-in-time data collection. Follow the [data-repository policy](https://github.com/soodoku/data-repos#maintenance-policy).

- Preserve sources, collection dates, provenance, schemas and reproducible parsing commands.
- Run the affected parser tests once when code changes. Check schemas, keys, missingness and source/output hashes when data change. Review documentation edits directly.
- Keep full-data validation, reprocessing, scraping and publication explicit. Do not run them for routine edits or repeat successful checks without a relevant change or failure.
- Do not add blanket CI, recurring dependency checks, version matrices, Docker/VM checks, pre-commit, Preen or package-release scaffolding. These collections do not need continuous package maintenance.
- Use the existing environment and standard tools. Install missing dependencies only for the checks needed by the current change; do not provision a matrix of environments.
- Ask when source meaning or credentials are unclear. Check official documentation for API questions. Preserve unrelated work and never infer substantive data values to make a check pass.
