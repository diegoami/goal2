# Native Windows replacement API diagnosis

[confirmed: complete-report.json] On actual Windows11/Python3.13.15, a15-case matrix compares no reader, ordinary Path.open, raw read/write/delete-shared handles, read+delete-access shared handles, and the production reader-only fix. With a reader open, os.replace/MoveFileExW fail WinError5 even with delete sharing. ReplaceFileW fails with the ordinary unshared reader but succeeds with raw and production delete-shared readers, preserving their old open snapshot while the target becomes the complete new payload. These are new owned diagnostic text files only; this matrix is not original-match/UI acceptance.

[confirmed: initial-native.log] The initial matrix stopped when its own diagnostic Path.read_bytes tried to open a file while another handle held DELETE access; its ordinary reader did not share DELETE access. That observer failure is preserved. The complete fresh matrix closes owned handles before diagnostic target reads and checkpoints each case. Production behavior was unchanged between matrix attempts.

[designed: #254] Both native reader sharing and an appropriate existing-file replacement primitive are required by this demonstrated interleave. Preserve original bounded error handling and packet validation. No timeout increase or broader error suppression is justified.
