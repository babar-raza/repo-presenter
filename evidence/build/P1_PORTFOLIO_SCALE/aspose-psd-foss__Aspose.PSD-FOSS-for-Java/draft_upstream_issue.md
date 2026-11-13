<!-- NOT FILED. Filing only as owner rulings R7/R15 allow (no upstream write before every candidate of both lanes passes). -->

**Target repository:** `aspose-psd-foss/Aspose.PSD-FOSS-for-Java`
**Target revision:** `a7b05fdd` (pinned Lane R revision, 2026-11-13)

## Proposed title

README documents a Maven install that does not resolve, and the shipped sources do not build

## Proposed body

- The README documents installing `org.aspose.psd:aspose-psd-foss-java:1.0.0` with Maven, but that artifact
  returns 404 on Maven Central.
- The repository ships no build manifest (`pom.xml` or `build.gradle`); the tree holds only `main/`, `test/` and
  `testdata/`, so there is no source build either.
- The shipped sources do not compile: `main/java` alone fails under javac 21 at
  `main/java/samples/streams/Program.java:34` (unreported checked exception `PsdLoadException`).

Recommend publishing the artifact (or correcting the coordinates), adding a build manifest, and fixing the sample.

## Why this blocks the README work (internal)

With no verifiable install (no registry artifact, no manifest, no compiling example), BC-02 cannot be satisfied
honestly; every R36(a) alternative was evaluated and none yields a certified candidate with no false claim.
Repository is terminal under R24 for Lane R until upstream changes.
