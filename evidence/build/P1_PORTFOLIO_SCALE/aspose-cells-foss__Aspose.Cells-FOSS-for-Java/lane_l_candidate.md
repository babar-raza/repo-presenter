Empty-patch ACCEPT. All 7 checked facts in facts.json are SUPPORTED (0 CONTRADICTED) -- the
Maven Central package/version match (confirmed live against repo1.maven.org), the Java
17/test-scope-only-POI claim, the precise 18-of-25-ChartType/7-ChartEx-unsupported claim
(cross-checked against ChartType.java's own enum and ChartCollection.add()'s exact reject
list), the 38-preset-AutoShapeType claim, the disclosed-and-genuinely-dead XML-mapper
skeleton classes, the API table's own internal 183-row count, and the Quick Start/Additional
Examples class references all reproduced true against the actual Java source at this
source_revision. One sub-claim (the exact pinned JUnit/POI dev-dependency version numbers,
5.10.2/5.3.0) is UNVERIFIED rather than SUPPORTED -- the pom.xml properties block was not
independently re-read to confirm the literal numbers -- but this does not contradict anything
and is left untouched. Per the playbook's fast path, the Lane L candidate is the live README
unchanged at source_revision c65329e7257b1311abb9686d7e4957a8cc002955. No
`lane_l_candidate.diff` is produced for this reason.
