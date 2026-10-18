# Strict propagation mutations after startup fixture correction

[confirmed: receipt.json and complete per-case logs] Writer, reader and cleanup
guards reject removing platform/error-number restrictions after correcting the
startup sys fixture. Each mutation failed at behavior assertions; saved product
bytes were restored in finally with exact SHA256 verification.
