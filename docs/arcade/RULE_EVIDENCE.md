# Repository evidence for architecture rules

The owner chose to enforce only rules supported by evidence from the repository
at the exact benchmark base. A dependency absent from the baseline is not,
by itself, a violation. A documented relationship, runtime invariant or coding
rule is not automatically an ARCADE component-level `forbid`. A supported rule
also needs an exact scope, faithful representation in the pinned analyzer,
coverage evidence, and clean and planted controls before it can be enforced.
No 48-task contract set or end-to-end guard is claimed here.

## Search scope

The benchmark dataset identifies 48 distinct repository/base pairs. The
preliminary review covered their source snapshots with different scoped
methods, not an exhaustive assessment of every rule:

| Repository | Bases | Preliminary inspection |
|---|---:|---|
| Dask | 8 | Targeted text scan of source archives at each base. |
| DVC | 26 | Targeted text scan of source archives at each base. |
| Requests | 4 | Source archives and tree inspection at each base. |
| Pydantic | 3 | Source archives and tree inspection at each base. |
| Conan | 2 | Complete GitHub tree listings plus selected files at each base. |
| Modin | 3 | Complete GitHub tree listings plus selected files at each base. |
| scikit-learn | 2 | Complete GitHub tree listings plus selected files at each base. |

The Dask/DVC scan matched selected architecture/import phrases in source and
configuration files; tests were excluded except for Dask's `test_base.py`.
Other reviews used selected source, documentation and configuration files. A
missing match does not prove that the repository has no rule. The examples
below apply to the linked exact revisions and cited scope only.

## Evidence and representability

- **Dask: runtime import behavior.** At base
  [`f9310c440b661f1ae96ffd8726404d3c3fe32edc`](https://github.com/dask/dask/blob/f9310c440b661f1ae96ffd8726404d3c3fe32edc/dask/tests/test_base.py#L719-L743),
  `test_default_imports` checks that importing `dask` does not load a listed
  set of heavy or optional modules into `sys.modules`. This is a runtime
  startup constraint, not a prohibition on every static edge between packages.
  It cannot be replaced by an unqualified component-edge ban.
- **DVC: banned symbol.** At base
  [`84b2e685e25c31fc1296d2902c728d84785a656d`](https://github.com/iterative/dvc/blob/84b2e685e25c31fc1296d2902c728d84785a656d/pyproject.toml#L250-L272),
  Ruff selects the TID family and configures `funcy.cached_property` as a
  banned API. The repository's [pre-commit configuration](https://github.com/iterative/dvc/blob/84b2e685e25c31fc1296d2902c728d84785a656d/.pre-commit-config.yaml#L24-L28)
  pins Ruff `v0.1.15`. A local clean control importing the recommended DVC
  symbol passed, while a planted `from funcy import cached_property` produced
  `TID251` using that version and configuration. This symbol-specific rule is
  not shown to be expressible by the current component-level ARCADE guard;
  the Ruff control does not substitute for an ARCADE guard test.
- **Pydantic: local and import-time behavior.** At base
  [`e131d53a07da080c2ba642775efa9e81cb2cf0ba`](https://github.com/pydantic/pydantic/blob/e131d53a07da080c2ba642775efa9e81cb2cf0ba/pydantic/_migration.py#L259-L260),
  a local import is explicitly used to avoid a circular import. At the separate
  base [`7af856a1098406aea84bcadfd0f3de6b7901526c`](https://github.com/pydantic/pydantic/blob/7af856a1098406aea84bcadfd0f3de6b7901526c/pydantic/_internal/_fields.py#L77-L80),
  a cached helper delays importing `annotated_types` until needed. These
  examples are about *when* an import happens. A blanket ban on the corresponding
  component dependency could reject the documented local import; do not infer
  such a ban without a tested scope-aware representation.
- **Requests: optional dependency policy.** At base
  [`0192aac24123735b3eaf9b08df46429bb770c283`](https://github.com/psf/requests/blob/0192aac24123735b3eaf9b08df46429bb770c283/docs/user/advanced.rst#L705-L713),
  the documentation describes `chardet` as optional for Python 3 and mandatory
  for Python 2. This version-specific runtime and packaging policy is not an
  unconditional ban on a package edge. At another Requests base, recovery
  also split entities in six files across components; the file-glob guard
  cannot exactly reproduce those memberships (see `SETUP.md`).
- **Modin: documented structure.** Each of the three inspected bases
  ([`22ce95e78b4db2f21d5940cbd8ee656e7e565d15`](https://github.com/modin-project/modin/blob/22ce95e78b4db2f21d5940cbd8ee656e7e565d15/docs/development/architecture.rst#L80-L88),
  [`e12b21703494dcbb8f7aa951b40ebe1d033307ba`](https://github.com/modin-project/modin/blob/e12b21703494dcbb8f7aa951b40ebe1d033307ba/docs/development/architecture.rst#L80-L88),
  [`d54dcfd8e4cceecdbf818a48bbc712854dda906e`](https://github.com/modin-project/modin/blob/d54dcfd8e4cceecdbf818a48bbc712854dda906e/docs/development/architecture.rst#L80-L88))
  describes the pandas API, query compiler and dataframe relationship. The
  description supports architectural context, not a blanket prohibition on
  reverse imports or on dependencies missing from the baseline.
- **scikit-learn: import syntax and test boundaries.** At both
  [`55bf5d93e5674f13a1134d93a11fd0cd11aabcd1`](https://github.com/scikit-learn/scikit-learn/blob/55bf5d93e5674f13a1134d93a11fd0cd11aabcd1/doc/developers/contributing.rst#L648-L656)
  and [`b7b4d3e2f1a65bcb6d40431d3b61ed1d563c9dab`](https://github.com/scikit-learn/scikit-learn/blob/b7b4d3e2f1a65bcb6d40431d3b61ed1d563c9dab/doc/developers/contributing.rst#L753-L761),
  the contributing guide recommends relative imports within the library,
  absolute public API imports in tests and no wildcard imports. These rules
  concern syntax and test use of public interfaces; component edges alone
  have not been shown to enforce them accurately.
- **Conan: scope needs confirmation.** The same
  [`conans/pylint_plugin.py`](https://github.com/conan-io/conan/blob/4614b3abbff15627b3fabdd98bee419721f423ce/conans/pylint_plugin.py#L57-L84)
  occurs at bases `4614b3abbff15627b3fabdd98bee419721f423ce` and
  `8c424def2d50c9c0e951b52f2609abff19cbeeaa` and flags deprecated `conans`
  imports. The repository also shows [`conans.*` imports](https://github.com/conan-io/conan/blob/4614b3abbff15627b3fabdd98bee419721f423ce/.github/CONTRIBUTING.md#L101-L111)
  in its own contributing guide. The checker scope needs confirmation before
  treating it as a project-wide rule.

Where no evidenced rule can be faithfully enforced, record the task as
unscorable for the guard comparison rather than adding a guessed rule. Existing
source analysis, runtime controls and official benchmark scores are distinct
evidence and must be reported separately.
