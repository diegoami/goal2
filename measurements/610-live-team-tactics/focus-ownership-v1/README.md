# Test-window key ownership

The previous combined35-test run remains FAILED with one packet-case failure. All3actual UI/verifiedPyPy journeys and the other controls passed. The extra-time case passes alone; the new foreign-focus control reproduces the same failure with a separate QLineEdit holding application focus. The test helper now directs QTest keys to its own Window instead of QApplication's global focus widget. Existing assertions are retained, including no key leakage into the other window. Production code is unchanged.

`foreign-before.log` fails at the original tactics-screen assertion. `packet-after.log`:13packet/transport checksPASS140.051s. `unchanged-actual-inputs.json` binds the previous actual-class AST, unchanged application/engine/tools, and exact original fixtures; T189 permits reuse of those3passing real journeys and20unaffected controls. Their previous35-test aggregate is never relabelled passed. New combined-source defaultFAST and hosted/native checks still follow.

Model inherited Codex GPT-6 family; exact variant unavailable.
