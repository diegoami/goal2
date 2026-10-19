# First IT13 integrated T79 batch

[confirmed: ../it13-integrated-full-01/report.json and status.json] On integrated source492c870140d4b72237a8861392bf9a0e078c0f16, five presentation controls and60tests passed with exact source restoration. Actual original handoff round0 reached full original state/Memory/RNG/event parity, frameACK4465 and complete-boardACK with an x11 SDL observer. The checkpoint replay then lacked round1 SDL metrics and the overall batch remains FAIL; retained gates did not start. No native Windows acceptance or final integration acceptance is claimed.

[confirmed: full.log and infrastructure envelopes] The source inventory matched after the failing child; owned WM/Xvfb were cleaned up and scenario cleanup reports no pending job or unreaped process. Exact infrastructure text bytes are preserved in UTF-8 envelopes; adjacent LF reading files trim only terminal blank lines. The SDL replay failure is under diagnosis, with no assertion weakening or product modification.
