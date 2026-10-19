# T79 SDL metadata crash diagnosis

[confirmed: ../it13-handoff-diagnostic-01/report.json and owned stderr] The real original first round completed, but replay's SDL child exited by SIGABRT after pygame's segmentation-fault handler, before writing metrics. The preserved stderr pins the compound metadata query; product/controller source was unchanged and cleanup reaped owned jobs without pending state.

[confirmed: ../it13-metadata-probe-01/report.json and ../it13-metadata-probe-02/report.json] All48 short fixed/resizable startup probes passed, with and without WM metadata. They did not reproduce the real rendering context and are infrastructure diagnostics only.

[confirmed: ../it13-handoff-traced-02/round-0-viewer-stderr.log] Per-call tracing in an explicitly diagnostic observer copy isolated the failure to pygame.display.get_wm_info(): actual x11 driver, SDL/Pygame versions,1000x720 window/surface, surface flags and OS metadata all completed first. The traced real observer then segfaulted at WM-info before its first metrics receipt. The full original dispatcher failure and both diagnostic failures are preserved; none is accepted final evidence.

[designed: T79] The owned production observer now queries WM-info only for Windows HWND/DPI collection, which remains required and unchanged there. Linux still measures actual driver/window/surface/fonts and all render/flip/capture/state/lifecycle oracles. No assertion, renderer, controller, protocol or dependency version is changed. Fresh integrated full/retained gates and actual Windows validation remain required after this helper correction. The pre-correction helper is retained verbatim.
