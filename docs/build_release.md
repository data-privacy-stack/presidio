# Build and release process

Presidio uses GitHub Actions workflows to validate, build, release, and deliver official artifacts.

## Workflows

The following workflows are maintained as part of the Presidio development process:

- [CI](https://github.com/data-privacy-stack/presidio/blob/main/.github/workflows/ci.yml) - triggered for pull requests and merges to the main branch.
    - Linting
    - Dependency review
    - Unit tests
    - Package builds
    - Container builds and E2E tests
- [Release](https://github.com/data-privacy-stack/presidio/blob/main/.github/workflows/release.yml) - manually triggered for official releases.
    - Publishes Python packages to [PyPI](https://pypi.org/search/?q=presidio)
    - Publishes container images to [GitHub Container Registry](https://github.com/orgs/data-privacy-stack/packages)
    - Creates a draft GitHub release

## Container image publishing

Official Presidio container images are now published to GitHub Container Registry (GHCR) under the Data Privacy Stack organization:

- [`ghcr.io/data-privacy-stack/presidio-analyzer`](https://github.com/orgs/data-privacy-stack/packages/container/package/presidio-analyzer)
- [`ghcr.io/data-privacy-stack/presidio-anonymizer`](https://github.com/orgs/data-privacy-stack/packages/container/package/presidio-anonymizer)
- [`ghcr.io/data-privacy-stack/presidio-image-redactor`](https://github.com/orgs/data-privacy-stack/packages/container/package/presidio-image-redactor)

The legacy Microsoft Container Registry images at `mcr.microsoft.com/presidio-*` are no longer updated. Existing MCR tags can still be pulled for older deployments, but users should update image references to GHCR before upgrading. For example:

```sh
docker pull ghcr.io/data-privacy-stack/presidio-analyzer:latest
```

For production deployments, avoid relying on the moving `latest` tag. Pin the release tag shown on the relevant [GitHub Packages page](https://github.com/orgs/data-privacy-stack/packages), for example:

```sh
docker pull ghcr.io/data-privacy-stack/presidio-analyzer:<release-version>
```

If an existing deployment uses `mcr.microsoft.com/presidio-analyzer:latest`, treat it as a legacy reference and replace it with either `ghcr.io/data-privacy-stack/presidio-analyzer:latest` for quick testing or a pinned GHCR release tag for production.

Docker registries do not provide a portable way to redirect `docker pull mcr.microsoft.com/presidio-analyzer:latest` to GHCR or show a deprecation warning during `docker pull`. To reduce confusion, each GitHub release includes the GHCR image names, the GHCR images include OCI metadata labels pointing to the source repository, package page, and installation guide, and the MCR tags are documented as legacy references.

## PyPI publishing with OIDC

The release workflow uses OIDC (OpenID Connect) trusted publishing to PyPI, which eliminates the need to manage PyPI API tokens. This requires:

1. **PyPI configuration**: Each package (`presidio-analyzer`, `presidio-anonymizer`, and the other Presidio packages) must be configured on PyPI to trust the GitHub repository and workflow.
2. **GitHub workflow permissions**: The workflow uses `pypa/gh-action-pypi-publish@release/v1` with `id-token: write`.
3. **No PyPI secrets**: No PyPI API tokens need to be stored as GitHub secrets.

Benefits of OIDC:

- Enhanced security through short-lived tokens
- No manual token management
- Automatic token rotation
- Audit trail of publishing activities

## GHCR publishing permissions

The container publishing jobs authenticate to GHCR with the workflow `GITHUB_TOKEN` by default and require `packages: write` permissions. If the workflow is run from a repository outside the `data-privacy-stack` organization during the transition, set the `GHCR_TOKEN` secret and optional `GHCR_USERNAME` variable to credentials that can publish packages to the Data Privacy Stack organization, or run the release from the migrated repository.
