# Public catalog boundary

## Allowed

- declarative agent definitions under `catalog/agents/`;
- declarative skill definitions under `catalog/skills/`;
- schemas required to interpret those definitions;
- sanitized public documentation and examples;
- catalog-only validation and CI controls; and
- provenance, attribution and licensing records.

## Forbidden

- HubICG runtime or application source;
- adapters, connectors, deployment automation and infrastructure configuration;
- tenant-specific features, prompts, policies, business rules or operational procedures;
- customer, tenant, employee or personal data;
- credentials, tokens, private URLs or private repository references;
- private prompt/chat history; and
- material without confirmed publication and licensing rights.

## Promotion control

The author may request a destination, but a HubTech reviewer selects the final destination and the
exact files. A changed source SHA, path selection or content hash invalidates prior approval.
Automation may validate and open a pull request after authorization; it must not merge to `main`.

Items that fail classification or provenance remain private. There is no automatic flow from a
private customer repository into this public catalog.
