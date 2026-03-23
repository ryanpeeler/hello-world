There are 57 staged files ready to commit, plus `artifacts/` and `config.carbon-nanotubes.yaml` untracked. Before I proceed, two quick questions:

1. **Include `artifacts/`?** These are run artifact directories — they can be large/noisy. Recommend excluding unless you need them versioned.
2. **Include `config.carbon-nanotubes.yaml`?** This is the project config for this pipeline run — likely worth committing.

I'll commit the 57 staged files + the config, and skip `artifacts/` (which you can add to `.gitignore`). Confirm and I'll proceed, or let me know if you want a different scope.