# Completion-head Linux gate before the legacy test await correction

[confirmed: execution logs] Sourcedea4b58a. Watched-job/publication/save checks pass, competitive checks pass, and32focused checks pass. Lifecycle group finishes53tests with one failure: the original pitch parity test expects the final-ACK poll to have published synchronously. It reaches the existing busy:false assertion before private preparation has finished. All its final result/Memory/RNG/save assertions remain unchanged by the correction.

[designed: #254] Await the new completion boundary using the same pre-existing600second hang guard, continue pumping Qt/polling, and preserve every final parity/once-only assertion. No production code, deadline or expected value changes. Rerun the affected lifecycle group and remaining gates; the three successful groups do not import or execute the changed pitch-test module, and all of their production/test bytes remain identical.
