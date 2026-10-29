# Contract kit 1.0.0 compatibility notes

**Status:** Released after bounded Gate 6 acceptance under DEC-13.

This release keeps the schemas, OpenAPI descriptions, fixture bytes, expected
numerical results, model and simulation semantics, and AI contract behavior of
the released `0.5.0` kit. The version, release documentation and scope notes
are the only changes. Existing `0.5.0` consumer locks remain valid until
coordinated adoption of the `1.0.0` archive and checksum.

For the bounded first release, [DEC-07](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-07-new-equipment-release-scope.md)
limits optimization to new equipment. A nonempty `existingComponentIds` request
is rejected by the VEF model; this kit does not add existing-equipment planning.
[DEC-08](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-08-complete-calendar-year.md)
limits deployed energy optimization to complete UTC calendar years with 8,760
or 8,784 consecutive hourly values. ODIP and VEF enforce that deployment
boundary; the existing schema and fixture are unchanged.

The first release also carries the current-release acceptance scope from
[DEC-10](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-10-current-release-recovery-test-exception.md),
[DEC-11](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-11-current-release-non-ai-acceptance-exceptions.md)
and [DEC-12](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-12-proposed-ai10-equivalent-regression.md).
These decisions classify specified tests and limits for this release; they do
not modify the data contracts or claim that excepted tests passed.

The [DEC-13 decision](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-13-bounded-gate-6-acceptance.md)
accepts the bounded test release with the DEC-10/11/12 limits. It does not
authorize production deployment. Consumers must pin the exact published
archive checksum before adopting this version.
