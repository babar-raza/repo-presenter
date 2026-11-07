// TC-021: tiny fixture run under node inside the sandbox-execute job's isolated container to
// prove the sandbox mechanism does not also break legitimate, non-malicious example code.
// Plain JS (no TS-only syntax) so it runs directly under node with no extra tsc/ts-node install
// inside the already-minimal sandbox image; deliberately trivial, same as the cpp fixture.
console.log("hello from typescript");
