# 📦 Conan Dependency Analyzer

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![CI](https://img.shields.io/github/actions/workflow/status/perseoGI/conan-deps-analyzer/ci.yml?branch=main&label=CI)](https://github.com/perseoGI/conan-deps-analyzer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A set of [Conan 2 Custom Commands](https://docs.conan.io/2/reference/extensions/custom_commands.html) for parsing and analyzing dependency graphs in [Conan Center Index](https://github.com/conan-io/conan-center-index)-style recipe repositories.

The tool statically analyzes `conanfile.py` files using Python's AST to extract dependency information without executing the recipes, then optionally evaluates conditional dependencies against Conan profiles.

## ✨ Features

- 📋 **Dependency listing** -- list all `requires` and `tool_requires` of any recipe, resolved per version.
- 🔗 **Usage analysis** -- find which recipes depend on a given library, including transitive consumers.
- 📊 **Version inventory** -- list version counts across the repository with statistics (average, std deviation).
- ✂️ **Version trimming** -- interactively remove old recipe versions based on cross-reference analysis and configurable heuristics, with automatic `config.yml`/`conandata.yml` cleanup and lint integration.
- 🎯 **Profile-aware evaluation** -- resolve conditional dependencies (`if self.settings.os == ...`, `if self.options.foo`, etc.) against host/build profiles.
- 🔄 **Fallback evaluation** -- when static analysis can't determine a condition's default, optionally fall back to loading the recipe with CCI profiles.
- ⚡ **Caching** -- parsed results are persisted to a `shelve` database keyed by file modification time, making repeated queries fast.

## 📥 Installation

Install the custom commands using [`conan config install`](https://docs.conan.io/2/reference/commands/config.html#conan-config-install):

```bash
conan config install https://github.com/perseoGI/conan-deps-analyzer.git -sf conan_config
```

The commands will then be available under the `cci` group in the Conan CLI.

### 📌 Requirements

- [Conan 2](https://docs.conan.io/2/) (provides the CLI framework and profile model)
- Python 3.10+
- `ruamel.yaml` (only required for the `trim-versions` command)

## 🚀 Usage

All commands expect `recipes_path` as the first positional argument -- the path to the root of a Conan Center Index-like `recipes/` directory.

### 📋 `conan cci:list dependencies`

List all dependencies of one or all recipes.

```bash
# All recipes
conan cci:list dependencies /path/to/recipes

# Single recipe, all versions
conan cci:list dependencies /path/to/recipes -r openssl

# Single recipe, specific version
conan cci:list dependencies /path/to/recipes -r openssl/3.2.0

# With profile-aware evaluation
conan cci:list dependencies /path/to/recipes -r openssl -pr:h default

# Only unconditionally-enabled dependencies
conan cci:list dependencies /path/to/recipes -r openssl --only-default

# JSON output
conan cci:list dependencies /path/to/recipes -r openssl -f json
```

### 🔍 `conan cci:list usages`

Find which recipes depend on a given library.

```bash
# All consumers of zlib
conan cci:list usages /path/to/recipes -r zlib

# Consumers of a specific version
conan cci:list usages /path/to/recipes -r zlib/1.3.1

# Include transitive consumers
conan cci:list usages /path/to/recipes -r zlib -t

# With profile evaluation
conan cci:list usages /path/to/recipes -r zlib -pr:h default
```

### 📈 `conan cci:list versions`

List version counts with optional filtering.

```bash
# Recipes with more than 15 versions
conan cci:list versions /path/to/recipes --min 15

# Recipes with 5 to 10 versions, counts only
conan cci:list versions /path/to/recipes --min 5 --max 10 --count

# Only versions that are actually referenced by other recipes
conan cci:list versions /path/to/recipes -r openssl --only-referenced
```

### ✂️ `conan cci:trim-versions`

Interactively trim old versions from recipes.

```bash
# Dry-run (interactive prompts, no changes written)
conan cci:trim-versions /path/to/recipes --max-versions 10

# Auto-confirm changes
conan cci:trim-versions /path/to/recipes --max-versions 10 --confirm

# Trim a single recipe
conan cci:trim-versions /path/to/recipes -r boost --max-versions 8

# Provide a precomputed ignore list of referenced versions
conan cci:trim-versions /path/to/recipes --ignore-refs-file refs.json --confirm
```

### ⚙️ Common options

| Option | Description |
|---|---|
| `-r`, `--reference` | Recipe reference (`name` or `name/version`). Omit to process all recipes. |
| `--only-default` | Show only dependencies that are enabled by default (unconditional or with default options). |
| `--no-cache` | Bypass the persistent parse cache and re-analyze from source. |
| `--fallback` | Use CCI profile-based fallback evaluation for conditions that can't be resolved statically. |
| `-pr:h`, `-pr:b` | Standard Conan profile arguments for host/build profile evaluation. |
| `-f json` | Output in JSON format. |
