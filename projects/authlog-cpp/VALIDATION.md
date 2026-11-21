# Validation record - November 5, 2026

GCC strict-warning optimized build: 10 tests passed. Local ASan/UBSan: 10 tests passed with ASAN_OPTIONS=detect_leaks=0 because LeakSanitizer cannot inspect tasks in this environment. This does not claim leak detection. CI runs default sanitizer configuration separately.

GitHub Actions passed all three jobs (C++, PyTorch, restricted Docker image build/test): https://github.com/rithmsAI/tripleten-portfolio/actions/runs/42085427942
GitHub Pages deployment passed: https://github.com/rithmsAI/tripleten-portfolio/actions/runs/42085426188
Local link-target checks passed for the updated landing page and all three new case studies. Browser rendering was not verified because the runtime browser executable was unavailable.
