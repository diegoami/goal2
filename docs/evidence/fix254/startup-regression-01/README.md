# Watched input preparation regression

[designed: owner, 2026-10-19] The [approved scope extension](scope-extension.md) belongs to existing #254/PR255. Encoding and writing use the already private job snapshot on one owned thread; owner checks, subprocess launch and publication stay on the calling thread. The validated save encoder and its exact bytes remain unchanged. Cancellation first invalidates publication; an unfinished bounded wait retains process/folder ownership and the match lock for retry.

[confirmed: before.log] On pre-extension source30ff8537, the four initial regression tests fail in seven subcases. Gated encoding prevents start from returning to release its gate; preparation/write/launch errors are synchronous instead of reaching the poll error boundary.

[confirmed: after.log] On the implementation in this commit, six startup regressions and the existing16 sharing/error/deadline/cleanup/packet tests pass with Python3.12.14. Actual save encode/decode and exact-byte comparisons are exercised using synthetic state; input writing is separately gated. The blocked encoding control exceeds the existing two0.5second cancellation waits, retains ownership and then retries cleanup without launching. A cleanup-denial regression retains the lock until retry. These are synthetic Linux tests, not native original-match acceptance or independent review.

[designed: remaining acceptance] Original-match Linux checks, regression mutations, actual native Windows Qt1x/2x receipt/independent anchoring and independent review remain required. All earlier failed native runs are retained.
