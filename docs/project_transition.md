# Presidio is transitioning to a community-owned project

We want to share an important update regarding the future of Presidio.

The Presidio project is in the process of transitioning from a Microsoft-owned project to an independent, community-governed open source project under the new GitHub organization Data Privacy Stack. Its new URL is: <https://github.com/data-privacy-stack/presidio>

Microsoft supports this transition and the continued success of the Presidio project as an open source community initiative.

Our goal is to ensure Presidio continues to serve the privacy engineering and data protection community as an open, transparent, and vendor-neutral project.

## What this means

* Presidio will continue to be open source under the MIT license.
* Existing functionality, APIs, and documentation will remain available.
* The project will continue to be maintained by contributors and volunteers from the community.
* The project will not be owned or operated by a commercial entity.
* The focus on privacy, responsible AI, and data protection tooling remains unchanged.

## Microsoft and Azure users

This transition does not change the experience for existing users of Presidio, including organizations using Presidio alongside Microsoft and Azure services.

Existing integrations, dependencies, and usage patterns are expected to continue working as they do today.

## Why this change

Over the years, Presidio has grown beyond its original scope and has been adopted by organizations, researchers, and developers across industries. We believe the project is best positioned for long-term sustainability, broader collaboration, and open governance as an independent community initiative.

## What to expect during the transition

During the migration process:

* Repositories, documentation links, and package references may gradually change.
* Some GitHub URLs and documentation pages may redirect temporarily.
* New Docker image releases are published to [GitHub Container Registry](https://github.com/orgs/data-privacy-stack/packages) under the Data Privacy Stack organization. Legacy Microsoft Container Registry (MCR) images remain available for older tags but are no longer updated; update `mcr.microsoft.com/presidio-*` image references to `ghcr.io/data-privacy-stack/presidio-*`.
* Contribution and governance processes will evolve and become more community-driven.
* The technical steering committee (TSC) will expand to include maintainers and contributors from outside Microsoft.

We will do our best to keep the transition smooth and minimize disruption for users and contributors.

## Maintainers and contributors

Many of the current maintainers and contributors intend to remain involved during and after the transition. We also welcome new contributors who care about privacy-preserving technologies and responsible data handling.

More details regarding governance, contribution guidelines, maintainership, Docker image publishing, and roadmap planning will be shared as the transition progresses.

Thank you to everyone who has supported Presidio so far and helped make it a valuable resource for the broader privacy engineering community.
