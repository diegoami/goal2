# Native Claude fixture projection

[confirmed: T73 local CLI2.1.292 continuation stdout SHA256351c8baca9c59202188c56f8bbeb6104d0186baa1caf51712ffe4ff37a8b43f2] `native-shape.json` projects native init/assistant/result fields. Session/cwd/final text were replaced; account/paths/socket/request identities were excluded. Numeric native usage/duration fields and null assistant stop_reason are retained. Tests create synthetic tool calls/results and explicit approval-looking failures using these native shapes. No credential or original-game bytes.
