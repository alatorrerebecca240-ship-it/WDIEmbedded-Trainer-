# Third-party content and project licensing

The project owner selected the MIT license for original project code, original
questions, templates, and newly authored adaptation text/code. The root LICENSE
retains the copyright notice already present in the owner's GitHub repository.

This does not replace upstream licenses. Source acquisition locks each selected
file to a full commit and SHA-256; imports retain license text, applicable NOTICE
files, original sources and modification notices inside each package.

| Selected upstream scope | Upstream license | New adaptation license |
| --- | --- | --- |
| Exercism C leap source and tests | MIT | MIT |
| OpenDSA selected C++ sorting source, not the textbook or images | MIT | MIT |
| Zephyr selected blinky example | Apache-2.0 | MIT |
| FreeRTOS-Kernel selected API headers | MIT | MIT |
| CMSIS_6 selected CMSIS-RTOS2 header | Apache-2.0 | MIT |

Mixed-license packages use `license: "mixed"`. A question's `origin.license`
describes its upstream license; `origin.authoredLicense` records the new
adaptation's MIT license. Both license texts are retained by the importer.
Never remove upstream copyright notices or infer that all files in a vendor SDK
share its repository's top-level license.

Unreviewed drafts and acquisition caches are excluded from ordinary commits.
Selecting MIT does not approve educational correctness or reference tests.
Only human-reviewed snapshots that pass the publication gates may become
downloadable knowledge package Releases. The original foundation course remains
a usable editable source package while its remaining reference implementations
and publication review are completed.

See [knowledge workflow](docs/knowledge-pack-workflow.md) and
`knowledge/sources.json` for the selected paths and source license links.
