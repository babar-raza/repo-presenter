// TC-021: tiny fixture compiled inside the sandbox-execute job's isolated container to prove the
// sandbox mechanism does not also break legitimate, non-malicious example code. Deliberately
// trivial -- this proves the *sandbox*, not the cpp extractor or verifier.
#include <cstdio>

int main() {
    std::printf("hello from cpp\n");
    return 0;
}
